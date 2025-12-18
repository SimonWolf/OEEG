import re
import polars as pl
from itertools import combinations


def compute_final_for_standort(standort: str, deltalake_path: str = "./delta-table/") -> pl.DataFrame:
    dl = pl.scan_delta(deltalake_path)
    filtered = dl.filter(
        (pl.col("standort") == standort)
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
            ((pl.col(c) == 0) & (pl.sum_horizontal(other_cols) != 0)).sum().alias(f"{c}_zero_count")
        )

    # total_count nur für Zeilen, bei denen mindestens ein Wert != 0
    total_count_expr = (pl.any_horizontal([pl.col(c) != 0 for c in columns])).sum().alias("total_count")

    # Gruppieren nach Datum: Korrelationen + Zero-Counts + total_count
    date_groups = (
        pivot_like.group_by("date")
        .agg(
            corr_exprs
            + zero_count_exprs
            + [total_count_expr]
        )
    )

    # Zero-Fraction berechnen
    for c in columns:
        date_groups = date_groups.with_columns(
            (1-pl.col(f"{c}_zero_count") / pl.col("total_count")).fill_nan(0).alias(f"{c}_availability")
        )

    # total_count skalieren (0 bis Maximum)
    date_groups = date_groups.with_columns(
        (pl.col("total_count") / pl.col("total_count").max()).fill_nan(0).alias("total_availability")
    )

    # Alle Spaltennamen für spätere Verarbeitung
    cols = date_groups.collect_schema().names()

    # Matching-Spalten für Fehlerberechnung
    new_exprs = []
    for t in unique_wr:
        # nur Korrelationen, die die Nummer t enthalten
        matching = [c for c in cols if c.startswith("corr_") and re.search(rf"_{t}(_|$)", c)]
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
            pl.mean_horizontal([pl.col(c) for c in error_cols]).alias("mean_correlation")
        )
        .collect()
    )

    return final
