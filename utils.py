from datetime import datetime
import requests
import pandas as pd
import re
from io import StringIO
ROOT_PATH = "/app/data/"


def get_day_df(standort: str, date: str):
    """Lädt und parst Loggerdaten für ein gegebenes Datum & Standort."""

    def split_wr_column(series: pd.Series, wr: str) -> pd.DataFrame:
        """Spaltet WR-Spalte in beschriftete Teilspalten"""
        split_data = series.str.split(";", expand=True).astype(int)
        n = split_data.shape[1]
        if n < 2:
            raise ValueError(f"{wr}: Ungültige Anzahl an Werten ({n})")

        n_strings = (n - 2) // 2
        col_names = [f"{wr}_P"] \
                  + [f"{wr}_S{i+1}_P" for i in range(n_strings)] \
                  + [f"{wr}_sum"] \
                  + [f"{wr}_S{i+1}_Udc" for i in range(n_strings)]
        if (n - 2) % 2 ==1:
            col_names += [f"{wr}_T"]
        split_data.columns = col_names
        return split_data

    try:
        # URL zusammenbauen
        base_url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{standort}/visualisierung/"
        heute = datetime.now().strftime("%y%m%d")
        file_name = "min_day.js" if date == heute else f"min{date}.js"
        url = base_url + file_name

        # Request & Daten extrahieren
        response = requests.get(url)
        if response.status_code != 200:
            return f"Download fehlgeschlagen: {response.status_code}"

        matches = re.findall(r'="([^"]+)"', response.text)
        if not matches:
            return pd.DataFrame()

        raw_data = "\n".join(matches).replace("|", ",")
        df = pd.read_csv(StringIO(raw_data), sep=",", header=None)
        df[0] = pd.to_datetime(df[0], format="%d.%m.%y %H:%M:%S")
        df.columns = ["Datetime"] + [f"WR{i+1}" for i in range(len(df.columns) - 1)]

        # WR-Spalten aufspalten
        parts = [df[["Datetime"]]]
        for wr in df.columns[1:]:
            parts.append(split_wr_column(df[wr], wr))

        return pd.concat(parts, axis=1)

    except Exception as e:
        return f"Fehler beim Parsen: {e}"
    
    
def get_hist_data(standort):
    url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{standort}/visualisierung/days_hist.js"

    # Request & Daten extrahieren
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Download fehlgeschlagen: {response.status_code}")

    matches = re.findall(r'="([^"]+)"', response.text)
    if not matches:
        pd.DataFrame()

    raw_data = "\n".join(matches).replace("|", ",")
    df = pd.read_csv(StringIO(raw_data), sep=",", header=None)
    dfs = [pd.to_datetime(df[0], format="%d.%m.%y")]
    for i in range(1,len(df.columns)):
        dfs.append(df[i].str.split(";", expand=True).astype(int)[0])
    df = pd.concat(dfs, axis=1)
    df.columns = ["Datetime"]+[f"WR{i+1}" for i in range(len(df.columns)-1)]
    return df



import os
import pandas as pd
import numpy as np
import itertools
import datetime as dt
from pathlib import Path
import warnings


import os
import pandas as pd
import numpy as np
import itertools
import datetime as dt
from pathlib import Path
import warnings

