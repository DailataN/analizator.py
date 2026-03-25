def validate_dataframe(df):
    errors = []

    if df is None:
        errors.append("Nie wczytano danych.")
        return errors

    if df.empty:
        errors.append("Plik jest pusty.")

    empty_cols = [col for col in df.columns if df[col].isna().all()]
    if empty_cols:
        errors.append("Puste kolumny: " + ", ".join(empty_cols))

    return errors