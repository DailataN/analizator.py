import pandas as pd


def clean_dataframe(df):
    df = df.copy()

    # tylko kolumny tekstowe
    obj_cols = df.select_dtypes(include=["object"]).columns

    for col in obj_cols:
        series = df[col]

        # szybkie sprawdzenie czy warto coś robić
        needs_strip = series.str.contains(r"^\s+|\s+$", regex=True, na=False).any()
        needs_replace = series.str.contains(",", na=False).any()

        if needs_strip:
            series = series.str.strip()

        if needs_replace:
            series = series.str.replace(",", ".", regex=False)

        df[col] = series

    return df