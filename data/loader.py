import pandas as pd


def load_csv_file(filename):
    try:
        # Najpierw szybka próba (silnik C, separator ;)
        try:
            df = pd.read_csv(
                filename,
                sep=";",
                engine="c",
                encoding="utf-8",
                low_memory=False
            )
            return df
        except Exception:
            pass

        # Druga próba (przecinek)
        try:
            df = pd.read_csv(
                filename,
                sep=",",
                engine="c",
                encoding="utf-8",
                low_memory=False
            )
            return df
        except Exception:
            pass

        # Dopiero na końcu fallback (wolny)
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