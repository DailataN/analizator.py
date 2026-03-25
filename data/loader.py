import pandas as pd


def load_csv_file(filename):
    try:
        try:
            df = pd.read_csv(filename, sep=None, engine="python", on_bad_lines="skip")
        except Exception:
            df = pd.read_csv(filename, sep=";", engine="python", on_bad_lines="skip")
        return df
    except Exception as e:
        raise Exception(f"Nie udało się wczytać CSV: {e}")