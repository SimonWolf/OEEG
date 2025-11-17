import pandas as pd
import requests
import re
from io import StringIO
from datetime import datetime
from typing import List, Tuple
from tqdm import tqdm
import datetime as dt

def get_day_df_long(standort: str, date_str: str) -> pd.DataFrame:
    """
    Lädt Loggerdaten (min<date>.js) und liefert ein "long" DataFrame mit diesen Spalten:
      - Datetime (pd.Timestamp)
      - wr (int)    (z.B. 1, 2)
      - string (int) (-1 wenn kein String, sonst 1,2,...)
      - sensor (str) ('P','sum','Udc','T',...)
      - value (float)
    """
    def make_column_metadata(n_cols: int, wr_label: str) -> List[Tuple[str,int]]:
        """
        Baut eine Liste (sensor, string) für jede Spalte nach der Logik:
          [WR_P] + [WR_S1_P ... WR_Sn_P] + [WR_sum] + [WR_S1_Udc ...] (+ [WR_T] optional)
        Rückgabe: Liste mit Länge n_cols, Eintrag z.B. ('P', -1) oder ('P', 1) oder ('Udc', 1) ...
        """
        if n_cols < 2:
            raise ValueError(f"{wr_label}: Ungültige Anzahl an Spalten ({n_cols})")

        # Anzahl Strings (Anzahl Sx-Paare)
        n_strings = (n_cols - 2) // 2

        meta: List[Tuple[str,int]] = []
        # erste Spalte = P (kein string)
        meta.append(("P", -1))
        # danach S1_P ... S{n}_P
        for i in range(1, n_strings + 1):
            meta.append(("P", i))
        # dann sum (kein string)
        meta.append(("sum", -1))
        # danach S1_Udc ... S{n}_Udc
        for i in range(1, n_strings + 1):
            meta.append(("Udc", i))
        # optionales T am Ende
        if (n_cols - 2) % 2 == 1:
            meta.append(("T", -1))

        # Sanity check
        if len(meta) != n_cols:
            raise RuntimeError("Interner Fehler bei meta-Erstellung")

        return meta

    try:
        # URL zusammenbauen
        base_url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{standort}/visualisierung/"
        heute = datetime.now().strftime("%y%m%d")
        file_name = "min_day.js" if date_str == heute else f"min{date_str}.js"
        url = base_url + file_name

        # download
        response = requests.get(url)
        if response.status_code != 200:
            return pd.DataFrame()  # oder: f"Download fehlgeschlagen: {response.status_code}"

        matches = re.findall(r'="([^"]+)"', response.text)
        if not matches:
            return pd.DataFrame()

        raw_data = "\n".join(matches).replace("|", ",")
        raw_df = pd.read_csv(StringIO(raw_data), sep=",", header=None)

        # Zeitspalte parsen + Spaltennamen setzen
        raw_df[0] = pd.to_datetime(raw_df[0], format="%d.%m.%y %H:%M:%S")
        raw_df.columns = ["Datetime"] + [f"WR{i+1}" for i in range(len(raw_df.columns) - 1)]

        # Ergebnis sammeln
        long_parts: List[pd.DataFrame] = []

        # für jede Wechselrichter-Spalte
        for wr_col in raw_df.columns[1:]:
            col_series = raw_df[wr_col].astype(str)  # sicherstellen, str für split
            split_df = col_series.str.split(";", expand=True)

            # konvertiere zu float — falls leere Werte vorhanden sind, bleiben NaN
            split_df = split_df.apply(pd.to_numeric, errors="coerce")

            # Index beibehalten, damit Datetime sauber zugeordnet werden kann
            split_df.index = raw_df.index

            # Metadaten generieren (sensor, string) pro resultierender Spalte
            meta = make_column_metadata(split_df.shape[1], wr_col)

            # melt: originaler index als id mitnehmen
            melted = split_df.reset_index().melt(id_vars="index", var_name="col_idx", value_name="value")

            # wr index extrahieren (z.B. aus "WR2" -> 2)
            wr_idx_match = re.search(r'(\d+)', wr_col)
            wr_idx = int(wr_idx_match.group(1)) if wr_idx_match else None

            # mappe col_idx (als int) auf meta
            def map_meta(col_idx: int) -> Tuple[int, str]:
                # col_idx ist 0-basierter Spaltenindex nach dem split
                col_idx = int(col_idx)
                sensor, stringnum = meta[col_idx]
                return stringnum, sensor

            mapped = melted["col_idx"].apply(map_meta)
            melted["string"] = mapped.apply(lambda x: x[0])
            melted["sensor"] = mapped.apply(lambda x: x[1])
            melted["wr"] = wr_idx

            # Datetime korrekt zuordnen über den originalen row-index
            melted["Datetime"] = melted["index"].map(raw_df["Datetime"])

            # Spaltenreihenfolge wie gewünscht
            part = melted[["Datetime", "wr", "string", "sensor", "value"]]
            long_parts.append(part)

        # alles zusammenfügen und Typen setzen
        result = pd.concat(long_parts, ignore_index=True)
        result["wr"] = result["wr"].astype(int)
        result["string"] = result["string"].astype(int)

        return result

    except Exception as e:
        # Bei Fehlern leere DF zurückgeben oder Fehlertext — hier leeres DF
        return pd.DataFrame()


def update_leistung():
    standorte = ["badboll","esslingen","geislingen","holzgerlingen","hospitalhof",
                 "karlsruhe","mettingen","muensingen","tuebingen","waiblingen"]
    
    end = dt.datetime.now()
    days_back = 5
    start = end - dt.timedelta(days=days_back)
    required_dates = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]

    new_data = []
    for s in tqdm(standorte):
        missing_dates = required_dates
        for date in missing_dates:
            temp = get_day_df_long(s, date.strftime("%y%m%d"))
            if isinstance(temp, pd.DataFrame) and temp.shape[0] > 0:
                # Standort-Spalte hinzufügen
                temp["standort"] = s
                new_data.append(temp)

    if new_data:
        res =  pd.concat(new_data, ignore_index=True).drop_duplicates()
    else:
        res =  pd.DataFrame()
    
    res.to_parquet("app/data/leistung.parquet",index=False)