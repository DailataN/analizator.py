import pandas as pd


def load_csv_file(filename):
    encodings = ["utf-8", "utf-8-sig", "iso-8859-2", "cp1250"]

    for sep in [";", ","]:
        for enc in encodings:
            try:
                df = pd.read_csv(
                    filename,
                    sep=sep,
                    engine="c",
                    encoding=enc,
                    low_memory=False,
                    parse_dates=True,
                    infer_datetime_format=True
                )

                if len(df.columns) > 1:
                    return df
            except Exception:
                continue


    try:
        df = pd.read_csv(
            filename,
            sep=None,
            engine="python",
            on_bad_lines="skip"
        )
        return df
    except Exception as e:
        raise Exception(f"Nie udało się wczytać CSV: {e}")


def load_excel_file(filename):
    try:
        return pd.read_excel(filename)
    except Exception as e:
        raise Exception(f"Nie udało się wczytać Excel: {e}")