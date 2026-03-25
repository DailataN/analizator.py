# Analizator danych pacjentów

Aplikacja desktopowa w Pythonie (PyQt5) służąca do analizy danych z plików CSV i Excel.

## Funkcjonalności

- wczytywanie danych (CSV, Excel)
- filtrowanie danych (AND / OR)
- analiza statystyczna (mean, median, min, max, std)
- wizualizacja danych (histogram, wykres rozrzutu)
- eksport danych do CSV
- eksport raportu do PDF

## Pipeline przetwarzania danych

1. Import danych:
   - pliki CSV
   - pliki Excel
   - baza danych SQLite (SQL)

2. Walidacja danych:
   - sprawdzenie pustych danych
   - identyfikacja braków i błędów

3. Czyszczenie danych:
   - usuwanie spacji
   - konwersja wartości liczbowych
   - ujednolicenie formatów

4. Filtrowanie:
   - operatory: =, >, <, >=, <=
   - warunki tekstowe (zawiera / nie zawiera)
   - logika AND / OR

5. Analiza statystyczna:
   - count, mean, median, min, max, std
   - grupowanie danych

6. Wizualizacja:
   - histogram
   - wykres rozrzutu

7. Analiza wpływu parametrów:
   - porównanie liczby rekordów przed i po filtracji
   - ocena wpływu parametrów na wyniki

8. Eksport:
   - CSV
   - PDF (raport)

## Struktura projektu

- `ui/` – interfejs użytkownika (PyQt5)
- `data/` – wczytywanie, walidacja i czyszczenie danych
- `analysis/` – statystyki i wizualizacja
- `export/` – eksport raportów

## Technologie

- Python
- PyQt5
- pandas
- matplotlib
- reportlab

## Uruchomienie

1. Zainstaluj wymagane biblioteki:
pip install pandas matplotlib pyqt5 reportlab openpyxl
2. Uruchom aplikację:
python main.py

## Autor
Projekt wykonany jako aplikacja egzaminacyjna.