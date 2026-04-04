# =============================================================================
# IMPORT BIBLIOTEK
# =============================================================================
import pandas as pd


# =============================================================================
# FUNKCJA — WCZYTYWANIE PLIKU CSV Z AUTO-DETEKCJĄ SEPARATORA I KODOWANIA
# Próbuje wczytać plik CSV iterując po kombinacjach separatorów (;, ,)
# i kodowań znaków. Jeśli żadna kombinacja nie zwróci więcej niż jednej
# kolumny, uruchamia fallback z automatycznym wykrywaniem separatora.
# =============================================================================
def load_csv_file(filename):

    # --- LISTY OBSŁUGIWANYCH KODOWAŃ ---
    # Kolejność dobrana pod typowe pliki polskojęzyczne:
    # utf-8 → utf-8-sig (BOM) → iso-8859-2 → cp1250 (Windows)
    encodings = ["utf-8", "utf-8-sig", "iso-8859-2", "cp1250"]

    # --- PRÓBA WCZYTANIA Z OKREŚLONYM SEPARATOREM I KODOWANIEM ---
    # Zewnętrzna pętla: separator (średnik, potem przecinek)
    # Wewnętrzna pętla: kolejne kodowania
    # Plik jest uznany za poprawnie wczytany jeśli powstał DataFrame
    # z więcej niż jedną kolumną — co wyklucza błędny dobór separatora.
    for sep in [";", ","]:
        for enc in encodings:
            try:
                df = pd.read_csv(
                    filename,
                    sep=sep,
                    engine="c",           # szybki silnik C
                    encoding=enc,
                    low_memory=False,     # wyłącza ostrzeżenia o mieszanych typach
                    parse_dates=True,
                    infer_datetime_format=True
                )

                if len(df.columns) > 1:
                    return df
            except Exception:
                continue

    # --- FALLBACK: AUTOMATYCZNE WYKRYWANIE SEPARATORA ---
    # Uruchamiany jeśli żadna kombinacja powyżej nie zadziałała.
    # Używa silnika Python (wolniejszy, ale bardziej elastyczny).
    # Błędne wiersze są pomijane zamiast przerywać wczytywanie.
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


# =============================================================================
# FUNKCJA — WCZYTYWANIE PLIKU EXCEL
# Prosta funkcja opakowująca pd.read_excel z obsługą błędów.
# =============================================================================
def load_excel_file(filename):
    try:
        return pd.read_excel(filename)
    except Exception as e:
        raise Exception(f"Nie udało się wczytać Excel: {e}")
