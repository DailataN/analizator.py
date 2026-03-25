# Analizator danych pacjentów

Aplikacja desktopowa w Pythonie (PyQt5) służąca do analizy danych z plików CSV i Excel.

## Funkcjonalności

- wczytywanie danych (CSV, Excel)
- filtrowanie danych (AND / OR)
- analiza statystyczna (mean, median, min, max, std)
- wizualizacja danych (histogram, wykres rozrzutu)
- eksport danych do CSV
- eksport raportu do PDF

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