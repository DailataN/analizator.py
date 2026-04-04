# =============================================================================
# IMPORT BIBLIOTEK
# =============================================================================
import pandas as pd


# =============================================================================
# FUNKCJA GŁÓWNA — CZYSZCZENIE DATAFRAME
# Operuje na kopii przekazanego DataFrame, aby nie modyfikować oryginału.
# Przetwarza wyłącznie kolumny tekstowe (dtype "object").
# Wykonuje dwa rodzaje czyszczenia:
#   1. Usuwanie białych znaków z początku i końca wartości (strip)
#   2. Zamianę przecinka na kropkę jako separatora dziesiętnego
#      — tylko w kolumnach, które wyglądają na numeryczne
# =============================================================================
def clean_dataframe(df):
    df = df.copy()

    # --- WYBÓR KOLUMN TEKSTOWYCH DO PRZETWORZENIA ---
    obj_cols = df.select_dtypes(include=["object"]).columns

    for col in obj_cols:
        series = df[col]

        # --- USUWANIE BIAŁYCH ZNAKÓW (STRIP) ---
        # Sprawdza czy jakakolwiek wartość w kolumnie ma białe znaki
        # na początku lub końcu — jeśli tak, wykonuje strip na całej kolumnie.
        needs_strip = series.str.contains(r"^\s+|\s+$", regex=True, na=False).any()
        if needs_strip:
            series = series.str.strip()

        # --- ZAMIANA PRZECINKA NA KROPKĘ (SEPARATOR DZIESIĘTNY) ---
        # Próbuje skonwertować wartości po zamianie przecinka na kropkę.
        # Zamiana jest wykonywana tylko jeśli ponad 50% wartości
        # da się poprawnie sparsować jako liczba — zapobiega to błędnej
        # konwersji kolumn tekstowych zawierających przypadkowe przecinki.
        converted = pd.to_numeric(
            series.str.replace(",", ".", regex=False),
            errors="coerce"
        )
        if converted.notna().mean() > 0.5:
            series = series.str.replace(",", ".", regex=False)

        df[col] = series

    return df
