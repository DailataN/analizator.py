# =============================================================================
# FUNKCJA GŁÓWNA — WALIDACJA DATAFRAME
# Sprawdza poprawność wczytanego zbioru danych i zwraca listę błędów.
# Jeśli lista jest pusta, dane są uznawane za poprawne.
# Wykonuje trzy poziomy walidacji:
#   1. Brak danych (None)
#   2. Pusty DataFrame
#   3. Kolumny zawierające wyłącznie wartości NaN
# =============================================================================
def validate_dataframe(df):
    errors = []

    # --- SPRAWDZENIE CZY DANE ZOSTAŁY WCZYTANE ---
    # Jeśli df jest None, dalsza walidacja jest bezcelowa — zwracamy od razu.
    if df is None:
        errors.append("Nie wczytano danych.")
        return errors

    # --- SPRAWDZENIE CZY DATAFRAME NIE JEST PUSTY ---
    if df.empty:
        errors.append("Plik jest pusty.")

    # --- WYKRYWANIE KOLUMN CAŁKOWICIE PUSTYCH ---
    # Kolumna jest uznawana za pustą jeśli wszystkie jej wartości to NaN.
    empty_cols = [col for col in df.columns if df[col].isna().all()]
    if empty_cols:
        errors.append("Puste kolumny: " + ", ".join(empty_cols))

    return errors
