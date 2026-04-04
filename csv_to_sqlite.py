# =============================================================================
# OPIS MODUŁU
# Skrypt konwertujący 5 plików CSV z danymi pacjentów do bazy SQLite.
#
# Schemat bazy:
#   patients    — dane demograficzne i kliniczne (tabela centralna)
#   medications — leki i recepty
#   outcomes    — hospitalizacje i wyniki leczenia
#   diagnoses   — wizyty z kodami ICD-10
#   lab_results — wyniki badań laboratoryjnych
#
# Użycie:
#   python csv_to_sqlite.py --input_dir ./dane --output baza_pacjentow.db
#
# Pliki CSV muszą znajdować się w folderze input_dir:
#   patients.csv, medications.csv, outcomes.csv, diagnoses.csv, lab_results.csv
# =============================================================================

# =============================================================================
# IMPORT BIBLIOTEK
# =============================================================================
import argparse
import sqlite3
import pandas as pd
import sys
from pathlib import Path


# =============================================================================
# KONFIGURACJA TABEL — SŁOWNIK TABLES
# Definiuje strukturę każdej z 5 tabel bazy danych:
#   file — nazwa pliku CSV źródłowego
#   pk   — nazwa klucza głównego (None jeśli tabela używa AUTOINCREMENT)
#   fk   — nazwa klucza obcego wskazującego na patients.patient_id
#   ddl  — polecenie CREATE TABLE z pełną definicją kolumn i typów
#
# Tabela patients jest tabelą centralną (bez klucza obcego).
# Pozostałe tabele posiadają klucz obcy patient_id → patients(patient_id).
# =============================================================================
TABLES = {
    "patients": {
        "file": "patients.csv",
        "pk": "patient_id",
        "fk": None,
        "ddl": """
            CREATE TABLE patients (
                patient_id                  TEXT PRIMARY KEY,
                age                         INTEGER,
                sex                         TEXT,
                bmi                         REAL,
                systolic_bp                 INTEGER,
                diastolic_bp                INTEGER,
                heart_rate                  INTEGER,
                temperature_f               REAL,
                smoking_status              TEXT,
                alcohol_use                 TEXT,
                exercise_level              TEXT,
                insurance_type              TEXT,
                charlson_index              INTEGER,
                dx_hypertension             INTEGER DEFAULT 0,
                dx_type2_diabetes           INTEGER DEFAULT 0,
                dx_hyperlipidemia           INTEGER DEFAULT 0,
                dx_obesity                  INTEGER DEFAULT 0,
                dx_coronary_artery_disease  INTEGER DEFAULT 0,
                dx_heart_failure            INTEGER DEFAULT 0,
                dx_atrial_fibrillation      INTEGER DEFAULT 0,
                dx_chronic_kidney_disease   INTEGER DEFAULT 0,
                dx_copd                     INTEGER DEFAULT 0,
                dx_asthma                   INTEGER DEFAULT 0,
                dx_depression               INTEGER DEFAULT 0,
                dx_anxiety                  INTEGER DEFAULT 0,
                dx_hypothyroidism           INTEGER DEFAULT 0,
                dx_osteoarthritis           INTEGER DEFAULT 0,
                dx_type1_diabetes           INTEGER DEFAULT 0
            )
        """
    },
    "medications": {
        "file": "medications.csv",
        "pk": None,
        "fk": "patient_id",
        "ddl": """
            CREATE TABLE medications (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id    TEXT NOT NULL,
                medication    TEXT,
                dose          REAL,
                unit          TEXT,
                frequency     TEXT,
                indication    TEXT,
                start_date    TEXT,
                duration_days INTEGER,
                is_generic    INTEGER DEFAULT 0,
                adherence_pct REAL,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        """
    },
    "outcomes": {
        "file": "outcomes.csv",
        "pk": None,
        "fk": "patient_id",
        "ddl": """
            CREATE TABLE outcomes (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id            TEXT NOT NULL,
                admission_date        TEXT,
                discharge_date        TEXT,
                length_of_stay_days   INTEGER,
                icu_admission         INTEGER DEFAULT 0,
                icu_days              INTEGER DEFAULT 0,
                in_hospital_death     INTEGER DEFAULT 0,
                discharge_disposition TEXT,
                readmitted_30d        INTEGER DEFAULT 0,
                days_to_readmission   REAL,
                primary_drg           INTEGER,
                total_charges_usd     REAL,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        """
    },
    "diagnoses": {
        "file": "diagnoses.csv",
        "pk": None,
        "fk": "patient_id",
        "ddl": """
            CREATE TABLE diagnoses (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id          TEXT NOT NULL,
                visit_date          TEXT,
                visit_type          TEXT,
                primary_diagnosis   TEXT,
                primary_icd10       TEXT,
                secondary_diagnoses TEXT,
                secondary_icd10s    TEXT,
                provider_specialty  TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        """
    },
    "lab_results": {
        "file": "lab_results.csv",
        "pk": None,
        "fk": "patient_id",
        "ddl": """
            CREATE TABLE lab_results (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id        TEXT NOT NULL,
                test_date         TEXT,
                test_name         TEXT,
                value             REAL,
                unit              TEXT,
                reference_low     REAL,
                reference_high    REAL,
                flag              TEXT,
                is_abnormal       INTEGER DEFAULT 0,
                delta_from_normal REAL,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        """
    }
}


