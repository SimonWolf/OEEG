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
from functools import lru_cache
from tqdm import tqdm

# Meta/paths kept outside the class, as requested
PATH_DELTA = "data/delta-table/"
lock = threading.Lock()


class DownloadError(RuntimeError):
    """Fehler beim Herunterladen der Quelldatei (HTTP o.ä.)."""


class ParseError(RuntimeError):
    """Fehler beim Parsen der Rohdaten in ein DataFrame."""


class DataNotAvailableError(RuntimeError):
    """Keine Daten für das angeforderte Datum/Standort verfügbar."""


class Leistung:
    def __init__(self):
        # Class no longer bound to a specific standort
        # create delta-table if not exists
        try:
            # Try opening existing table to ensure it exists
            DeltaTable(PATH_DELTA)
        except Exception:
            with lock:
                empty_df = pd.DataFrame(
                    {
                        "Datetime": pd.Series(dtype="datetime64[s]"),
                        "wr": pd.Series(dtype="int64"),
                        "string": pd.Series(dtype="int64"),
                        "sensor": pd.Series(dtype="str"),
                        "value": pd.Series(dtype="float64"),
                        "standort": pd.Series(dtype="str"),
                    }
                )
                pl.DataFrame(empty_df).write_delta(PATH_DELTA, mode="overwrite")
        pass
    
    def __make_column_metadata(self, n_cols: int, wr_label: str) -> List[Tuple[str, int]]:
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

    @lru_cache(maxsize=32)   
    def download_day_long(self, standort: str, date_str: str, ttl_hash=None) -> pd.DataFrame:
        """
        Lädt Loggerdaten (min<date>.js) und liefert ein "long" DataFrame mit diesen Spalten:
          - Datetime (pd.Timestamp)
          - wr (int)
          - string (int) (-1 wenn kein String, sonst 1,2,...)
          - sensor (str) ('P','sum','Udc','T',...)
          - value (float)
        """
        
        base_url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{standort}/visualisierung/"
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
            # Ensure second-level sampling (drop sub-second precision)
            raw_df[0] = raw_df[0]
        except Exception as e:
            raise ParseError(f"ParseError: Time {e} {url}")

        raw_df.columns = ["Datetime"] + [f"WR{i + 1}" for i in range(len(raw_df.columns) - 1)]

        long_parts: List[pd.DataFrame] = []
        for wr_col in raw_df.columns[1:]:
            col_series = raw_df[wr_col].astype(str)
            split_df = col_series.str.split(";", expand=True)
            split_df = split_df.apply(pd.to_numeric, errors="coerce")
            split_df.index = raw_df.index

            meta = self.__make_column_metadata(split_df.shape[1], wr_col)
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
        result["standort"] = standort
        return result

    def write_to_file(self, df: pd.DataFrame, date: dt.date):
        with lock:
            pdf = df.copy()
            pdf["Datetime"] = pd.to_datetime(pdf["Datetime"])
            pldf = (
                pl.DataFrame(pdf)
                .with_columns(
                    pl.col("Datetime").cast(pl.Datetime(time_unit="ms"))
                )
            )
            pldf.write_delta(PATH_DELTA, mode="append")

    def optimize(self):
        with lock:
            dtbl = DeltaTable(PATH_DELTA)
            before = len(dtbl.file_uris())
            dtbl.optimize.z_order(["Datetime", "standort"])
            dtbl.optimize.compact()
            dtbl.vacuum(retention_hours=0, dry_run=False, enforce_retention_duration=False)
            after = len(dtbl.file_uris())
            print(f"[optimize]: Files before: {before}, after: {after}")

    def get_day_and_update(self, standort: str, date: dt.date) -> pl.LazyFrame:
        if date == dt.datetime.now().date():
            try:
                ttl_hash = int(dt.datetime.now().timestamp() // 300)  # 5 minutes TTL
                df = self.download_day_long(standort, date.strftime("%y%m%d"), ttl_hash=ttl_hash)
                return pl.LazyFrame(df)
            except Exception as e:
                raise DownloadError(f"Heutiger Download fehlgeschlagen: {standort} - {date} - {e}") from e
        else:
            with lock:
                lf = pl.scan_delta(PATH_DELTA)
                lf = lf.filter((pl.col("Datetime").dt.date() == date) & (pl.col("standort") == standort))

            n_rows_of_lf = lf.select(pl.len()).collect().item()
            if n_rows_of_lf > 1:
                return lf
            if n_rows_of_lf == 1:
                raise DataNotAvailableError(
                    f"Platzhalter vorhanden, aber keine echten Daten: {standort} - {date}"
                )
            if n_rows_of_lf == 0:
                try:
                    df = self.download_day_long(standort, date.strftime("%y%m%d"))
                    threading.Thread(target=self.write_to_file, args=(df, date), daemon=True).start()
                    return pl.LazyFrame(df)
                except Exception as e:
                    # Schreibe Platzhalter und werfe Error weiter
                    df_empty = pd.DataFrame(
                        [
                            {
                                "Datetime": date,
                                "wr": -1,
                                "string": -1,
                                "sensor": -1,
                                "value": -1,
                                "standort": standort,
                            }
                        ]
                    )
                    df_empty["Datetime"] = pd.to_datetime(df_empty["Datetime"])
                    threading.Thread(target=self.write_to_file, args=(df_empty, date), daemon=True).start()
                    raise DownloadError(
                        f"Download/Parse fehlgeschlagen: {standort} - {date} - {e}"
                    ) from e

    def download_days(self, standort: str, days_back: int) -> None:
        """
        Für einen Standort lädt für die letzten `days_back` Tage (inkl. heute)
        die Leistungsdaten via `get_day_and_update` und führt danach `optimize()` aus.
        Gibt nichts zurück.

        Beispiel: days_back=7 lädt heute bis einschließlich vor 7 Tagen.
        """
        if days_back < 0:
            return
        today = dt.datetime.now().date()
        start_date = today - dt.timedelta(days=days_back)
        # Single-scan: build availability map to avoid per-day scans
        counts_df = self._get_existing_counts(standort, start_date, today)
        missing_dates = counts_df.loc[counts_df["count"]==0]["date"].tolist()

        for single_date in tqdm(missing_dates, desc=f"Downloading days for {standort}"):
            try:
                self.get_day_and_update(standort, single_date)
            except Exception as e:
                print(f"[download_days]: {standort} - {single_date} - {e}")
       

    def _get_existing_counts(self, standort: str, start_date: dt.date, end_date: dt.date) -> dict:
        """
        Liefert eine Map {date: row_count} für einen Standort und Datumsbereich.
        Führt nur EINE Delta-Scan-Operation durch und gruppiert nach Datum.
        """
        try:
            lf = pl.scan_delta(PATH_DELTA)
            # Filter by standort and date range; use derived date for grouping
            lf = lf.filter(pl.col("standort") == standort)
            lf = lf.with_columns(pl.col("Datetime").dt.date().alias("date"))
            lf = lf.filter((pl.col("date") >= pl.lit(start_date)) & (pl.col("date") <= pl.lit(end_date)))
            counts_df = (
                lf.group_by("date")
                .agg(pl.len().alias("count"))
                .collect(engine="streaming")
                .to_pandas()
            )
            # sample the count_df to have a row for each date if no count fill with 0
            all_dates = pd.date_range(start=start_date, end=end_date).date
            counts_df = counts_df.set_index("date").reindex(all_dates, fill_value=0).reset_index()
            counts_df.columns = ["date", "count"]
            return counts_df
        except Exception as e:
            print(f"[existing_counts]: {standort} - {e}")
            return {}

    # def get_heutige_Leistung(self, standort: str) -> np.ndarray:
    #     """
    #     Liest die Daten im Long-Format und gibt die P-Werte des heutigen Tages
    #     für den Standort als NumPy-Array zurück (ohne führende/nachlaufende Nullen).
    #     """
    #     today = dt.datetime.today().date()
    #     try:
    #         lf = self.get_day_and_update(standort, today)
    #         if lf is None:
    #             return np.array([])

    #         df_filtered = (
    #             lf.filter((pl.col("string") == -1) & (pl.col("sensor") == "P"))
    #             .group_by("Datetime")
    #             .agg(pl.col("value").sum().alias("P_gesamt"))
    #             .sort("Datetime")
    #             .collect(engine="streaming")
    #             .to_pandas()
    #         )
    #         return np.trim_zeros(df_filtered["P_gesamt"].to_numpy(), "fb")
    #     except Exception as e:
    #         print(e)
    #         return np.array([])
