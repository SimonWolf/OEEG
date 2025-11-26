import datetime as dt
import threading
import polars as pl
from deltalake import DeltaTable
import pandas as pd
from update_leistungsdaten import get_day_df_long
deltalake_path = "./delta-table/"
lock = threading.Lock()


def write_to_file(df,standort,date):
    with lock:
        pl.DataFrame(df).write_delta(deltalake_path,mode="append")
    print(f"--- [{threading.get_ident()}]:  {standort} - {date} - deltalake updated shape: {df.shape}")

def optimize():
    with lock:
        dt = DeltaTable(deltalake_path)
        before = len(dt.file_uris())
        dt.optimize.z_order(["Datetime","standort"])
        dt.optimize.compact()
        dt.vacuum(retention_hours=0,dry_run=False, enforce_retention_duration=False)
        after = len(dt.file_uris())
        print(f"[optimize]: Files before: {before}, after: {after}")

def get_day_and_update(standort, date) -> str:
    #check if date is today:
    if date == dt.datetime.now().date():
        #print("[getDay] Heute: get data and return. Kein speichern!")
        df = get_day_df_long(standort, date.strftime("%y%m%d"))
        print(f"[getDay]: {standort} - {date} - heute... Downloaded shape: {df.shape}") 
        return df
    else:
        #print("[getDay]: nicht Heute: Versuche Daten aus Deltalake zu laden!")
        try:
            #with lock:
            dl = pl.scan_delta(deltalake_path)
            df = dl.filter(
                (pl.col("Datetime").dt.date() == date) & (pl.col("standort") == standort)
            ).collect().to_pandas()
        except:
            df = pd.DataFrame()

        if df.shape[0]==1:
            #print(f"[getDay]: {standort} - {date} - SKIP: No data avalaible!")
            return pd.DataFrame()
        if df.shape[0]==0:
            #print("[getDay]: Download missing data")
            
            df = get_day_df_long(standort, date.strftime("%y%m%d"))
            if df.shape[0]==0 | df.shape[1]!=6:
                print(f"[getDay]: {standort} - {date} - Warning: No data avalaible!")
                df_empty = pd.DataFrame([{"Datetime": date,"wr": -1,"string": -1,"sensor": -1,"value": -1,"standort": standort}])
                df_empty["Datetime"] = pd.to_datetime(df_empty["Datetime"])
                df = df_empty
            threading.Thread(target=write_to_file, args=(df,standort,date), daemon=True).start()
            #print(f"[getDay]: {standort} - {date} - Downloaded shape: {df.shape}")
            return df
        else:
            #print("[getDay]: Kein Download notwendig. (alle Daten verfügbar)")

            return df

   

from tqdm import tqdm
standorte = ["badboll","esslingen","geislingen","holzgerlingen","hospitalhof",
                "karlsruhe","mettingen","muensingen","tuebingen","waiblingen"]

end = dt.datetime.now()
days_back = 50
start = end - dt.timedelta(days=days_back)
required_dates = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]

new_data = []
for s in standorte:
    missing_dates = required_dates
    for date in missing_dates:
       _ = get_day_and_update(s, date.date()) 
optimize()
