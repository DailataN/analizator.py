import pandas as pd


def clean_dataframe(df):
    df = df.copy()

    # tylko kolumny tekstowe
    obj_cols = df.select_dtypes(include=["object"]).columns

    for col in obj_cols:
        series = df[col]

        # usuń białe znaki z początku i końca
        needs_strip = series.str.contains(r"^\s+|\s+$", regex=True, na=False).any()
        if needs_strip:
            series = series.str.strip()

        # zamień przecinek na kropkę TYLKO jeśli kolumna wygląda na numeryczną
        # (ponad 50% wartości daje się zamienić na liczbę)
        converted = pd.to_numeric(
            series.str.replace(",", ".", regex=False),
            errors="coerce"
        )
        if converted.notna().mean() > 0.5:
            series = series.str.replace(",", ".", regex=False)

        df[col] = series

    return df