# =============================================================================
# KONFIGURACJA INDEKSÓW
# Lista poleceń CREATE INDEX dla kluczy obcych i często filtrowanych kolumn.
# Indeksy na patient_id przyspieszają operacje JOIN między tabelami.
# Dodatkowe indeksy na test_name, primary_icd10 i medication
# wspierają filtrowanie po wartościach klinicznych.
# =============================================================================
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_med_patient  ON medications(patient_id)",
    "CREATE INDEX IF NOT EXISTS idx_out_patient  ON outcomes(patient_id)",
    "CREATE INDEX IF NOT EXISTS idx_diag_patient ON diagnoses(patient_id)",
    "CREATE INDEX IF NOT EXISTS idx_lab_patient  ON lab_results(patient_id)",
    "CREATE INDEX IF NOT EXISTS idx_lab_test     ON lab_results(test_name)",
    "CREATE INDEX IF NOT EXISTS idx_diag_icd10   ON diagnoses(primary_icd10)",
    "CREATE INDEX IF NOT EXISTS idx_med_name     ON medications(medication)",
]


# =============================================================================
# FUNKCJA — WCZYTYWANIE PLIKU CSV Z AUTO-DETEKCJĄ
# Iteruje po kombinacjach separatorów (,  ;) i kodowań.
# Plik uznawany za poprawny jeśli powstał DataFrame z więcej niż 1 kolumną.
# Fallback: silnik Python z automatycznym wykrywaniem separatora.
# =============================================================================
def load_csv(path: Path) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "iso-8859-2", "cp1250"]
    for sep in [",", ";"]:
        for enc in encodings:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, low_memory=False)
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue
    return pd.read_csv(path, sep=None, engine="python", on_bad_lines="skip")


# =============================================================================
# FUNKCJA — SPRAWDZENIE OBECNOŚCI PLIKÓW CSV
# Weryfikuje czy wszystkie pliki zdefiniowane w TABLES istnieją w input_dir.
# Jeśli któregoś brakuje — wypisuje listę brakujących i kończy skrypt (exit 1).
# Zwraca słownik {nazwa_tabeli: Path do pliku CSV}.
# =============================================================================
def check_files(input_dir: Path) -> dict:
    file_paths = {}
    missing = []
    for table, cfg in TABLES.items():
        path = input_dir / cfg["file"]
        if not path.exists():
            missing.append(cfg["file"])
        else:
            file_paths[table] = path
    if missing:
        print(f"\nBrakujące pliki w folderze '{input_dir}':")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)
    return file_paths


# =============================================================================
# FUNKCJA — TWORZENIE BAZY DANYCH I WSTAWIANIE DANYCH
# Wykonuje pełny proces budowania bazy SQLite:
#   1. Ustawia PRAGMA (klucze obce, WAL journal, synchronous NORMAL)
#   2. Usuwa istniejące tabele w odwrotnej kolejności (respektuje FK)
#   3. Tworzy tabele wg DDL ze słownika TABLES
#   4. Wczytuje każdy CSV i wstawia dane przez pandas to_sql()
#      — kolumna "id" usuwana jeśli istnieje (AUTOINCREMENT w DDL)
#   5. Tworzy wszystkie indeksy z listy INDEXES
# Zwraca słownik {nazwa_tabeli: liczba_wierszy}.
# =============================================================================
def build_database(file_paths: dict, db_path: str) -> dict:
    stats = {}

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")

        # Usunięcie istniejących tabel w odwrotnej kolejności (zachowanie integralności FK)
        for table in reversed(list(TABLES.keys())):
            conn.execute(f"DROP TABLE IF EXISTS {table}")

        # Tworzenie tabel według DDL
        for table, cfg in TABLES.items():
            conn.execute(cfg["ddl"])

        # Wczytywanie CSV i wstawianie danych
        for table, cfg in TABLES.items():
            path = file_paths[table]
            print(f"  Wczytywanie {cfg['file']}...")
            df = load_csv(path)

            # Usunięcie kolumny "id" z CSV — baza generuje ją przez AUTOINCREMENT
            if "id" in df.columns and cfg["pk"] != "id":
                df = df.drop(columns=["id"])

            df.to_sql(table, conn, if_exists="append", index=False)
            stats[table] = len(df)
            print(f"  OK {table}: {len(df):,} wierszy")

        # Tworzenie indeksów
        print("\n  Tworzenie indeksów...")
        for idx_sql in INDEXES:
            conn.execute(idx_sql)

        conn.commit()

    return stats


