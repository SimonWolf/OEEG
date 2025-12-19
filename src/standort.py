import pandas as pd
from pvlib.location import Location
from functools import lru_cache
from datetime import date
import polars as pl
from calendar import monthrange
import numpy as np
from itertools import combinations
import re
from src.leistung import Leistung

PATH_META = "data/allgemein.csv"
PATH_ERTRAG = "data/ertrag.parquet"
PATH_DELTA = "data/delta-table/"
CACHE_SIZE = 32

META = pd.read_csv(PATH_META)

class Standort:
    def __init__(
        self,
        standort: str,
    ):
        self.standort = standort
        self.meta = self.__get_meta_data()
        self.leistung = Leistung()
        return None

    
    def __get_meta_data(self):
        meta = META.loc[META.id == self.standort].iloc[0].to_dict()
        return meta

    @lru_cache(maxsize=CACHE_SIZE)
    def calculate_sunrise_times(self, datum: date):
        """Berechne Sonnenaufgang und -untergang."""
        location = Location(
            self.meta["lat"],
            self.meta["lon"],
            tz=self.meta["tz"],
            altitude=self.meta["alt"],
        )
        times_for_sun = pd.DatetimeIndex(
            [datum + pd.Timedelta(hours=24)], tz=self.meta["tz"]
        )
        sun_df = location.get_sun_rise_set_transit(times_for_sun, method="spa")
        #round to seconds
        sun_df["sunrise"] = sun_df["sunrise"].dt.round("s")
        sun_df["sunset"] = sun_df["sunset"].dt.round("s")
        return sun_df["sunrise"].iloc[0], sun_df["sunset"].iloc[0]

    ##############################################################################################################
    ## Leistungs-Daten:
    def load_total_power_of_day(self, datum: date, ttl_hash=None) -> pd.DataFrame:
        df_polars = self.leistung.get_day_and_update(self.standort, datum)
        return (
            df_polars
            .filter((pl.col("string") == -1) & (pl.col("sensor") == "P"))
            .group_by("Datetime")
            .agg(pl.col("value").sum().alias("P_gesamt"))
            .sort("Datetime")
            .collect(engine="streaming")
            .to_pandas()
        )

    def load_wr_power_of_day(self, datum: date, ttl_hash=None) -> pd.DataFrame:
        df_polars = self.leistung.get_day_and_update(self.standort, datum)
        return (
            df_polars.filter((pl.col("string") == -1) & (pl.col("sensor") == "P"))
            # .pivot(on="wr",on_columns=df_polars.select("wr").unique().sort(by="wr").collect(),index="Datetime",values="value")
            .sort("Datetime")
            .collect(engine="streaming")
            .to_pandas()
        )

    def load_string_power_of_day(self, datum: date, ttl_hash=None) -> pd.DataFrame:
        df_polars = self.leistung.get_day_and_update(self.standort, datum)
        return (
            df_polars.filter((pl.col("string") != -1) & (pl.col("sensor") == "P"))
            .sort("Datetime")
            .collect(engine="streaming")
            .to_pandas()
        )

    ##############################################################################################################
    ## Ertrags-Daten:

    @lru_cache
    def load_daily_yield_this_month(self):
        data_polars = pl.scan_parquet(PATH_ERTRAG)

        heute = date.today()
        akt_jahr = heute.year
        akt_monat = heute.month
        # Anzahl Tage im aktuellen Monat
        days_in_month = monthrange(akt_jahr, akt_monat)[1]

        df_monat = (
            data_polars.filter(
                (pl.col("standort").str.to_lowercase() == self.standort)
                & (pl.col("date").dt.year() == akt_jahr)
                & (pl.col("date").dt.month() == akt_monat)
            )
            .group_by(["standort", "date"])
            .agg(pl.col("value").sum().alias("value_sum") / 1000)
            .sort("date")  # optional: nach Datum sortieren
            .collect(engine="streaming")
        )

        numpy_array = df_monat.to_pandas()["value_sum"].values
        # Array auffüllen bis zur Länge des Monats
        if len(numpy_array) < days_in_month:
            fill_length = days_in_month - len(numpy_array)
            numpy_array = np.pad(
                numpy_array, (0, fill_length), "constant", constant_values=0
            )

        # Als Liste zurückgeben
        return np.round(numpy_array, 1)

    @lru_cache
    def load_monthly_yield_this_year(self):
        data_polars = pl.scan_parquet(PATH_ERTRAG)

        heute = date.today()
        akt_jahr = heute.year

        # Daten für das aktuelle Jahr filtern
        df_jahr = (
            data_polars.filter(
                (pl.col("standort").str.to_lowercase() == self.standort.lower())
                & (pl.col("date").dt.year() == akt_jahr)
            )
            .with_columns(
                [
                    pl.col("date").dt.month().alias("month")  # Monat extrahieren
                ]
            )
            .group_by("month")
            .agg(
                (pl.col("value").sum() / 1000).alias("value_sum")  # kWh
            )
            .sort("month")
            .collect(engine="streaming")
        )

        # In ein dict für schnelles Auffüllen
        month_dict = {m: v for m, v in zip(df_jahr["month"], df_jahr["value_sum"])}

        # Array für 12 Monate erstellen
        ertrag_liste = [month_dict.get(i, 0) for i in range(1, 13)]

        # Runde auf 1 Nachkommastelle und als numpy Array zurückgeben
        return np.round(ertrag_liste, 1)

    @lru_cache
    def load_total_yield(self):
        data_polars = pl.scan_parquet(PATH_ERTRAG)

        # Filter nur nach Standort
        df = (
            data_polars.filter(
                pl.col("standort").str.to_lowercase() == self.standort.lower()
            )
            .select(
                (pl.col("value").sum() / 1000).alias("total_sum")  # Summe in kWh
            )
            .collect(engine="streaming")
        )

        total = df["total_sum"][0] if len(df) > 0 else 0
        return int(round(total, 0))  # gerundet als Integer

    @lru_cache
    def load_daily_yield_last_year(self):
        data_polars = pl.scan_parquet(PATH_ERTRAG)

        first_date = date.today() - pd.Timedelta(days=365)
    
        df_year = (
            data_polars.filter(
                (pl.col("standort").str.to_lowercase() == self.standort)
                & (pl.col("date") >= first_date)
            )
            .group_by(["date"])
            .agg(pl.col("value").sum().alias("value_sum") / 1000)
            .sort("date")  # optional: nach Datum sortieren
            .collect(engine="streaming")
            .to_pandas()
        )

        # resample to date from dirst_date to today and fill with 0
        all_dates = pd.date_range(start=first_date, end=date.today(), freq='D')
        df_year.set_index('date', inplace=True)
        df_year = df_year.reindex(all_dates, fill_value=0).rename_axis('date').reset_index()

        return df_year

    ##############################################################################################################
    ## Fehler-analyse:
    @lru_cache
    def calculate_error_statistics(self) -> pl.DataFrame:
        dl = pl.scan_delta(PATH_DELTA)
        filtered = dl.filter(
            (pl.col("standort") == self.standort)
            & (pl.col("string") == -1)
            & (pl.col("sensor") == "P")
        )

        unique_wr = (
            filtered.select(pl.col("wr")).unique().collect().to_series().to_list()
        )

        pivot_like = (
            filtered.group_by(pl.col("Datetime"))
            .agg(
                [
                    pl.col("value").filter(pl.col("wr") == v).max().alias(str(v))
                    for v in unique_wr
                ]
            )
            .sort("Datetime")
            .with_columns(pl.col("Datetime").dt.date().alias("date"))
        )

        columns = [str(v) for v in unique_wr]

        # Korrelationen zwischen allen Spalten
        corr_exprs = [
            pl.corr(pl.col(c1), pl.col(c2)).alias(f"corr_{c1}_{c2}")
            for c1, c2 in combinations(columns, 2)
        ]

        # Zero-Count nur, wenn andere Spalten ungleich 0 sind
        zero_count_exprs = []
        for c in columns:
            other_cols = [pl.col(col) for col in columns if col != c]
            zero_count_exprs.append(
                ((pl.col(c) == 0) & (pl.sum_horizontal(other_cols) != 0))
                .sum()
                .alias(f"{c}_zero_count")
            )

        # total_count nur für Zeilen, bei denen mindestens ein Wert != 0
        total_count_expr = (
            (pl.any_horizontal([pl.col(c) != 0 for c in columns]))
            .sum()
            .alias("total_count")
        )

        # Gruppieren nach Datum: Korrelationen + Zero-Counts + total_count
        date_groups = pivot_like.group_by("date").agg(
            corr_exprs + zero_count_exprs + [total_count_expr]
        )

        # Zero-Fraction berechnen
        for c in columns:
            date_groups = date_groups.with_columns(
                (1 - pl.col(f"{c}_zero_count") / pl.col("total_count"))
                .fill_nan(0)
                .alias(f"{c}_availability")
            )

        # total_count skalieren (0 bis Maximum)
        date_groups = date_groups.with_columns(
            (pl.col("total_count") / pl.col("total_count").max())
            .fill_nan(0)
            .alias("total_availability")
        )

        # Alle Spaltennamen für spätere Verarbeitung
        cols = date_groups.collect_schema().names()

        # Matching-Spalten für Fehlerberechnung
        new_exprs = []
        for t in unique_wr:
            # nur Korrelationen, die die Nummer t enthalten
            matching = [
                c for c in cols if c.startswith("corr_") and re.search(rf"_{t}(_|$)", c)
            ]
            if matching:
                new_exprs.append((t, matching))
        error_cols = [f"{t}_correlation" for t, _ in new_exprs]

        # Finale Berechnungen: Fehler-Median und Mittelwert
        final = (
            date_groups.with_columns(
                [
                    pl.max_horizontal([pl.col(c).fill_nan(0) for c in matching]).alias(
                        f"{t}_correlation"
                    )
                    for t, matching in new_exprs
                ]
            )
            .with_columns(
                pl.mean_horizontal([pl.col(c) for c in error_cols]).alias(
                    "mean_correlation"
                )
            )
            .collect().to_pandas()
        )
        # resample by 0 and fill missing  with 0 
        end = date.today()
        start = end - pd.Timedelta(days=365)
        all_dates = pd.date_range(start=start, end=end, freq='D')
        final.set_index('date', inplace=True)
        final = final.reindex(all_dates, fill_value=0).rename_axis('date').reset_index()
        
        return final
