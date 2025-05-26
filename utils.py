from datetime import datetime
import requests
import pandas as pd
import re
from io import StringIO

def get_day_df(standort: str, date: str) -> pd.DataFrame | str:
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
    def __init__(self, standort, save_dir="data", days_back=60):
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