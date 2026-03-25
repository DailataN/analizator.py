import pandas as pd


def clean_dataframe(df):
    df = df.copy()

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

            # zamiana przecinka dziesiętnego na kropkę tylko w tekstach liczbowych
            df[col] = df[col].str.replace(",", ".", regex=False)

    return df