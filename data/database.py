# =============================================================================
# IMPORT BIBLIOTEK
# =============================================================================
import sqlite3
import pandas as pd
import re


# =============================================================================
# FUNKCJA GŁÓWNA — WCZYTYWANIE TABELI Z BAZY DANYCH SQLITE
# Łączy się z bazą pod podaną ścieżką i zwraca całą tabelę jako DataFrame.
# Zawiera zabezpieczenie przed SQL injection przez walidację nazwy tabeli
# wyrażeniem regularnym przed wykonaniem zapytania.
# =============================================================================
def load_table_from_db(db_path, table_name):
    try:
        # --- WALIDACJA NAZWY TABELI (OCHRONA PRZED SQL INJECTION) ---
        # Dopuszczalne są tylko litery, cyfry, podkreślenia i spacje.
        # Każda inna nazwa jest odrzucana przed nawiązaniem połączenia z bazą.
        if not re.match(r'^[\w\s]+$', table_name):
            raise ValueError("Nieprawidłowa nazwa tabeli.")

        # --- POŁĄCZENIE Z BAZĄ I WYKONANIE ZAPYTANIA ---
        # Nazwa tabeli dodatkowo ujęta w cudzysłowy, co chroni przed
        # konfliktami ze słowami kluczowymi SQL i znakami specjalnymi.
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)

        return df

    # --- OBSŁUGA BŁĘDÓW ---
    # Wszelkie wyjątki (brak pliku, brak tabeli, błąd SQL) są przechwytywane
    # i przekazywane dalej z czytelnym komunikatem.
    except Exception as e:
        raise Exception(f"Błąd odczytu bazy danych: {e}")
