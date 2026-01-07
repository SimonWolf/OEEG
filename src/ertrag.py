import re
from datetime import datetime
import pandas as pd
import requests
import os 


def _parse_date(ddmm_string):
    """Konvertiert 'dd.mm.yy' oder 'dd.mm.yyyy' -> 'YYYY-MM-DD' (ISO)"""
    s = ddmm_string.strip()
    try:
        if re.match(r'^\d{2}\.\d{2}\.\d{2}$', s):
            return datetime.strptime(s, '%d.%m.%y').date().isoformat()
        else:
            return datetime.strptime(s, '%d.%m.%Y').date().isoformat()
    except Exception:
        # falls unbekanntes Format: original zurückgeben
        return s

def parse_js_text(text, standort='Esslingen'):
    """
    Parst Text mit Zeilen wie:
    da[dx++]="13.06.23|4500;0|1905;0|1668;0"
    -> DataFrame long format mit Spalten: date, standort, wr, value
    wr wird als 'WR1','WR2',... bezeichnet.
    """
    rows = []
    # alle "..." Inhalte extrahieren (darin sind die records)
    matches = re.findall(r'"([^"]+)"', text)
    for m in matches:
        parts = m.split('|')
        if not parts:
            continue
        date_iso = _parse_date(parts[0])
        # alle folgenden tokens sind "value;0" - wir nehmen nur den value-Teil vor dem ';'
        for i, token in enumerate(parts[1:], start=1):
            token = token.strip()
            if token == '':
                continue
            val = token.split(';')[0]
            # versuche int, sonst float, sonst None
            try:
                val_num = int(val)
            except ValueError:
                try:
                    val_num = float(val.replace(',', '.'))
                except Exception:
                    val_num = None
            rows.append({
                'date': date_iso,
                'standort': standort,
                'wr': i,
                'value': val_num
            })
    df = pd.DataFrame(rows, columns=['date', 'standort', 'wr', 'value'])
    # date in datetime umwandeln (wenn möglich) und sortieren (neueste zuerst)
    try:
        df['date'] = pd.to_datetime(df['date'])
        df["date"] = df["date"].dt.date
        df = df.sort_values(['date', 'wr'], ascending=[False, True]).reset_index(drop=True)
    except Exception:
        pass
    return df


def update_ertrag():
    standorte =  ["muensingen", "karlsruhe", "badboll", "mettingen", "holzgerlingen", "tuebingen", "hospitalhof"]
    new_data_pull = []
    for s in standorte:
        url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{s}/visualisierung/days_hist.js"
        response = requests.get(url)
        new_data_pull.append(parse_js_text(response.text, standort=s))
        url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{s}/visualisierung/days.js"
        response = requests.get(url)
        new_data_pull.append(parse_js_text(response.text, standort=s))
    new_data_pull = pd.concat(new_data_pull) 

    if os.path.exists("data/ertrag.parquet"):

        old_data = pd.read_parquet("data/ertrag.parquet")
  
        final = pd.concat([new_data_pull,old_data]).drop_duplicates(subset=["date","standort","wr"],keep="first").sort_values(by="date")
        
        final.to_parquet("data/ertrag.parquet",index=False)
    else:
        new_data_pull.drop_duplicates(subset=["date","standort","wr"]).sort_values(by="date").to_parquet("data/ertrag.parquet",index=False)

    print("Ertragsdaten aktualisiert!")