# Analizator danych pacjentów

Aplikacja desktopowa w Pythonie (PyQt5) do analizy relacyjnych danych medycznych. Realizuje pełny pipeline analizy danych — od importu i walidacji, przez filtrowanie i zapytania SQL, aż po wizualizację i raport końcowy.

## Diagram przepływu danych

![Pipeline](docs/pipeline_diagram.png)

## Funkcjonalności

- wczytywanie danych: CSV, Excel, baza SQLite (5 tabel relacyjnych)
- walidacja i czyszczenie danych
- filtrowanie z operatorami =, >, <, >=, <=, zawiera / nie zawiera, logika AND / OR
- zapytania SQL z JOIN między tabelami (patients, medications, outcomes, diagnoses, lab_results)
- analiza statystyczna: count, mean, median, min, max, std, grupowanie
- wizualizacja: violin plot, histogram, bar chart, scatter plot, wykres liniowy
- analiza wpływu parametrów filtrowania na wyniki
- eksport do CSV i PDF z wykresem

## Pipeline przetwarzania danych

1. Import — CSV / Excel / SQLite
2. Walidacja — braki danych, puste kolumny, typy
3. Czyszczenie — spacje, separatory dziesiętne, formaty
4. Filtrowanie — operatory numeryczne i tekstowe, AND / OR
5. Zapytania SQL — JOIN między 5 tabelami, agregacje
6. Analiza statystyczna — metryki dla kolumn numerycznych i tekstowych
7. Wizualizacja — automatyczny dobór typu wykresu według typów danych
8. Analiza wpływu parametrów — porównanie przed/po filtrze
9. Eksport — CSV, PDF z wykresem i statystykami

## Schemat bazy danych

Baza SQLite zawiera 5 tabel połączonych przez `patient_id`:

Baza SQLite zawiera 5 tabel połączonych przez `patient_id`:

- `patients` — dane demograficzne i kliniczne (do testu: 100 000 pacjentów)
  - Klucze: patient_id (Text, not NULL)
  - Kolumny: medication (TEXT), dose (Real), unit (Text), frequency (Text), indication (Text), start_date (Text), duration_days (Int), is_generic (Int, Def.: 0), adherence_pct (Real)
                
- `medications` — leki i recepty (do testu: 364 174 rekordów)
  - Klucze: id (Int, Autoincrement), *patient_id* (Text, not NULL)
  - Kolumny: medication (Text), dose (Real), unit (Text), frequency (Text), indication (Text), start_date (Text), duration_days (Int), is_generic (Int, Def.: 0), adherence_pct (Real)
                
- `outcomes` — hospitalizacje i wyniki leczenia (do testu: 11 001 rekordów)
  - Klucze: id (Int), *patient_id* (Text, not NULL) 
  - Kolumny: admission_date (Text), discharge_date (Text), length_of_stay_days (Int), icu_admission (Int, Def.: 0), icu_days (Int, Def.: 0), in_hospital_death (Int, Def.: 0), discharge_disposition (Text), readmitted_30d (Int, Def.: 0), days_to_readmission (Real), primary_drg (Int), total_charges_usd (Real)
                
- `diagnoses` — wizyty z kodami ICD-10 (do testu: 274 592 rekordów)
  - Klucze: id (Int, Autoincrement), *patient_id* (Text, not NULL)
  - Kolumny: visit_date (Text), visit_type (Text), primary_diagnosis (Text), primary_icd10 (Text), secondary_diagnoses (Text), secondary_icd10s (Text), provider_specialty (Text), 
                
- `lab_results` — wyniki badań laboratoryjnych (do testu: 2 827 722 rekordów)
  - Klucze: id (Int, Autoincrement), *patient_id* (Text, not NULL)
  - Kolumny: patient_id (text, not NULL), test_date (Text), test_name (Text), value (Real), unit (Text), reference_low (Real), reference_high (Real), flag (Text), is_abnormal (Int, Def.: 0), delta_from_normal (Real)


Aby wygenerować bazę danych z plików CSV:
```bash
python csv_to_sqlite.py --input_dir ./dane --output baza_pacjentow.db
```

## Struktura projektu
analizator.py/
├── ui/                  # interfejs użytkownika (PyQt5)
├── data/                # loader, validator, cleaner, database
├── analysis/            # stats, visualization
├── export/              # eksport raportów
├── docs/                # diagram pipeline
├── csv_to_sqlite.py     # konwersja CSV → SQLite
└── main.py              # punkt startowy
## Technologie

| Technologia | Zastosowanie |
|---|---|
| Python 3.9+ | język główny |
| PyQt5 | interfejs graficzny |
| pandas | przetwarzanie danych |
| matplotlib | wizualizacja |
| SQLite | baza danych relacyjna |
| reportlab | generowanie PDF |

## Uruchomienie
```bash
pip install pandas matplotlib pyqt5 reportlab openpyxl
python main.py
```

Projekt wykonany jako aplikacja egzaminacyjna z analizy danych medycznych.