class QualityIndexStore:
    def __init__(self, standort, save_dir=ROOT_PATH, days_back=60):
        self.standort = standort
        self.save_dir = Path(save_dir)
        self.days_back = days_back
        self.file_path = self.save_dir / f"{standort}_quality.pkl"
        self._ensure_dir()
        self.df = self._load_or_init()
        self._set_combinations()

    def _ensure_dir(self):
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _load_or_init(self):
        if self.file_path.exists():
            return pd.read_pickle(self.file_path)
        return pd.DataFrame()

    def _set_combinations(self):
        max_lookback_weeks = 400  # maximale Anzahl Tage, die rückwärts geprüft werden
        if not self.df.empty:
            self.combos = list(itertools.combinations(self.df.columns[self.df.columns.str.endswith("_P")], 2))
            return
        today = dt.date.today()

        for offset in range(max_lookback_weeks):
            check_date = today - dt.timedelta(weeks=offset)
            sample_df = get_day_df(self.standort, check_date.strftime("%y%m%d"))
            if isinstance(sample_df, str) or sample_df.empty:
                continue  # leer oder Fehler, nächsten Tag prüfen
            else:
                self.combos = list(itertools.combinations(
                    sample_df.columns[sample_df.columns.str.endswith("_P")], 2))
                return

        # Wenn kein gültiger Tag gefunden wurde
        self.combos = []
        
    def _penalized_corr(self, a, b, nan_penalty=-1):
        mask_valid = a.notna() & b.notna()
        mask_both_nan = a.isna() | b.isna()

        if mask_valid.sum() < 10:
            return np.nan  # zu wenige Daten

        corr_val = a[mask_valid].corr(b[mask_valid])

        # Optional: einfache lineare Strafe für doppelte NaNs
        penalty_strength = mask_both_nan.sum() / len(a)
        penalized = corr_val + penalty_strength * nan_penalty  # z. B. -0.5 pro NaN

        return penalized
    
    def _calc_quality_index(self, df_day):
        if isinstance(df_day, str) or df_day.empty:
            return {pair: np.nan for pair in self.combos}
        np.seterr(divide='ignore', invalid='ignore')
        return {pair: self._penalized_corr(df_day[pair[0]],df_day[pair[1]]) for pair in self.combos}
        return {pair: df_day[pair[0]].corr(df_day[pair[1]]) for pair in self.combos}

   

    def _fetch_missing_dates(self, required_dates):
        missing_dates = [d for d in required_dates if d not in self.df.index]
        new_data = []
        for date in missing_dates:
            df_day = get_day_df(self.standort, date.strftime("%y%m%d"))
            
            if not isinstance(df_day, str) and not df_day.empty:
                df_day = df_day.set_index("Datetime").resample("5min").asfreq().reset_index()
                df_day = df_day[df_day["Datetime"].dt.time.between(dt.time(6, 0), dt.time(22, 0))]
                
            quality = self._calc_quality_index(df_day)
            row = {}
            for wr in set(w for pair in self.combos for w in pair):
                wr_pairs = [pair for pair in self.combos if wr in pair]
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    row[wr] = np.nanmean([quality[pair] for pair in wr_pairs])
            new_data.append((date, row))

        if new_data:
            update_df = pd.DataFrame({d: r for d, r in new_data}).T
            update_df.index.name = "Date"
            self.df = pd.concat([self.df, update_df]).sort_index()
            self.df = self.df[~self.df.index.duplicated()]
            self.df.to_pickle(self.file_path)

    def get_data(self, start_date=None):
        if start_date is None:
            end = dt.date.today()- dt.timedelta(days=1)
        else:
            end = start_date - dt.timedelta(days=1)

        start = end - dt.timedelta(days=self.days_back)
        required_dates = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]

        self._fetch_missing_dates(required_dates)

        return self.df.loc[self.df.index.isin(required_dates)].copy()


import os
import pickle
import pandas as pd
import datetime as dt
import requests
from utils import QualityIndexStore, get_day_df



