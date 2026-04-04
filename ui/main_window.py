# =============================================================================
# IMPORT BIBLIOTEK — MODUŁY WEWNĘTRZNE
# =============================================================================
from ui.table_model import DataFrameTableModel
from data.loader import load_csv_file, load_excel_file
from data.validator import validate_dataframe
from data.cleaner import clean_dataframe
from data.database import load_table_from_db
from analysis.stats import calculate_selected_stats, compare_filter_impact, analyze_filter_impact
from analysis.visualization import create_plot

# =============================================================================
# IMPORT BIBLIOTEK — BIBLIOTEKI ZEWNĘTRZNE
# =============================================================================
import io
import pandas as pd
import sqlite3
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt

from datetime import datetime

# =============================================================================
# IMPORT BIBLIOTEK — NARZĘDZIA GUI (PyQt5)
# =============================================================================
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QTextEdit, QFrame, QSplitter, QFileDialog, QLineEdit,
    QMessageBox, QAction, QComboBox, QListWidget, QListWidgetItem,
    QRadioButton, QButtonGroup, QCheckBox, QInputDialog, QTableView, QDialog,
    QApplication
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


# =============================================================================
# WĄTEK DO WCZYTYWANIA PLIKÓW (QThread)
# Wczytywanie plików odbywa się w osobnym wątku, dzięki czemu GUI nie
# zamraża się podczas ładowania dużych zbiorów danych.
# Emituje sygnały: progress (komunikat tekstowy), finished (df + błędy),
# error (komunikat błędu).
# Pipeline wątku: wczytanie → walidacja → czyszczenie → emit finished.
# =============================================================================
class FileLoaderThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, filename=None, db_path=None, table_name=None):
        super().__init__()
        self.filename = filename
        self.db_path = db_path
        self.table_name = table_name

    def run(self):
        try:
            if self.db_path:
                self.progress.emit(f"Wczytywanie tabeli '{self.table_name}' z bazy...")
                df = load_table_from_db(self.db_path, self.table_name)
            elif self.filename.lower().endswith(".xlsx"):
                self.progress.emit("Wczytywanie pliku Excel...")
                df = load_excel_file(self.filename)
            else:
                self.progress.emit("Wczytywanie pliku CSV...")
                df = load_csv_file(self.filename)

            self.progress.emit("Walidacja danych...")
            errors = validate_dataframe(df)

            self.progress.emit("Czyszczenie danych...")
            df = clean_dataframe(df)

            self.finished.emit((df, errors))

        except Exception as e:
            self.error.emit(str(e))