# =============================================================================
# FUNKCJA — WERYFIKACJA BAZY PRZEZ PRZYKŁADOWE ZAPYTANIA JOIN
# Wykonuje 3 testowe zapytania SQL sprawdzające poprawność relacji
# między tabelami i integralność danych po imporcie:
#   1. Pacjenci >70 lat z lekami (JOIN patients + medications)
#   2. Nieprawidłowe wyniki lab z diagnozami (JOIN lab_results + diagnoses)
#   3. Adherencja vs rehospitalizacja z agregacją (JOIN medications + outcomes)
# =============================================================================
def verify_database(db_path: str) -> None:
    queries = {
        "Pacjenci z lekami (JOIN 2 tabel)": """
            SELECT p.patient_id,
                   p.age,
                   m.medication,
                   m.dose,
                   m.adherence_pct
            FROM   patients p
            JOIN   medications m ON m.patient_id = p.patient_id
            WHERE  p.age > 70
            LIMIT  5
        """,
        "Nieprawidlowe wyniki lab z diagnozami (JOIN 2 tabel)": """
            SELECT l.patient_id,
                   l.test_name,
                   l.value,
                   l.flag,
                   d.primary_diagnosis
            FROM   lab_results l
            JOIN   diagnoses   d ON d.patient_id = l.patient_id
            WHERE  l.is_abnormal = 1
            LIMIT  5
        """,
        "Adherencja vs rehospitalizacja (JOIN 2 tabel, agregacja)": """
            SELECT m.medication,
                   ROUND(AVG(m.adherence_pct), 2) AS avg_adherence,
                   SUM(o.readmitted_30d)           AS readmissions,
                   COUNT(*)                        AS n
            FROM   medications m
            JOIN   outcomes    o ON o.patient_id = m.patient_id
            GROUP  BY m.medication
            ORDER  BY readmissions DESC
            LIMIT  5
        """
    }

    with sqlite3.connect(db_path) as conn:
        for title, sql in queries.items():
            print(f"\n  --- {title} ---")
            try:
                df = pd.read_sql_query(sql, conn)
                print(df.to_string(index=False))
            except Exception as e:
                print(f"  Blad: {e}")


# =============================================================================
# PUNKT WEJŚCIA SKRYPTU — FUNKCJA MAIN
# Parsuje argumenty wiersza poleceń (--input_dir, --output),
# a następnie wykonuje kolejne kroki konwersji z komunikatami postępu:
#   [1/4] Sprawdzenie plików CSV
#   [2/4] Budowanie bazy danych
#   [3/4] Podsumowanie liczby wierszy na tabelę
#   [4/4] Weryfikacja przez zapytania JOIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Konwertuje 5 plikow CSV z danymi pacjentow do bazy SQLite."
    )
    parser.add_argument(
        "--input_dir", required=True,
        help="Folder z plikami CSV (patients.csv, medications.csv, itd.)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Sciezka do pliku wyjsciowego SQLite (.db)"
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    db_path   = args.output

    if not input_dir.is_dir():
        print(f"Blad: folder '{input_dir}' nie istnieje.")
        sys.exit(1)

    print(f"\n[1/4] Sprawdzanie plikow w: {input_dir}")
    file_paths = check_files(input_dir)
    print("  Wszystkie pliki znalezione.")

    print("\n[2/4] Tworzenie bazy danych...")
    stats = build_database(file_paths, db_path)

    print(f"\n[3/4] Podsumowanie:")
    total = sum(stats.values())
    for table, count in stats.items():
        print(f"  {table:<15} {count:>10,} wierszy")
    print(f"  {'RAZEM':<15} {total:>10,} wierszy")

    print("\n[4/4] Weryfikacja - przykladowe zapytania JOIN:")
    verify_database(db_path)

    print(f"\nGotowe! Baza zapisana jako: {db_path}\n")
    print("Przyklad uzycia w aplikacji:")
    print(f"  Wybierz 'Wczytaj z bazy SQL' -> wskaż plik '{db_path}'")
    print("  Dostepne tabele: patients, medications, outcomes, diagnoses, lab_results\n")


# =============================================================================
# WYWOŁANIE SKRYPTU
# =============================================================================
if __name__ == "__main__":
    main()