class OverviewDatenManager:
    def __init__(self, standorte, pickle_path=f"{ROOT_PATH}overview.pkl"):
        self.standorte = standorte
        self.pickle_path = pickle_path
        self.df = self._load_or_initialize_df()

    def _load_or_initialize_df(self):
        if os.path.exists(self.pickle_path):
            with open(self.pickle_path, "rb") as f:
                return pickle.load(f)
        else:
            return pd.DataFrame()

    def _save_df(self):
        with open(self.pickle_path, "wb") as f:
            pickle.dump(self.df, f)

    def _get_general_data(self, standort: str) -> pd.DataFrame:
        url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{standort}/visualisierung/base_vars.js"
        response = requests.get(url)
        key_value_list = [
            line[4:].split("=")
            for line in response.text.split("\n")
            if line.startswith("var ")
        ]
        df = pd.DataFrame(key_value_list, columns=["key", "value"]).set_index("key").T
        return df

    def _process_quality_data(self, standort: str) -> pd.DataFrame:
        quality = QualityIndexStore(standort, days_back=30).get_data().mean().reset_index()
        if quality.empty:
            return pd.DataFrame()
        quality_grouped = (
            quality[0]
            .groupby(quality["index"].str.split("_").str[0])
            .mean()
            .reset_index()
            .T
        )
        column_names = quality_grouped.iloc[0]
        data = quality_grouped[1:]
        data.columns = column_names
        return data

    def _get_last_day_data(self, standort: str, date: str) -> pd.DataFrame:
        return get_day_df(standort, date)

    def _build_entries(self, standort: str, general_df: pd.DataFrame, quality_df: pd.DataFrame, last_day_df: pd.DataFrame) -> list[dict]:
        eintraege = []
        max_leistung_kwp = f"{int(general_df['AnlagenKWP'].iloc[0]) / 1000} kWp"
        standort_name = general_df["HPStandort"].iloc[0].strip().strip('"')

        if quality_df.empty:
            eintraege.append({
                "s": standort,
                "Standort": standort_name,
                "Max. Leistung": max_leistung_kwp,
                "Wechselrichter": "--",
                "letzter Tag": [],
                "Datenqualität": 0,
                **general_df.to_dict(orient="records")[0]
            })
        else:
            for wr in quality_df.columns:
                eintraege.append({
                    "s": standort,
                    "Standort": standort_name,
                    "Max. Leistung": max_leistung_kwp,
                    "Wechselrichter": wr,
                    "letzter Tag": last_day_df.get(wr + "_P", pd.Series([])).values.tolist()
                        if isinstance(last_day_df, pd.DataFrame) else [],
                    "Datenqualität": quality_df[wr].iloc[0],
                    **general_df.to_dict(orient="records")[0]
                })
        return eintraege

    def _build_df_from_scratch(self):
        """Hilfsfunktion: erstellt das gesamte DataFrame frisch"""
        all_entries = []
        date_str = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%y%m%d")

        for standort in self.standorte:
            general_df = self._get_general_data(standort)
            quality_df = self._process_quality_data(standort)
            last_day_df = self._get_last_day_data(standort, date_str)
            entries = self._build_entries(standort, general_df, quality_df, last_day_df)
            all_entries.extend(entries)

        return pd.DataFrame(all_entries).fillna(0)

    def update_quality_only(self):
        """Aktualisiert nur die Qualitätsdaten"""
        if self.df.empty:
            self.df = self._build_df_from_scratch()

        for idx, row in self.df.iterrows():
            standort = row["s"]
            wr = row["Wechselrichter"]
            if wr == "--":
                continue
            quality_df = self._process_quality_data(standort)
            if wr in quality_df.columns:
                self.df.at[idx, "Datenqualität"] = quality_df[wr].iloc[0]

        self._save_df()

    def update_last_day_only(self):
        """Aktualisiert nur die Daten des letzten Tages"""
        if self.df.empty:
            self.df = self._build_df_from_scratch()

        date_str = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%y%m%d")
        #date_str = dt.datetime.now().strftime("%y%m%d")
        for idx, row in self.df.iterrows():
            standort = row["s"]
            wr = row["Wechselrichter"]
            if wr == "--":
                continue
            last_day_df = self._get_last_day_data(standort, date_str)
            if isinstance(last_day_df, pd.DataFrame) and wr + "_P" in last_day_df.columns:
                self.df.at[idx, "letzter Tag"] = last_day_df[wr + "_P"].values.tolist()[::-1]

        self._save_df()

    def get_dataframe(self) -> pd.DataFrame:
        """Lädt das DataFrame oder erzeugt es, falls es noch nicht existiert"""
        if self.df.empty:
            # 👉 automatisch initial aufbauen, wenn leer
            self.df = self._build_df_from_scratch()
            self._save_df()

        return self.df.copy()