# =============================================================================
# GŁÓWNE OKNO APLIKACJI
# Klasa AnalizatorCSV dziedziczy po QMainWindow i stanowi centralny punkt
# całej aplikacji. Zarządza stanem danych (df, df_filtered), układem GUI,
# zakładkami oraz logiką wszystkich funkcji analitycznych.
# =============================================================================
class AnalizatorCSV(QMainWindow):

    # -------------------------------------------------------------------------
    # INICJALIZACJA OKNA
    # Ustawia tytuł, rozmiar i inicjalizuje wszystkie zmienne stanu:
    #   df            — surowe dane po wczytaniu
    #   df_filtered   — dane po zastosowaniu filtrów
    #   last_fig      — ostatnia figura matplotlib (do powiększenia/eksportu)
    #   canvas        — widget wykresu osadzony w zakładce
    #   filters       — lista aktywnych warunków filtrowania
    #   loader_thread — referencja do wątku wczytywania
    # -------------------------------------------------------------------------
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analizator danych pacjentów")
        self.setGeometry(100, 100, 1280, 760)

        self.df = None
        self.df_filtered = None
        self.last_fig = None
        self.canvas = None
        self.filters = []
        self.loader_thread = None

        self.initUI()

    # =========================================================================
    # BUDOWANIE INTERFEJSU UŻYTKOWNIKA
    # Metoda initUI() tworzy cały układ graficzny aplikacji:
    #   - pasek menu
    #   - panel boczny z przyciskami
    #   - zakładki: Podgląd, Filtry, Statystyki, Wizualizacja, Analiza progów
    #   - panel logów na dole okna
    #   - połączenia sygnałów z metodami (slots)
    # =========================================================================
    def initUI(self):

        # --- PASEK MENU ---
        # Menu "Plik": wczytaj plik, wyjście
        # Menu "Eksport": eksport PDF i CSV
        menubar = self.menuBar()

        menu_plik = menubar.addMenu("Plik")
        action_wczytaj = QAction("Wczytaj plik", self)
        action_wczytaj.triggered.connect(self.load_file)
        menu_plik.addAction(action_wczytaj)
        menu_plik.addSeparator()

        action_exit = QAction("Wyjście", self)
        action_exit.triggered.connect(self.close)
        menu_plik.addAction(action_exit)

        menu_eksport = menubar.addMenu("Eksport")

        action_pdf = QAction("Eksportuj raport PDF", self)
        action_pdf.triggered.connect(self.export_pdf)
        menu_eksport.addAction(action_pdf)

        action_csv = QAction("Eksportuj dane CSV", self)
        action_csv.triggered.connect(self.export_csv)
        menu_eksport.addAction(action_csv)

        # --- CENTRALNY UKŁAD OKNA ---
        # Splitter poziomy dzieli okno na panel boczny (przyciski) i zakładki.
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)

        # --- PANEL BOCZNY Z PRZYCISKAMI NAWIGACJI ---
        # Każdy przycisk odpowiada jednej funkcji lub zakładce aplikacji.
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        self.btn_load = QPushButton("📂 Wczytaj plik")
        self.btn_load_sql = QPushButton("🗄️ Wczytaj z bazy SQL")
        self.btn_filter = QPushButton("⚙️ Filtry")
        self.btn_stats = QPushButton("📊 Statystyki")
        self.btn_plot = QPushButton("📈 Wizualizacja")
        self.btn_threshold = QPushButton("🔬 Analiza progów")
        self.btn_compare = QPushButton("📉 Analiza wpływu filtrów")
        self.btn_export_csv = QPushButton("💾 Eksport CSV")
        self.btn_export_pdf = QPushButton("🧾 Eksport PDF")

        for b in [
            self.btn_load,
            self.btn_load_sql,
            self.btn_filter,
            self.btn_stats,
            self.btn_plot,
            self.btn_threshold,
            self.btn_compare,
            self.btn_export_csv,
            self.btn_export_pdf
        ]:
            b.setMinimumHeight(40)
            panel_layout.addWidget(b)

        panel_layout.addStretch()
        splitter.addWidget(panel)

        # --- WIDGET ZAKŁADEK ---
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        # =====================================================================
        # ZAKŁADKA 0: PODGLĄD DANYCH
        # Wyświetla wczytane dane w tabeli (QTableView z modelem DataFrameTableModel).
        # Etykieta pokazuje liczbę aktualnie wyświetlanych rekordów.
        # Włączone naprzemienne kolorowanie wierszy i ukryty nagłówek pionowy.
        # =====================================================================
        self.tab_data = QWidget()
        vbox_data = QVBoxLayout(self.tab_data)

        self.preview_label = QLabel("Podgląd danych: 0 z 0 rekordów")
        vbox_data.addWidget(self.preview_label)

        self.table = QTableView()
        self.table_model = DataFrameTableModel()
        self.table.setModel(self.table_model)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setDefaultSectionSize(24)

        vbox_data.addWidget(self.table)
        self.tabs.addTab(self.tab_data, "Podgląd danych")

        # =====================================================================
        # ZAKŁADKA 1: FILTRY
        # Pozwala budować warunki filtrowania w trybie AND/OR.
        # Dla kolumn tekstowych wyświetla listę rozwijaną z unikalnymi wartościami
        # (max 500). Dla kolumn numerycznych — pole tekstowe.
        # Warunki mogą być dodawane i usuwane pojedynczo.
        # =====================================================================
        self.tab_filter = QWidget()
        vbox_filter = QVBoxLayout(self.tab_filter)

        vbox_filter.addWidget(QLabel("Wybierz kolumnę:"))
        self.combo_col = QComboBox()
        vbox_filter.addWidget(self.combo_col)

        vbox_filter.addWidget(QLabel("Wybierz operator:"))
        self.combo_op = QComboBox()
        self.combo_op.addItems(["=", ">", "<", ">=", "<=", "zawiera", "nie zawiera"])
        vbox_filter.addWidget(self.combo_op)

        self.filter_value_label = QLabel("Wartość:")
        vbox_filter.addWidget(self.filter_value_label)

        # Pole tekstowe dla wartości numerycznych
        self.input_value = QLineEdit()
        self.input_value.setPlaceholderText("np. 50 lub 5,5")
        vbox_filter.addWidget(self.input_value)

        # Lista rozwijana dla wartości tekstowych (widoczna warunkowo)
        self.combo_value = QComboBox()
        self.combo_value.setVisible(False)
        vbox_filter.addWidget(self.combo_value)

        # Przyciski dodawania i usuwania warunków
        btn_condition_row = QHBoxLayout()
        self.btn_add_condition = QPushButton("Dodaj warunek")
        self.btn_remove_condition = QPushButton("Usuń zaznaczony")
        self.btn_remove_condition.setEnabled(False)
        btn_condition_row.addWidget(self.btn_add_condition)
        btn_condition_row.addWidget(self.btn_remove_condition)
        vbox_filter.addLayout(btn_condition_row)

        # Lista aktywnych warunków
        vbox_filter.addWidget(QLabel("Aktywne warunki:"))
        self.list_filters = QListWidget()
        vbox_filter.addWidget(self.list_filters)

        # Wybór logiki łączenia warunków: AND / OR
        hbox_logic = QHBoxLayout()
        hbox_logic.addWidget(QLabel("Łącz warunki za pomocą:"))

        self.radio_and = QRadioButton("AND")
        self.radio_or = QRadioButton("OR")
        self.radio_and.setChecked(True)

        self.logic_group = QButtonGroup(self)
        self.logic_group.addButton(self.radio_and)
        self.logic_group.addButton(self.radio_or)

        hbox_logic.addWidget(self.radio_and)
        hbox_logic.addWidget(self.radio_or)
        vbox_filter.addLayout(hbox_logic)

        # Przyciski zastosowania i czyszczenia filtrów
        self.btn_apply_filters = QPushButton("Zastosuj filtry")
        self.btn_clear_filters = QPushButton("Wyczyść filtry")

        hbox_buttons = QHBoxLayout()
        hbox_buttons.addWidget(self.btn_apply_filters)
        hbox_buttons.addWidget(self.btn_clear_filters)
        vbox_filter.addLayout(hbox_buttons)

        vbox_filter.addStretch()
        self.tabs.addTab(self.tab_filter, "Filtry")

        # =====================================================================
        # ZAKŁADKA 2: STATYSTYKI
        # Umożliwia obliczenie wybranych metryk (count/mean/median/min/max/std)
        # dla zaznaczonych kolumn, z opcjonalnym grupowaniem po kolumnie.
        # Zakres danych: przefiltrowane lub całe.
        # =====================================================================
        self.tab_stats = QWidget()
        vbox_stats = QVBoxLayout(self.tab_stats)

        # Wybór zakresu danych: przefiltrowane / całe
        src_box = QHBoxLayout()
        src_box.addWidget(QLabel("Zakres danych:"))

        self.radio_scope_filtered = QRadioButton("Przefiltrowane")
        self.radio_scope_all = QRadioButton("Całe")
        self.radio_scope_filtered.setChecked(True)

        self.scope_group = QButtonGroup(self)
        self.scope_group.addButton(self.radio_scope_filtered)
        self.scope_group.addButton(self.radio_scope_all)

        src_box.addWidget(self.radio_scope_filtered)
        src_box.addWidget(self.radio_scope_all)
        vbox_stats.addLayout(src_box)

        # Lista kolumn z checkboxami (MultiSelection)
        vbox_stats.addWidget(QLabel("Kolumny do analizy (zaznacz co chcesz):"))
        self.list_cols = QListWidget()
        self.list_cols.setSelectionMode(QListWidget.MultiSelection)
        vbox_stats.addWidget(self.list_cols)

        # Grupowanie wyników po wybranej kolumnie
        grp = QHBoxLayout()
        grp.addWidget(QLabel("Grupuj wg (opcjonalnie):"))
        self.combo_groupby = QComboBox()
        grp.addWidget(self.combo_groupby)
        vbox_stats.addLayout(grp)

        # Checkboxy wyboru metryk — domyślnie zaznaczone: count, mean, median, min, max
        vbox_stats.addWidget(QLabel("Metryki:"))
        self.chk_count = QCheckBox("Liczność (count)")
        self.chk_mean = QCheckBox("Średnia (mean)")
        self.chk_median = QCheckBox("Mediana (median)")
        self.chk_min = QCheckBox("Min")
        self.chk_max = QCheckBox("Max")
        self.chk_std = QCheckBox("Odchylenie std")

        for c in [self.chk_count, self.chk_mean, self.chk_median, self.chk_min, self.chk_max]:
            c.setChecked(True)

        metrics_row = QHBoxLayout()
        for c in [self.chk_count, self.chk_mean, self.chk_median, self.chk_min, self.chk_max, self.chk_std]:
            metrics_row.addWidget(c)
        vbox_stats.addLayout(metrics_row)

        self.btn_compute_stats = QPushButton("Oblicz statystyki")
        vbox_stats.addWidget(self.btn_compute_stats)

        # Pole wynikowe (tylko do odczytu)
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        vbox_stats.addWidget(self.stats_text)

        self.tabs.addTab(self.tab_stats, "Statystyki")

        # =====================================================================
        # ZAKŁADKA 3: WIZUALIZACJA
        # Umożliwia wybór kolumn X i Y, typu wykresu oraz opcjonalnego
        # zakresu osi Y. Wykres jest osadzany jako FigureCanvas w zakładce.
        # Przycisk powiększenia otwiera wykres w osobnym oknie dialogowym
        # z paskiem narzędzi matplotlib.
        # =====================================================================
        self.tab_plot = QWidget()
        vbox_plot = QVBoxLayout(self.tab_plot)

        vbox_plot.addWidget(QLabel("Kolumna X:"))
        self.combo_plot_x = QComboBox()
        vbox_plot.addWidget(self.combo_plot_x)

        vbox_plot.addWidget(QLabel("Kolumna Y (opcjonalna dla wykresu rozrzutu):"))
        self.combo_plot_y = QComboBox()
        vbox_plot.addWidget(self.combo_plot_y)

        vbox_plot.addWidget(QLabel("Typ wykresu:"))
        self.combo_chart_type = QComboBox()
        self.combo_chart_type.addItems([
            "Auto",
            "Histogram",
            "Bar chart",
            "Wykres rozrzutu",
            "Box plot",
            "Wykres liniowy"
        ])
        vbox_plot.addWidget(self.combo_chart_type)

        # Przyciski rysowania i powiększenia wykresu
        btn_row = QHBoxLayout()
        self.btn_draw_plot = QPushButton("Rysuj wykres")
        self.btn_fullscreen = QPushButton("🔍 Powiększ wykres")
        self.btn_fullscreen.setEnabled(False)
        btn_row.addWidget(self.btn_draw_plot)
        btn_row.addWidget(self.btn_fullscreen)
        vbox_plot.addLayout(btn_row)

        # Opcjonalne ręczne ustawienie zakresu osi Y
        self.chk_yrange = QCheckBox("Ustaw zakres osi Y ręcznie")
        vbox_plot.addWidget(self.chk_yrange)

        yrange_box = QHBoxLayout()
        yrange_box.addWidget(QLabel("Min:"))
        self.input_ymin = QLineEdit()
        self.input_ymin.setPlaceholderText("np. 0")
        self.input_ymin.setEnabled(False)
        yrange_box.addWidget(self.input_ymin)
        yrange_box.addWidget(QLabel("Max:"))
        self.input_ymax = QLineEdit()
        self.input_ymax.setPlaceholderText("np. 1000")
        self.input_ymax.setEnabled(False)
        yrange_box.addWidget(self.input_ymax)
        vbox_plot.addLayout(yrange_box)

        # Checkbox zakresu Y włącza/wyłącza pola Min i Max
        self.chk_yrange.toggled.connect(self.input_ymin.setEnabled)
        self.chk_yrange.toggled.connect(self.input_ymax.setEnabled)

        self.plot_info_label = QLabel("Brak danych do wizualizacji.")
        vbox_plot.addWidget(self.plot_info_label)

        # Kontener na osadzony wykres matplotlib
        self.plot_container = QWidget()
        self.plot_container_layout = QVBoxLayout(self.plot_container)
        self.plot_container_layout.setContentsMargins(0, 0, 0, 0)
        vbox_plot.addWidget(self.plot_container)

        self.tabs.addTab(self.tab_plot, "Wizualizacja")

        # =====================================================================
        # ZAKŁADKA 4: ANALIZA PROGÓW
        # Pozwala zbadać jak zmiana wartości progowej filtra wpływa na liczbę
        # rekordów i średnie wartości wybranych kolumn numerycznych.
        # Użytkownik podaje kolumnę, operator i listę progów oddzielonych przecinkami.
        # =====================================================================
        self.tab_threshold = QWidget()
        vbox_thresh = QVBoxLayout(self.tab_threshold)

        vbox_thresh.addWidget(QLabel("Kolumna filtrowana (próg):"))
        self.combo_thresh_col = QComboBox()
        vbox_thresh.addWidget(self.combo_thresh_col)

        thresh_op_row = QHBoxLayout()
        thresh_op_row.addWidget(QLabel("Operator:"))
        self.combo_thresh_op = QComboBox()
        self.combo_thresh_op.addItems([">", ">=", "<", "<="])
        thresh_op_row.addWidget(self.combo_thresh_op)
        vbox_thresh.addLayout(thresh_op_row)

        vbox_thresh.addWidget(QLabel("Wartości progowe (oddzielone przecinkami, np. 40,50,60,70):"))
        self.input_thresholds = QLineEdit()
        self.input_thresholds.setPlaceholderText("np. 40,50,60,70,80")
        vbox_thresh.addWidget(self.input_thresholds)

        vbox_thresh.addWidget(QLabel("Kolumny do analizy (zaznacz):"))
        self.list_thresh_cols = QListWidget()
        self.list_thresh_cols.setSelectionMode(QListWidget.MultiSelection)
        self.list_thresh_cols.setMaximumHeight(120)
        vbox_thresh.addWidget(self.list_thresh_cols)

        self.btn_run_threshold = QPushButton("▶ Uruchom analizę progów")
        vbox_thresh.addWidget(self.btn_run_threshold)

        # Pole wynikowe w czcionce monospacowej dla wyrównania tabeli
        self.threshold_result = QTextEdit()
        self.threshold_result.setReadOnly(True)
        self.threshold_result.setFont(QFont("Courier New", 9))
        vbox_thresh.addWidget(self.threshold_result)

        self.tabs.addTab(self.tab_threshold, "Analiza progów")
        # =====================================================================
        # ZAKŁADKA 5: POMOC
        # Wyświetla tekst z opisem wszystkich zakładek i funkcji aplikacji.
        # =====================================================================
        self.tab_help = QWidget()
        vbox_help = QVBoxLayout(self.tab_help)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setFont(QFont("Segoe UI", 10))
        help_text.setStyleSheet("QTextEdit { padding: 12px; }")

        help_content = """
        ANALIZATOR DANYCH PACJENTÓW — POMOC
        ━━━━━━━━━━━━━━━━━━
        Witaj w programie Analizator Danych Pacjentów!
        Cieszę się, że wybrałeś akurat ten program! 
        Mam nadzieję, że działa poprawnie, chociaż nic nie obiecuję! 
        Poniżej krótki poradnik dla użytkownika:        

        WCZYTYWANIE DANYCH
        ──────────────────
        • Plik CSV / Excel — kliknij „Wczytaj plik" lub użyj menu Plik.
          Separator i kodowanie wykrywane są automatycznie (obsługa UTF-8,
          ISO-8859-2, CP1250).
        • Baza SQLite — kliknij „Wczytaj z bazy SQL", wybierz plik .db,
          a następnie wskaż tabelę z listy dostępnych tabel.

        ZAKŁADKI APLIKACJI
        ──────────────────

        PODGLĄD DANYCH
          Wyświetla wczytane dane w tabeli. Po zastosowaniu filtrów pokazuje
          tylko przefiltrowane rekordy. Liczba widocznych rekordów widoczna
          jest w nagłówku zakładki.

        FILTRY
          Budowanie warunków filtrowania krok po kroku:
          1. Wybierz kolumnę z listy.
          2. Wybierz operator: =  >  <  >=  <=  zawiera  nie zawiera
          3. Podaj wartość (dla kolumn tekstowych pojawi się lista rozwijana).
          4. Kliknij „Dodaj warunek" — warunek pojawi się na liście aktywnych.
          5. Powtórz dla kolejnych warunków.
          6. Wybierz logikę łączenia: AND (wszystkie warunki muszą być spełnione)
             lub OR (wystarczy jeden).
          7. Kliknij „Zastosuj filtry".

          Wskazówka: pojedynczy zaznaczony warunek można usunąć przyciskiem
          „Usuń zaznaczony". „Wyczyść filtry" usuwa wszystkie naraz.

        STATYSTYKI
          Obliczanie metryk dla wybranych kolumn:
          1. Wybierz zakres: Przefiltrowane lub Całe dane.
          2. Zaznacz kolumny checkboxami.
          3. Opcjonalnie wybierz kolumnę grupowania (np. płeć, typ ubezpieczenia).
          4. Zaznacz metryki: count / mean / median / min / max / std.
          5. Kliknij „Oblicz statystyki".

          Kolumny numeryczne — wyświetlają pełne statystyki.
          Kolumny tekstowe  — wyświetlają liczbę unikalnych wartości
                              oraz najczęstsze wystąpienia.

        WIZUALIZACJA
          Tworzenie wykresów:
          1. Wybierz kolumnę X (obowiązkowa).
          2. Wybierz kolumnę Y (opcjonalna — wymagana dla scatter/box/liniowy).
          3. Wybierz typ wykresu lub pozostaw „Auto" (dobór automatyczny):
             • Histogram      — jedna kolumna numeryczna
             • Bar chart      — jedna kolumna tekstowa
             • Box plot       — tekst (X) + liczba (Y)
             • Wykres rozrzutu— liczba (X) + liczba (Y), próbka do 5000 pkt
             • Wykres liniowy — data (X) + liczba (Y)
          4. Opcjonalnie zaznacz „Ustaw zakres osi Y ręcznie" i podaj Min/Max.
          5. Kliknij „Rysuj wykres".
          6. Przycisk „Powiększ wykres" otwiera wykres w osobnym oknie
             z paskiem narzędzi matplotlib (zoom, zapis PNG).

        ANALIZA PROGÓW
          Sprawdza jak zmiana wartości progowej filtra wpływa na liczbę
          rekordów i średnie kolumn numerycznych:
          1. Wybierz kolumnę filtrowaną (np. age, bmi).
          2. Wybierz operator (>, >=, <, <=).
          3. Wpisz wartości progowe oddzielone przecinkami, np.: 40,50,60,70
          4. Zaznacz kolumny do analizy.
          5. Kliknij „Uruchom analizę progów".

        EKSPORT
        ───────
        • Eksport CSV  — zapisuje przefiltrowane dane do pliku .csv
                         (separator: średnik).
        • Eksport PDF  — generuje raport zawierający:
                         stronę tytułową, metodologię, statystyki,
                         wykres (jeśli wygenerowany) oraz automatyczne wnioski.

        ANALIZA WPŁYWU FILTRÓW
        ──────────────────────
        Przycisk „Analiza wpływu filtrów" (panel boczny) porównuje dane
        przed i po filtracji — pokazuje procentowy ubytek rekordów oraz
        zmiany średnich i median dla kolumn numerycznych.
        Wyniki można wyeksportować do pliku .txt.

        BAZA DANYCH SQLite
        ──────────────────
        Projekt zawiera skrypt csv_to_sqlite.py do jednorazowej konwersji
        plików CSV do bazy danych:

          python csv_to_sqlite.py --input_dir ./dane --output baza.db

        Baza zawiera 5 tabel połączonych przez patient_id:
          patients (100k) · medications (364k) · outcomes (11k)
          diagnoses (274k) · lab_results (2,8M)

        SKRÓTY I WSKAZÓWKI
        ──────────────────
        • Logi działań aplikacji widoczne są w panelu na dole okna.
        • Przy dużych zbiorach danych wczytywanie odbywa się w tle —
          aplikacja pozostaje responsywna.
        • Scatter plot automatycznie próbkuje dane do 5000 punktów
          przy bardzo dużych zbiorach.
        • Wartości liczbowe można wpisywać z przecinkiem lub kropką
          jako separatorem dziesiętnym.
          
          Miłego korzystania z programu!
        """

        help_text.setPlainText(help_content.strip())
        vbox_help.addWidget(help_text)
        self.tabs.addTab(self.tab_help, "❓ Pomoc")

        # --- PANEL LOGÓW ---
        # Wyświetla chronologiczny dziennik działań użytkownika i zdarzeń systemowych.
        logs_frame = QFrame()
        logs_layout = QVBoxLayout(logs_frame)
        logs_layout.addWidget(QLabel("Logi:"))

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        logs_layout.addWidget(self.logs)

        main_layout.addWidget(splitter)
        main_layout.addWidget(logs_frame)

        # =====================================================================
        # POŁĄCZENIA SYGNAŁÓW I SLOTÓW
        # Każdy przycisk i widget interaktywny jest połączony z odpowiednią metodą.
        # =====================================================================
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load_sql.clicked.connect(self.load_sql)
        self.btn_filter.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.btn_stats.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.btn_plot.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        self.btn_compare.clicked.connect(self.compare_filters)
        self.btn_threshold.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        self.btn_run_threshold.clicked.connect(self.run_threshold_analysis)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        self.btn_export_csv.clicked.connect(self.export_csv)
        self.btn_add_condition.clicked.connect(self.add_condition)
        self.btn_remove_condition.clicked.connect(self.remove_condition)
        self.list_filters.itemSelectionChanged.connect(
            lambda: self.btn_remove_condition.setEnabled(
                len(self.list_filters.selectedItems()) > 0
            ))
        self.btn_clear_filters.clicked.connect(self.clear_filters)
        self.btn_apply_filters.clicked.connect(self.apply_filters)
        self.btn_compute_stats.clicked.connect(self.compute_selected_stats)
        self.btn_draw_plot.clicked.connect(self.show_plot)
        self.btn_fullscreen.clicked.connect(self.open_fullscreen_plot)
        self.combo_col.currentTextChanged.connect(self._update_value_widget)

    # =========================================================================
    # METODY POMOCNICZE OKNA
    # =========================================================================

    # --- LOGGER ---
    # Dopisuje komunikat do panelu logów z prefiksem ">".
    def log(self, msg):
        self.logs.append(f"> {msg}")

    # --- PARSOWANIE WARTOŚCI LICZBOWEJ ---
    # Zamienia przecinek na kropkę przed konwersją — obsługa polskiego formatu.
    def _parse_numeric_value(self, value_text):
        return float(value_text.replace(",", "."))

    # --- CZYSZCZENIE OBSZARU WYKRESU ---
    # Zamyka poprzednią figurę matplotlib (zapobiega wyciekowi pamięci),
    # usuwa wszystkie widgety z kontenera wykresu i resetuje referencje.
    def _clear_plot_area(self):
        if self.last_fig is not None:
            plt.close(self.last_fig)
            self.last_fig = None
        while self.plot_container_layout.count():
            item = self.plot_container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self.canvas = None

    # --- ODŚWIEŻANIE UI PO WCZYTANIU DANYCH ---
    # Wypełnia wszystkie ComboBox, listy kolumn i resetuje stan filtrów
    # po każdorazowym wczytaniu nowego zbioru danych.
    def _refresh_ui_after_load(self):
        if self.df is None or self.df.empty:
            return

        self.df_filtered = self.df.copy()
        self.update_table(self.df)

        self.combo_col.clear()
        self.combo_col.addItems([str(col) for col in self.df.columns])

        self.combo_plot_x.clear()
        self.combo_plot_y.clear()
        self.combo_plot_x.addItems([str(col) for col in self.df.columns])
        self.combo_plot_y.addItems(["(brak)"] + [str(col) for col in self.df.columns])

        self.list_cols.clear()
        for col in self.df.columns:
            item = QListWidgetItem(str(col))
            item.setCheckState(Qt.Unchecked)
            self.list_cols.addItem(item)

        self.combo_groupby.clear()
        self.combo_groupby.addItem("(brak)")
        self.combo_groupby.addItems([str(col) for col in self.df.columns])

        self.filters.clear()
        self.list_filters.clear()
        self.input_value.clear()
        self.radio_and.setChecked(True)

        self.stats_text.clear()
        self._clear_plot_area()
        self.plot_info_label.setText("Brak danych do wizualizacji.")

        self.combo_thresh_col.clear()
        self.combo_thresh_col.addItems([str(col) for col in self.df.columns])
        self.list_thresh_cols.clear()
        for col in self.df.columns:
            item = QListWidgetItem(str(col))
            self.list_thresh_cols.addItem(item)

    # =========================================================================
    # WCZYTYWANIE PLIKU CSV / EXCEL
    # Otwiera dialog wyboru pliku i uruchamia wątek FileLoaderThread.
    # =========================================================================
    def load_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik", "",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        if not filename:
            return
        self._start_loader(filename=filename)

    # =========================================================================
    # WCZYTYWANIE DANYCH Z BAZY SQLite
    # Otwiera dialog wyboru pliku .db, pobiera listę tabel z bazy,
    # wyświetla QInputDialog z listą tabel do wyboru,
    # a następnie uruchamia wątek wczytywania dla wybranej tabeli.
    # =========================================================================
    def load_sql(self):
        db_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz bazę danych", "",
            "SQLite Files (*.db *.sqlite *.sqlite3)"
        )
        if not db_path:
            return

        # Pobierz listę tabel z bazy
        try:
            with sqlite3.connect(db_path) as conn:
                tables = pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", #noqa
                    conn
                )["name"].tolist()
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można otworzyć bazy:\n{e}")
            return

        if not tables:
            QMessageBox.warning(self, "Brak tabel", "Baza danych nie zawiera żadnych tabel.")
            return

        # Dialog wyboru tabeli (bez znaku zapytania w tytule)
        dialog = QInputDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("Wybierz tabelę")
        dialog.setLabelText(f"Dostępne tabele w bazie ({len(tables)}):")
        dialog.setComboBoxItems(tables)
        dialog.setComboBoxEditable(False)
        ok = dialog.exec_()
        table_name = dialog.textValue()
        if not ok or not table_name:
            return

        self.current_db_path = db_path
        self._start_loader(db_path=db_path, table_name=table_name)

    # =========================================================================
    # URUCHAMIANIE WĄTKU WCZYTYWANIA
    # Blokuje przyciski wczytywania, ustawia kursor oczekiwania
    # i startuje FileLoaderThread z odpowiednimi parametrami.
    # =========================================================================
    def _start_loader(self, filename=None, db_path=None, table_name=None):
        self.btn_load.setEnabled(False)
        self.btn_load_sql.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        self.loader_thread = FileLoaderThread(
            filename=filename,
            db_path=db_path,
            table_name=table_name
        )
        self.loader_thread.progress.connect(self.log)
        self.loader_thread.finished.connect(self._on_load_finished)
        self.loader_thread.error.connect(self._on_load_error)
        self.loader_thread.start()

    # --- CALLBACK: WCZYTYWANIE ZAKOŃCZONE SUKCESEM ---
    # Przywraca kursor, odblokowuje przyciski, zapisuje df,
    # wyświetla ostrzeżenia walidacji i odświeża cały interfejs.
    def _on_load_finished(self, result):
        QApplication.restoreOverrideCursor()
        self.btn_load.setEnabled(True)
        self.btn_load_sql.setEnabled(True)

        df, errors = result
        self.df = df

        if errors:
            QMessageBox.warning(self, "Walidacja danych", "\n".join(errors))

        self._refresh_ui_after_load()

        self.log(f"Wczytano dane: {len(self.df)} wierszy, {len(self.df.columns)} kolumn")
        if errors:
            self.log("Walidacja wykryła problemy: " + " | ".join(errors))

        self.tabs.setCurrentIndex(0)

    # --- CALLBACK: WCZYTYWANIE ZAKOŃCZONE BŁĘDEM ---
    # Przywraca kursor, odblokowuje przyciski i wyświetla komunikat błędu.
    def _on_load_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.btn_load.setEnabled(True)
        self.btn_load_sql.setEnabled(True)
        QMessageBox.warning(self, "Błąd wczytywania", error_msg)
        self.log(f"Błąd wczytywania: {error_msg}")

    # =========================================================================
    # TABLICA DANYCH — AKTUALIZACJA WIDOKU
    # Przekazuje DataFrame do modelu tabeli z wyłączeniem odświeżania
    # podczas aktualizacji (setUpdatesEnabled) dla lepszej wydajności.
    # =========================================================================
    def update_table(self, df):
        if df is None or df.empty:
            self.table.setUpdatesEnabled(False)
            self.table_model.set_dataframe(None)
            self.table.setUpdatesEnabled(True)
            self.preview_label.setText("Podgląd danych: 0 z 0 rekordów")
            self.log("Brak danych do wyświetlenia")
            return

        self.table.setUpdatesEnabled(False)
        self.table_model.set_dataframe(df)
        self.table.setUpdatesEnabled(True)
        self.preview_label.setText(f"Podgląd danych: {len(df)} rekordów")
        self.log(f"Załadowano do widoku: {len(df)} wierszy")

    # =========================================================================
    # DYNAMICZNE PRZEŁĄCZANIE WIDŻETU WARTOŚCI FILTRA
    # Wywoływane przy zmianie wybranej kolumny w zakładce Filtry.
    # Dla kolumn numerycznych: pokazuje pole tekstowe (input_value).
    # Dla kolumn tekstowych: pokazuje ComboBox z unikalnymi wartościami.
    # blockSignals(True) zapobiega wielokrotnemu wyzwalaniu sygnałów
    # podczas wypełniania ComboBox.
    # =========================================================================
    def _update_value_widget(self, col_name):
        if self.df is None or col_name not in self.df.columns:
            return

        series = self.df[col_name]
        is_numeric = pd.api.types.is_numeric_dtype(series) or \
                     pd.to_numeric(series, errors="coerce").notna().mean() > 0.5

        if is_numeric:
            self.input_value.setVisible(True)
            self.combo_value.setVisible(False)
            self.filter_value_label.setText("Wartość:")
            self.input_value.setPlaceholderText("np. 50 lub 5,5")
        else:
            all_unique = series.dropna().astype(str).unique()
            n_total = len(all_unique)
            MAX_VALUES = 500
            if n_total > MAX_VALUES:
                unique_vals = sorted(all_unique[:MAX_VALUES])
                label = f"Wartość (pokazano {MAX_VALUES} z {n_total}):"
            else:
                unique_vals = sorted(all_unique)
                label = f"Wartość ({n_total} unikalnych):"

            self.combo_value.clear()
            self.combo_value.blockSignals(True)
            self.combo_value.addItems(unique_vals)
            self.combo_value.blockSignals(False)
            self.combo_value.setVisible(True)
            self.input_value.setVisible(False)
            self.filter_value_label.setText(label)

    # =========================================================================
    # MODUŁ FILTRÓW
    # =========================================================================

    # --- DODAWANIE WARUNKU ---
    # Odczytuje kolumnę, operator i wartość z widżetów.
    # Dla operatorów porównawczych (>, <, >=, <=) sprawdza czy wartość jest liczbą.
    # Dodaje warunek do listy self.filters i wyświetla go w list_filters.
    def add_condition(self):
        col = self.combo_col.currentText()
        op = self.combo_op.currentText()

        if self.combo_value.isVisible():
            val = self.combo_value.currentText().strip()
        else:
            val = self.input_value.text().strip()

        if not col or not val:
            QMessageBox.information(self, "Brak danych", "Wybierz kolumnę i wprowadź wartość.")
            return

        if op in [">", "<", ">=", "<="]:
            try:
                self._parse_numeric_value(val)
            except ValueError:
                QMessageBox.warning(
                    self, "Błąd wartości",
                    f"Operator '{op}' wymaga wartości liczbowej.\nWprowadź liczbę (np. 50 lub 5,5)."
                )
                return

        condition = (col, op, val)
        self.filters.append(condition)
        self.list_filters.addItem(f"{col} {op} {val}")
        self.input_value.clear()
        self.log(f"Dodano warunek: {col} {op} {val}")

    # --- USUWANIE ZAZNACZONEGO WARUNKU ---
    # Usuwa zaznaczone pozycje z listy GUI i z listy self.filters.
    # Po usunięciu dezaktywuje przycisk "Usuń zaznaczony".
    def remove_condition(self):
        selected = self.list_filters.selectedItems()
        if not selected:
            return

        for item in selected:
            row = self.list_filters.row(item)
            self.list_filters.takeItem(row)
            if 0 <= row < len(self.filters):
                removed = self.filters.pop(row)
                self.log(f"Usunięto warunek: {removed[0]} {removed[1]} {removed[2]}")

        self.btn_remove_condition.setEnabled(False)

    # --- CZYSZCZENIE WSZYSTKICH FILTRÓW ---
    # Resetuje listę warunków, przywraca pełny DataFrame jako df_filtered
    # i aktualizuje widok tabeli.
    def clear_filters(self):
        self.filters.clear()
        self.list_filters.clear()
        self.input_value.clear()
        self.radio_and.setChecked(True)
        self.btn_remove_condition.setEnabled(False)

        if self.df is not None:
            self.df_filtered = self.df.copy()
            self.update_table(self.df)

        self.log("Wyczyszczono wszystkie filtry.")

    # --- ZASTOSOWANIE FILTRÓW ---
    # Tworzy maski boolowskie dla każdego warunku, z cache'owaniem kolumn
    # (col_cache) aby nie przeliczać tej samej kolumny wielokrotnie.
    # Obsługiwane operatory: =, >, <, >=, <=, zawiera, nie zawiera.
    # Maski łączone są operatorem AND lub OR zgodnie z wyborem użytkownika.
    def apply_filters(self):
        if self.df is None:
            QMessageBox.information(self, "Filtry", "Najpierw wczytaj dane.")
            return

        if not self.filters:
            QMessageBox.information(self, "Filtry", "Nie dodano żadnych warunków.")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        logic = "and" if self.radio_and.isChecked() else "or"
        masks = []
        errors = []

        # Cache kolumn: każda kolumna konwertowana raz (jako str i jako liczba)
        col_cache = {}
        for col, op, val in self.filters:
            if col not in col_cache:
                series_str = self.df[col].astype(str)
                series_num = pd.to_numeric(
                    series_str.str.replace(",", ".", regex=False),
                    errors="coerce"
                )
                col_cache[col] = (series_str, series_num)

        # Budowanie masek boolowskich dla każdego warunku
        for col, op, val in self.filters:
            series_str, series_num = col_cache[col]
            try:
                if op == "=":
                    mask = series_str.str.lower() == val.lower()
                    try:
                        vnum = self._parse_numeric_value(val)
                        mask = mask | (series_num == vnum)
                    except ValueError:
                        pass

                elif op == ">":
                    vnum = self._parse_numeric_value(val)
                    mask = series_num > vnum

                elif op == "<":
                    vnum = self._parse_numeric_value(val)
                    mask = series_num < vnum

                elif op == ">=":
                    vnum = self._parse_numeric_value(val)
                    mask = series_num >= vnum

                elif op == "<=":
                    vnum = self._parse_numeric_value(val)
                    mask = series_num <= vnum

                elif op == "zawiera":
                    mask = series_str.str.contains(val, case=False, na=False)

                elif op == "nie zawiera":
                    mask = ~series_str.str.contains(val, case=False, na=False)

                else:
                    mask = pd.Series([True] * len(self.df), index=self.df.index)

                masks.append(mask.fillna(False))

            except Exception as e:
                errors.append(f"Warunek '{col} {op} {val}': {e}")
                masks.append(pd.Series([False] * len(self.df), index=self.df.index))

        if errors:
            QMessageBox.warning(
                self, "Błędy filtrowania",
                "Niektóre warunki nie zadziałały:\n" + "\n".join(errors)
            )

        # Łączenie masek operatorem AND lub OR
        final_mask = masks[0]
        for m in masks[1:]:
            final_mask = (final_mask & m) if logic == "and" else (final_mask | m)

        self.df_filtered = self.df.loc[final_mask].copy()

        QApplication.restoreOverrideCursor()

        self.update_table(self.df_filtered)
        self.tabs.setCurrentIndex(0)
        self.log(
            f"Zastosowano {len(self.filters)} filtrów ({logic.upper()}); "
            f"wyników: {len(self.df_filtered)} z {len(self.df)}"
        )

    # =========================================================================
    # MODUŁ STATYSTYK
    # Zbiera zaznaczone kolumny i metryki, przekazuje do calculate_selected_stats
    # i wyświetla wynik w polu stats_text.
    # =========================================================================
    def compute_selected_stats(self):
        if self.df is None:
            QMessageBox.warning(self, "Brak danych", "Najpierw wczytaj plik.")
            return

        df_src = self.df_filtered if self.radio_scope_filtered.isChecked() and self.df_filtered is not None else self.df

        selected_cols = []
        for i in range(self.list_cols.count()):
            item = self.list_cols.item(i)
            if item.checkState() == Qt.Checked:
                selected_cols.append(item.text())

        if not selected_cols:
            QMessageBox.information(self, "Statystyki", "Zaznacz przynajmniej jedną kolumnę.")
            return

        group_col = self.combo_groupby.currentText()

        want = {
            "count": self.chk_count.isChecked(),
            "mean": self.chk_mean.isChecked(),
            "median": self.chk_median.isChecked(),
            "min": self.chk_min.isChecked(),
            "max": self.chk_max.isChecked(),
            "std": self.chk_std.isChecked(),
        }

        try:
            result = calculate_selected_stats(
                df_src, selected_cols, want, group_col,
                is_filtered=self.radio_scope_filtered.isChecked()
            )
            self.stats_text.setPlainText(result)
            self.log("Obliczono statystyki.")
            self.tabs.setCurrentIndex(2)

        except Exception as e:
            QMessageBox.warning(self, "Błąd statystyk", f"Nie udało się policzyć statystyk:\n{e}")
            self.log(f"Błąd statystyk: {e}")

    # =========================================================================
    # MODUŁ WIZUALIZACJI
    # =========================================================================

    # --- RYSOWANIE WYKRESU ---
    # Odczytuje parametry z zakładki Wizualizacja, opcjonalnie parsuje zakres Y,
    # tworzy figurę przez create_plot() i osadza ją jako FigureCanvas w GUI.
    # Bufor PNG wykresu zapisywany jest do self._plot_buf dla eksportu PDF.
    def show_plot(self):
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Brak danych", "Brak danych do wizualizacji.")
            return

        col_x = self.combo_plot_x.currentText()
        col_y = self.combo_plot_y.currentText()
        chart_type = self.combo_chart_type.currentText()

        if not col_x:
            QMessageBox.warning(self, "Brak kolumny", "Wybierz przynajmniej kolumnę X.")
            return

        y_min = None
        y_max = None
        if self.chk_yrange.isChecked():
            try:
                y_min = float(self.input_ymin.text().replace(",", "."))
            except ValueError:
                QMessageBox.warning(self, "Błąd", "Nieprawidłowa wartość Min osi Y.")
                return
            try:
                y_max = float(self.input_ymax.text().replace(",", "."))
            except ValueError:
                QMessageBox.warning(self, "Błąd", "Nieprawidłowa wartość Max osi Y.")
                return
            if y_min >= y_max:
                QMessageBox.warning(self, "Błąd", "Min musi być mniejsze niż Max.")
                return

        try:
            fig, final_chart_type = create_plot(
                self.df_filtered, col_x, col_y, chart_type,
                y_min=y_min, y_max=y_max
            )
        except Exception as e:
            QMessageBox.warning(self, "Błąd wykresu", str(e))
            self.log(f"Błąd wykresu: {e}")
            return

        self._clear_plot_area()

        self.canvas = FigureCanvas(fig)
        self.plot_container_layout.addWidget(self.canvas)
        self.canvas.draw()

        self.last_fig = fig
        self.plot_info_label.setText("")
        self.btn_fullscreen.setEnabled(True)

        self.tabs.setCurrentIndex(3)
        self.log(
            f"Wygenerowano wykres ({final_chart_type}) dla kolumny {col_x}"
            + (f" i {col_y}" if col_y and col_y != "(brak)" else "")
            + (f" [Y: {y_min}–{y_max}]" if y_min is not None else "")
        )

    # --- POWIĘKSZONY PODGLĄD WYKRESU ---
    # Otwiera wykres w osobnym oknie QDialog z paskiem narzędzi matplotlib
    # (NavigationToolbar2QT). Po zamknięciu rozłącza zdarzenia canvas.
    def open_fullscreen_plot(self):
        if self.last_fig is None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Podgląd wykresu")
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setMinimumSize(900, 600)
        dialog.resize(1100, 700)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(8, 8, 8, 8)

        canvas = FigureCanvas(self.last_fig)
        layout.addWidget(canvas)

        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
        toolbar = NavigationToolbar(canvas, dialog)
        layout.addWidget(toolbar)

        dialog.exec_()

        # Odłączenie zdarzeń matplotlib po zamknięciu okna
        # — zapobiega błędowi "QLabel has been deleted"
        try:
            canvas.mpl_disconnect_all()
        except Exception:
            pass
        try:
            self.last_fig.canvas.mpl_disconnect_all()
        except Exception:
            pass

    # =========================================================================
    # ANALIZA WPŁYWU FILTRÓW
    # Wywołuje compare_filter_impact (podstawowe porównanie rekordów)
    # i analyze_filter_impact (szczegółowe porównanie średnich i median).
    # Wyniki wyświetlane są w scrollowalnym oknie dialogowym z opcją
    # eksportu do pliku TXT.
    # =========================================================================
    def compare_filters(self):
        if self.df is None or self.df_filtered is None:
            QMessageBox.warning(self, "Brak danych", "Najpierw wczytaj dane.")
            return

        if not self.filters:
            QMessageBox.information(self, "Brak filtrów", "Najpierw dodaj i zastosuj filtry.")
            return

        try:
            # Podstawowe porównanie liczby rekordów
            basic = compare_filter_impact(self.df, self.df_filtered)

            # Szczegółowa analiza wpływu filtrów na statystyki kolumn numerycznych
            numeric_cols = self.df.select_dtypes(include="number").columns.tolist()
            detailed = analyze_filter_impact(self.df, self.df_filtered, numeric_cols)

            # Okno dialogowe z wynikami
            dialog = QDialog(self)
            dialog.setWindowTitle("Analiza wpływu parametrów filtrowania")
            dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            dialog.resize(700, 500)

            layout = QVBoxLayout(dialog)

            text = QTextEdit()
            text.setReadOnly(True)
            text.setFont(QFont("Courier New", 10))
            text.setPlainText(basic + "\n\n" + detailed)
            layout.addWidget(text)

            btn_close = QPushButton("Zamknij")
            btn_close.clicked.connect(dialog.close)

            btn_export = QPushButton("💾 Eksport TXT")
            btn_export.clicked.connect(lambda: self._export_analysis_txt(basic + "\n\n" + detailed))

            btn_row = QHBoxLayout()
            btn_row.addWidget(btn_export)
            btn_row.addWidget(btn_close)
            layout.addLayout(btn_row)

            dialog.exec_()
            self.log("Wykonano analizę wpływu parametrów filtrowania.")

        except Exception as e:
            QMessageBox.warning(self, "Błąd", str(e))
            self.log(f"Błąd analizy wpływu: {e}")

    # --- EKSPORT ANALIZY DO PLIKU TXT ---
    # Zapisuje wynik analizy wpływu filtrów do pliku tekstowego z timestampem.
    def _export_analysis_txt(self, content):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Zapisz analizę", f"analiza_wplywu_{timestamp}.txt",
            "Text Files (*.txt)"
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"Zapisano analizę: {filename}")
            QMessageBox.information(self, "Sukces", f"Zapisano:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Błąd", str(e))

    # =========================================================================
    # ANALIZA PROGÓW
    # Dla każdego progu z listy filtruje DataFrame według warunku
    # (col_filter op thresh) i oblicza średnie wartości wybranych kolumn.
    # Wyniki są formatowane jako tabela tekstowa w polu threshold_result.
    # =========================================================================
    def run_threshold_analysis(self):
        if self.df is None:
            QMessageBox.warning(self, "Brak danych", "Najpierw wczytaj dane.")
            return

        col_filter = self.combo_thresh_col.currentText()
        op = self.combo_thresh_op.currentText()

        raw = self.input_thresholds.text().strip()
        if not raw:
            QMessageBox.warning(self, "Brak progów", "Wprowadź wartości progowe.")
            return

        try:
            thresholds = [float(v.replace(",", ".").strip()) for v in raw.split(",")]
        except ValueError:
            QMessageBox.warning(self, "Błąd",
                "Nieprawidłowe wartości progowe — wpisz liczby oddzielone przecinkami.")
            return

        selected_cols = [
            self.list_thresh_cols.item(i).text()
            for i in range(self.list_thresh_cols.count())
            if self.list_thresh_cols.item(i).isSelected()
        ]
        if not selected_cols:
            QMessageBox.warning(self, "Brak kolumn",
                "Zaznacz co najmniej jedną kolumnę do analizy.")
            return

        # Filtrowanie tylko kolumn numerycznych spośród zaznaczonych
        num_cols = [
            c for c in selected_cols
            if pd.api.types.is_numeric_dtype(self.df[c]) or
               pd.to_numeric(self.df[c], errors="coerce").notna().mean() > 0.5
        ]
        if not num_cols:
            QMessageBox.warning(self, "Błąd",
                "Zaznaczone kolumny nie zawierają danych numerycznych.")
            return

        col_series = pd.to_numeric(self.df[col_filter], errors="coerce")
        total = len(self.df)

        # Budowanie tabeli wynikowej
        lines = []
        lines.append(f"ANALIZA WPLYWU PROGU: {col_filter} {op} X")
        lines.append(f"Kolumny analizowane: {', '.join(num_cols)}")
        lines.append("=" * 70)
        header = f"{'Prog':<10} {'N rekordow':<14} {'% zbioru':<12}"
        header += "".join(f"{c[:12]:<14}" for c in num_cols)
        lines.append(header)
        lines.append("-" * 70)

        for thresh in sorted(thresholds):
            if op == ">":
                mask = col_series > thresh
            elif op == ">=":
                mask = col_series >= thresh
            elif op == "<":
                mask = col_series < thresh
            else:
                mask = col_series <= thresh

            subset = self.df.loc[mask.fillna(False)]
            n = len(subset)
            pct = n / total * 100 if total > 0 else 0

            means = []
            for c in num_cols:
                s = pd.to_numeric(subset[c], errors="coerce").dropna()
                means.append(f"{s.mean():.2f}" if len(s) > 0 else "N/A")

            line = f"{thresh:<10.1f} {n:<14,} {pct:<12.1f}"
            line += "".join(f"{m:<14}" for m in means)
            lines.append(line)

        lines.append("-" * 70)
        lines.append("")
        lines.append("Interpretacja: tabela pokazuje jak zmiana progu wplywu")
        lines.append("na liczbe rekordow i srednie wartosci wybranych kolumn.")

        self.threshold_result.setPlainText("\n".join(lines))
        self.log(f"Analiza progow: {col_filter} {op} {thresholds}")

    # =========================================================================
    # EKSPORT CSV
    # Zapisuje przefiltrowane dane do pliku CSV z separatorem średnika.
    # =========================================================================
    def export_csv(self):
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Brak danych", "Brak danych do eksportu.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Zapisz dane CSV", "wynik.csv", "CSV Files (*.csv)"
        )
        if not filename:
            return

        if not filename.lower().endswith(".csv"):
            filename += ".csv"

        try:
            self.df_filtered.to_csv(filename, index=False, sep=";")
            self.log(f"Zapisano dane CSV: {filename}")
            QMessageBox.information(self, "Sukces", f"Dane zapisano jako:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Błąd CSV", f"Nie udało się zapisać pliku CSV:\n{e}")
            self.log(f"Błąd eksportu CSV: {e}")

    # =========================================================================
    # EKSPORT PDF — GENEROWANIE RAPORTU (ReportLab Platypus)
    # Buduje wielostronicowy dokument PDF przy użyciu ReportLab Platypus.
    # Struktura raportu: strona tytułowa → metodologia → statystyki → wykres → wnioski.
    # Import ReportLab jest opóźniony — nie blokuje startu aplikacji.
    # Czcionka TTF rejestrowana dynamicznie dla obsługi polskich znaków.
    # =========================================================================
    def export_pdf(self):

        # --- SPRAWDZENIE DOSTĘPNOŚCI DANYCH DO RAPORTU ---
        has_data = self.df_filtered is not None and not self.df_filtered.empty
        has_sql = hasattr(self, "sql_df") and self.sql_df is not None

        if not has_data and not has_sql:
            QMessageBox.warning(self, "Brak danych", "Brak danych do eksportu.")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table,
                TableStyle, PageBreak, HRFlowable
            )
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import Image as RLImage
            import os
        except Exception as e:
            QMessageBox.warning(self, "Brak biblioteki",
                                "Zainstaluj: pip install reportlab")
            return

        # --- REJESTRACJA CZCIONKI Z OBSŁUGĄ POLSKICH ZNAKÓW ---
        # Próbuje zarejestrować czcionkę regularną i bold (arial/calibri/dejavu).
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("PolishFont", fp))
                    bold_path = fp.replace("arial.ttf", "arialbd.ttf").replace(
                        "calibri.ttf", "calibrib.ttf").replace(
                        "DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont("PolishFontBold", bold_path))
                        font_bold = "PolishFontBold"
                    font_name = "PolishFont"
                    break
                except Exception:
                    continue

        # --- DIALOG ZAPISU PLIKU PDF ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"raport_{timestamp}.pdf"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Zapisz raport PDF", default_name, "PDF Files (*.pdf)"
        )
        if not filename:
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        try:
            doc = SimpleDocTemplate(
                filename, pagesize=A4,
                topMargin=2 * cm, bottomMargin=2 * cm,
                leftMargin=2.5 * cm, rightMargin=2.5 * cm
            )

            # --- DEFINICJA STYLÓW TEKSTU ---
            styles = getSampleStyleSheet()
            style_title = ParagraphStyle("Title",
                                         fontName=font_bold, fontSize=22,
                                         textColor=colors.HexColor("#1a2e4a"),
                                         alignment=TA_CENTER, spaceAfter=6)
            style_subtitle = ParagraphStyle("Subtitle",
                                            fontName=font_name, fontSize=12,
                                            textColor=colors.HexColor("#555555"),
                                            alignment=TA_CENTER, spaceAfter=4)
            style_h1 = ParagraphStyle("H1",
                                      fontName=font_bold, fontSize=14,
                                      textColor=colors.HexColor("#1a2e4a"),
                                      spaceBefore=16, spaceAfter=8)
            style_h2 = ParagraphStyle("H2",
                                      fontName=font_bold, fontSize=12,
                                      textColor=colors.HexColor("#2563eb"),
                                      spaceBefore=12, spaceAfter=6)
            style_body = ParagraphStyle("Body",
                                        fontName=font_name, fontSize=10,
                                        textColor=colors.HexColor("#1f2937"),
                                        leading=16, alignment=TA_JUSTIFY,
                                        spaceAfter=8)
            style_mono = ParagraphStyle("Mono",
                                        fontName=font_name, fontSize=9,
                                        textColor=colors.HexColor("#374151"),
                                        leading=14, spaceAfter=4)

            story = []

            # -----------------------------------------------------------------
            # SEKCJA PDF: STRONA TYTUŁOWA
            # Tytuł, podtytuł, data generowania, liczba rekordów i kolumn.
            # -----------------------------------------------------------------
            story.append(Spacer(1, 3 * cm))
            story.append(Paragraph("Analizator Danych Pacjentów", style_title))
            story.append(Paragraph("Raport z analizy danych medycznych", style_subtitle))
            story.append(Spacer(1, 0.5 * cm))
            story.append(HRFlowable(width="100%", thickness=1,
                                    color=colors.HexColor("#2563eb")))
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph(
                f"Data wygenerowania: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                style_subtitle))

            if has_data:
                story.append(Paragraph(
                    f"Liczba rekordów: {len(self.df_filtered):,} "
                    f"(z {len(self.df):,} całkowitych)",
                    style_subtitle))
                story.append(Paragraph(
                    f"Liczba kolumn: {len(self.df_filtered.columns)}",
                    style_subtitle))

            story.append(PageBreak())

            # -----------------------------------------------------------------
            # SEKCJA PDF: METODOLOGIA
            # Cel analizy i 8-krokowy pipeline przetwarzania danych.
            # Jeśli aktywne filtry — wypisuje ich listę z logiką AND/OR.
            # -----------------------------------------------------------------
            story.append(Paragraph("1. Cel i metodologia", style_h1))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#d1d5db")))
            story.append(Spacer(1, 0.3 * cm))

            story.append(Paragraph("Cel analizy", style_h2))
            story.append(Paragraph(
                "Niniejszy raport przedstawia wyniki analizy danych medycznych "
                "z wykorzystaniem aplikacji Analizator Danych Pacjentów. "
                "Celem analizy jest eksploracja danych klinicznych, identyfikacja "
                "wzorców oraz ocena wpływu zastosowanych parametrów filtrowania "
                "na uzyskane wyniki statystyczne.",
                style_body))

            story.append(Paragraph("Pipeline przetwarzania danych", style_h2))
            pipeline_steps = [
                ("1. Import danych", "Wczytanie danych z pliku CSV, Excel lub bazy SQLite."),
                ("2. Walidacja", "Sprawdzenie kompletności danych, wykrycie braków i błędów typów."),
                ("3. Czyszczenie", "Usunięcie nadmiarowych spacji, ujednolicenie formatów liczbowych."),
                ("4. Filtrowanie", "Zastosowanie warunków filtrowania z operatorami numerycznymi i tekstowymi."),
                ("5. Analiza SQL", "Wykonanie zapytań JOIN między tabelami relacyjnymi."),
                ("6. Statystyki", "Obliczenie metryk: count, mean, median, min, max, std z grupowaniem."),
                ("7. Wizualizacja", "Generowanie wykresów z automatycznym doborem typu na podstawie danych."),
                ("8. Raport", "Eksport wyników do pliku PDF z opisem metodologii i wnioskami."),
            ]
            for step, desc in pipeline_steps:
                story.append(Paragraph(
                    f"<b>{step}:</b> {desc}", style_body))

            # Lista aktywnych filtrów
            if self.filters:
                story.append(Paragraph("Zastosowane filtry", style_h2))
                logic = "AND" if self.radio_and.isChecked() else "OR"
                for col, op, val in self.filters:
                    story.append(Paragraph(
                        f"• {col} {op} {val}", style_mono))
                story.append(Paragraph(
                    f"Logika łączenia warunków: {logic}", style_mono))

            story.append(PageBreak())

            # -----------------------------------------------------------------
            # SEKCJA PDF: STATYSTYKI
            # Tekst z zakładki Statystyki + tabela describe() dla kolumn num.
            # Wyniki SQL wyświetlane jako tabela (max 20 wierszy).
            # -----------------------------------------------------------------
            story.append(Paragraph("2. Wyniki analizy statystycznej", style_h1))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#d1d5db")))
            story.append(Spacer(1, 0.3 * cm))

            # Statystyki z edytora tekstowego zakładki Statystyki
            stats_text = self.stats_text.toPlainText()
            if stats_text:
                story.append(Paragraph("Obliczone metryki", style_h2))
                for line in stats_text.splitlines():
                    if line.strip():
                        story.append(Paragraph(line, style_mono))
                story.append(Spacer(1, 0.3 * cm))

            # Tabela describe() dla kolumn numerycznych (dane przefiltrowane)
            if has_data:
                story.append(Paragraph("Statystyki opisowe (dane przefiltrowane)", style_h2))
                try:
                    desc = self.df_filtered.describe(include="number").round(3)
                    table_data = [[""] + list(desc.columns)]
                    for idx in desc.index:
                        row = [idx] + [str(v) for v in desc.loc[idx]]
                        table_data.append(row)

                    col_width = (doc.width - 2 * cm) / len(desc.columns + [""])
                    col_widths = [3 * cm] + [col_width] * len(desc.columns)

                    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
                    tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2e4a")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), font_bold),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("FONTNAME", (0, 1), (-1, -1), font_name),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                         [colors.white, colors.HexColor("#f0f4ff")]),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(tbl)
                except Exception:
                    pass

            # Tabela wyników SQL (max 20 wierszy)
            if has_sql:
                story.append(Spacer(1, 0.5 * cm))
                story.append(Paragraph("Wyniki zapytania SQL", style_h2))
                try:
                    sql_preview = self.sql_df.head(20)
                    table_data = [list(sql_preview.columns)]
                    for _, row in sql_preview.iterrows():
                        table_data.append([str(v) for v in row])

                    n_cols = len(sql_preview.columns)
                    col_w = doc.width / n_cols
                    tbl = Table(table_data,
                                colWidths=[col_w] * n_cols, repeatRows=1)
                    tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), font_bold),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("FONTNAME", (0, 1), (-1, -1), font_name),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                         [colors.white, colors.HexColor("#f0f4ff")]),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]))
                    story.append(tbl)
                    if len(self.sql_df) > 20:
                        story.append(Paragraph(
                            f"Pokazano 20 z {len(self.sql_df)} wyników.",
                            style_mono))
                except Exception:
                    pass

            # -----------------------------------------------------------------
            # SEKCJA PDF: WYKRES
            # Wstawia obraz z bufora self._plot_buf (jeśli wykres był wygenerowany).
            # -----------------------------------------------------------------
            if hasattr(self, "_plot_buf") and self._plot_buf is not None:
                story.append(PageBreak())
                story.append(Paragraph("3. Wizualizacja danych", style_h1))
                story.append(HRFlowable(width="100%", thickness=0.5,
                                        color=colors.HexColor("#d1d5db")))
                story.append(Spacer(1, 0.3 * cm))
                try:
                    self._plot_buf.seek(0)
                    img = RLImage(self._plot_buf,
                                  width=doc.width, height=doc.width * 0.6)
                    story.append(img)
                except Exception:
                    pass

            # -----------------------------------------------------------------
            # SEKCJA PDF: WNIOSKI
            # Automatycznie generowane wnioski na podstawie danych i filtrów:
            # ubytki rekordów, braki danych, liczba kolumn, wyniki SQL.
            # -----------------------------------------------------------------
            story.append(PageBreak())
            story.append(Paragraph("4. Wnioski", style_h1))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#d1d5db")))
            story.append(Spacer(1, 0.3 * cm))

            wnioski = []

            if has_data:
                n_total = len(self.df)
                n_filt = len(self.df_filtered)
                pct = (n_filt / n_total * 100) if n_total > 0 else 0
                wnioski.append(
                    f"Po zastosowaniu {len(self.filters)} filtrów pozostało "
                    f"{n_filt:,} rekordów ({pct:.1f}% zbioru wejściowego)."
                )

                # Braki danych w kolumnach
                missing = self.df_filtered.isnull().sum()
                missing_cols = missing[missing > 0]
                if len(missing_cols) > 0:
                    wnioski.append(
                        f"Wykryto braki danych w {len(missing_cols)} kolumnach: "
                        f"{', '.join(missing_cols.index[:3])}."
                    )
                else:
                    wnioski.append("Zbiór danych nie zawiera braków danych.")

                # Liczba kolumn numerycznych i tekstowych
                num_cols = self.df_filtered.select_dtypes(include="number").columns
                if len(num_cols) > 0:
                    wnioski.append(
                        f"Analiza obejmuje {len(num_cols)} kolumn numerycznych "
                        f"i {len(self.df_filtered.columns) - len(num_cols)} "
                        f"kolumn tekstowych."
                    )

            if has_sql:
                wnioski.append(
                    f"Zapytanie SQL zwróciło {len(self.sql_df):,} rekordów "
                    f"z {len(self.sql_df.columns)} kolumnami."
                )

            wnioski.append(
                "Analiza została przeprowadzona z wykorzystaniem aplikacji "
                "Analizator Danych Pacjentów, zbudowanej w Pythonie z użyciem "
                "bibliotek pandas, matplotlib i PyQt5."
            )

            for w in wnioski:
                story.append(Paragraph(f"• {w}", style_body))

            # Stopka końcowa z datą i godziną generowania
            story.append(Spacer(1, 1 * cm))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#d1d5db")))
            story.append(Paragraph(
                f"Raport wygenerowany: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                style_subtitle))

            # --- ZAPIS DOKUMENTU PDF ---
            doc.build(story)

            self.log(f"Zapisano raport: {filename}")
            QMessageBox.information(self, "Sukces",
                                    f"Raport zapisano jako:\n{filename}")

        except Exception as e:
            QMessageBox.warning(self, "Błąd PDF",
                                f"Nie udało się zapisać raportu:\n{e}")
            self.log(f"Błąd eksportu PDF: {e}")
