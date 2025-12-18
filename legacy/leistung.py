import datetime as dt
import threading
import polars as pl
from deltalake import DeltaTable
import pandas as pd
import requests
import re
from io import StringIO
from datetime import datetime
from typing import List, Tuple
import numpy as np


# Meta/paths kept outside the class, as requested
PATH_DELTA = "./delta-table/"
lock = threading.Lock()


class DownloadError(RuntimeError):
    """Fehler beim Herunterladen der Quelldatei (HTTP o.ä.)."""


class ParseError(RuntimeError):
    """Fehler beim Parsen der Rohdaten in ein DataFrame."""


class Leistung:
    def __init__(self, standort: str):
        self.standort = standort

    def download_day_long(self, date_str: str, ttl_hash=None) -> pd.DataFrame:
        """
        Lädt Loggerdaten (min<date>.js) und liefert ein "long" DataFrame mit diesen Spalten:
          - Datetime (pd.Timestamp)
          - wr (int)
          - string (int) (-1 wenn kein String, sonst 1,2,...)
          - sensor (str) ('P','sum','Udc','T',...)
          - value (float)
        """
        print("Download:", self.standort, date_str)

        def make_column_metadata(n_cols: int, wr_label: str) -> List[Tuple[str, int]]:
            """
            Baut eine Liste (sensor, string) für jede Spalte nach der Logik:
              [WR_P] + [WR_S1_P ... WR_Sn_P] + [WR_sum] + [WR_S1_Udc ...] (+ [WR_T] optional)
            Rückgabe: Liste mit Länge n_cols, Eintrag z.B. ('P', -1) oder ('P', 1) oder ('Udc', 1) ...
            """
            if n_cols < 2:
                raise ValueError(f"{wr_label}: Ungültige Anzahl an Spalten ({n_cols})")

            n_strings = (n_cols - 2) // 2

            meta: List[Tuple[str, int]] = []
            meta.append(("P", -1))
            for i in range(1, n_strings + 1):
                meta.append(("P", i))
            meta.append(("sum", -1))
            for i in range(1, n_strings + 1):
                meta.append(("Udc", i))
            if (n_cols - 2) % 2 == 1:
                meta.append(("T", -1))

            if len(meta) != n_cols:
                raise RuntimeError("Interner Fehler bei meta-Erstellung")

            return meta

        base_url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{self.standort}/visualisierung/"
        heute = datetime.now().strftime("%y%m%d")
        file_name = "min_day.js" if date_str == heute else f"min{date_str}.js"
        url = base_url + file_name

        response = requests.get(url)
        if response.status_code != 200:
            raise DownloadError(f"{response.status_code} for URL {url}")

        matches = re.findall(r'="([^"]+)"', response.text)
        if not matches:
            raise ParseError(f"ParseError: regex {url}")

        raw_data = "\n".join(matches).replace("|", ",")
        try:
            raw_df = pd.read_csv(StringIO(raw_data), sep=",", header=None)
        except Exception:
            raise ParseError(f"ParseError: CSV {url}")
        if raw_df.shape[1] < 2:
            raise ParseError(f"ParseError: Shape {url}")

        try:
            raw_df[0] = pd.to_datetime(raw_df[0], format="%d.%m.%y %H:%M:%S")
        except Exception as e:
            raise ParseError(f"ParseError: Time {e} {url}")

        raw_df.columns = ["Datetime"] + [f"WR{i + 1}" for i in range(len(raw_df.columns) - 1)]

        long_parts: List[pd.DataFrame] = []
        for wr_col in raw_df.columns[1:]:
            col_series = raw_df[wr_col].astype(str)
            split_df = col_series.str.split(";", expand=True)
            split_df = split_df.apply(pd.to_numeric, errors="coerce")
            split_df.index = raw_df.index

            meta = make_column_metadata(split_df.shape[1], wr_col)
            if len(meta) != split_df.shape[1]:
                raise ParseError(
                    f"Meta-Länge stimmt nicht mit Spaltenanzahl überein für {wr_col} "
                    f"({len(meta)} != {split_df.shape[1]})"
                )

            melted = split_df.reset_index().melt(id_vars="index", var_name="col_idx", value_name="value")

            wr_idx_match = re.search(r"(\d+)", wr_col)
            if not wr_idx_match:
                raise ParseError(f"Konnte WR-Index nicht aus Spaltennamen '{wr_col}' extrahieren.")
            wr_idx = int(wr_idx_match.group(1)) if wr_idx_match else None

            def map_meta(col_idx: int) -> Tuple[int, str]:
                col_idx = int(col_idx)
                sensor, stringnum = meta[col_idx]
                return stringnum, sensor

            mapped = melted["col_idx"].apply(map_meta)
            melted["string"] = mapped.apply(lambda x: x[0])
            melted["sensor"] = mapped.apply(lambda x: x[1])
            melted["wr"] = wr_idx
            melted["Datetime"] = melted["index"].map(raw_df["Datetime"])

            part = melted[["Datetime", "wr", "string", "sensor", "value"]].copy()
            part["wr"] = part["wr"].astype(int)
            part["string"] = part["string"].astype(int)
            part["value"] = pd.to_numeric(part["value"], errors="coerce")
            long_parts.append(part)

        if not long_parts:
            raise ParseError("Keine Wechselrichter-Spalten verarbeitet (keine Teile erzeugt).")

        result = pd.concat(long_parts, ignore_index=True)
        result = result.drop_duplicates().reset_index(drop=True)
        result["standort"] = self.standort
        return result

    def write_to_file(self, df: pd.DataFrame, date: dt.date):
        with lock:
            pl.DataFrame(df).write_delta(PATH_DELTA, mode="append")

    def optimize(self):
        with lock:
            dtbl = DeltaTable(PATH_DELTA)
            before = len(dtbl.file_uris())
            dtbl.optimize.z_order(["Datetime", "standort"])
            dtbl.optimize.compact()
            dtbl.vacuum(retention_hours=0, dry_run=False, enforce_retention_duration=False)
            after = len(dtbl.file_uris())
            print(f"[optimize]: Files before: {before}, after: {after}")

    def get_day_and_update(self, date: dt.date) -> pl.LazyFrame | None:
        # Heute: direkt laden, nicht speichern
        if date == dt.datetime.now().date():
            try:
                df = self.download_day_long(date.strftime("%y%m%d"))
                return pl.LazyFrame(df)
            except Exception as e:
                print("heute:", e)
                return None
        else:
            # Nicht heute: aus Delta laden oder einmalig downloaden
            with lock:
                lf = pl.scan_delta(PATH_DELTA)
                lf = lf.filter((pl.col("Datetime").dt.date() == date) & (pl.col("standort") == self.standort))

            n_rows_of_lf = lf.select(pl.len()).collect().item()
            if n_rows_of_lf > 1:
                return lf
            if n_rows_of_lf == 1:
                return None
            if n_rows_of_lf == 0:
                try:
                    df = self.download_day_long(date.strftime("%y%m%d"))
                    threading.Thread(target=self.write_to_file, args=(df, date), daemon=True).start()
                    return pl.LazyFrame(df)
                except Exception as e:
                    print(f"[getDay]: {self.standort} - {date} - {e}")
                    df_empty = pd.DataFrame(
                        [
                            {
                                "Datetime": date,
                                "wr": -1,
                                "string": -1,
                                "sensor": -1,
                                "value": -1,
                                "standort": self.standort,
                            }
                        ]
                    )
                    df_empty["Datetime"] = pd.to_datetime(df_empty["Datetime"])
                    threading.Thread(target=self.write_to_file, args=(df_empty, date), daemon=True).start()
                    return None

    def get_heutige_Leistung(self) -> np.ndarray:
        """
        Liest die Daten im Long-Format und gibt die P-Werte des heutigen Tages
        für den Standort als NumPy-Array zurück (ohne führende/nachlaufende Nullen).
        """
        today = dt.datetime.today().date()
        try:
            lf = self.get_day_and_update(today)
            if lf is None:
                return np.array([])

            df_filtered = (
                lf.filter((pl.col("string") == -1) & (pl.col("sensor") == "P"))
                .group_by("Datetime")
                .agg(pl.col("value").sum().alias("P_gesamt"))
                .sort("Datetime")
                .collect(engine="streaming")
                .to_pandas()
            )
            return np.trim_zeros(df_filtered["P_gesamt"].to_numpy(), "fb")
        except Exception as e:
            print(e)
            return np.array([])
