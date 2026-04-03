# IMPORT BIBLIOTEK
from ui.table_model import DataFrameTableModel
from data.loader import load_csv_file, load_excel_file
from data.validator import validate_dataframe
from data.cleaner import clean_dataframe
from data.database import load_table_from_db
from analysis.stats import calculate_selected_stats, compare_filter_impact, analyze_filter_impact
from analysis.visualization import create_plot

import io
import pandas as pd
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt

from datetime import datetime

# NARZĘDZIA GUI
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
1

# WĄTEK DO WCZYTYWANIA PLIKÓW
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


# GŁÓWNE OKNO APLIKACJI
class AnalizatorCSV(QMainWindow):
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

    def initUI(self):
        # MENU
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

        # CENTRALNY UKŁAD
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)

        # PANEL BOCZNY
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        self.btn_load = QPushButton("📂 Wczytaj plik")
        self.btn_load_sql = QPushButton("🗄️ Wczytaj z bazy SQL")
        self.btn_filter = QPushButton("⚙️ Filtry")
        self.btn_stats = QPushButton("📊 Statystyki")
        self.btn_plot = QPushButton("📈 Wizualizacja")
        self.btn_compare = QPushButton("📉 Analiza wpływu filtrów")
        self.btn_export_csv = QPushButton("💾 Eksport CSV")
        self.btn_export_pdf = QPushButton("🧾 Eksport PDF")

        for b in [
            self.btn_load,
            self.btn_load_sql,
            self.btn_filter,
            self.btn_stats,
            self.btn_plot,
            self.btn_compare,
            self.btn_export_csv,
            self.btn_export_pdf
        ]:
            b.setMinimumHeight(40)
            panel_layout.addWidget(b)

        panel_layout.addStretch()
        splitter.addWidget(panel)

        # ZAKŁADKI
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        # PODGLĄD DANYCH
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

        # FILTRY
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

        self.input_value = QLineEdit()
        self.input_value.setPlaceholderText("np. 50 lub 5,5")
        vbox_filter.addWidget(self.input_value)

        self.combo_value = QComboBox()
        self.combo_value.setVisible(False)
        vbox_filter.addWidget(self.combo_value)

        btn_condition_row = QHBoxLayout()
        self.btn_add_condition = QPushButton("Dodaj warunek")
        self.btn_remove_condition = QPushButton("Usuń zaznaczony")
        self.btn_remove_condition.setEnabled(False)
        btn_condition_row.addWidget(self.btn_add_condition)
        btn_condition_row.addWidget(self.btn_remove_condition)
        vbox_filter.addLayout(btn_condition_row)

        vbox_filter.addWidget(QLabel("Aktywne warunki:"))
        self.list_filters = QListWidget()
        vbox_filter.addWidget(self.list_filters)

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

        self.btn_apply_filters = QPushButton("Zastosuj filtry")
        self.btn_clear_filters = QPushButton("Wyczyść filtry")

        hbox_buttons = QHBoxLayout()
        hbox_buttons.addWidget(self.btn_apply_filters)
        hbox_buttons.addWidget(self.btn_clear_filters)
        vbox_filter.addLayout(hbox_buttons)

        vbox_filter.addStretch()
        self.tabs.addTab(self.tab_filter, "Filtry")

        # STATYSTYKI
        self.tab_stats = QWidget()
        vbox_stats = QVBoxLayout(self.tab_stats)

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

        vbox_stats.addWidget(QLabel("Kolumny do analizy (zaznacz co chcesz):"))
        self.list_cols = QListWidget()
        self.list_cols.setSelectionMode(QListWidget.MultiSelection)
        vbox_stats.addWidget(self.list_cols)

        grp = QHBoxLayout()
        grp.addWidget(QLabel("Grupuj wg (opcjonalnie):"))
        self.combo_groupby = QComboBox()
        grp.addWidget(self.combo_groupby)
        vbox_stats.addLayout(grp)

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

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        vbox_stats.addWidget(self.stats_text)

        self.tabs.addTab(self.tab_stats, "Statystyki")

        # WIZUALIZACJA
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

        btn_row = QHBoxLayout()
        self.btn_draw_plot = QPushButton("Rysuj wykres")
        self.btn_fullscreen = QPushButton("🔍 Powiększ wykres")
        self.btn_fullscreen.setEnabled(False)
        btn_row.addWidget(self.btn_draw_plot)
        btn_row.addWidget(self.btn_fullscreen)
        vbox_plot.addLayout(btn_row)

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

        self.chk_yrange.toggled.connect(self.input_ymin.setEnabled)
        self.chk_yrange.toggled.connect(self.input_ymax.setEnabled)

        self.plot_info_label = QLabel("Brak danych do wizualizacji.")
        vbox_plot.addWidget(self.plot_info_label)

        self.plot_container = QWidget()
        self.plot_container_layout = QVBoxLayout(self.plot_container)
        self.plot_container_layout.setContentsMargins(0, 0, 0, 0)
        vbox_plot.addWidget(self.plot_container)

        self.tabs.addTab(self.tab_plot, "Wizualizacja")

        # LOGI
        logs_frame = QFrame()
        logs_layout = QVBoxLayout(logs_frame)
        logs_layout.addWidget(QLabel("Logi:"))

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        logs_layout.addWidget(self.logs)

        main_layout.addWidget(splitter)
        main_layout.addWidget(logs_frame)

        # POŁĄCZENIA
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load_sql.clicked.connect(self.load_sql)
        self.btn_filter.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.btn_stats.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.btn_plot.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        self.btn_compare.clicked.connect(self.compare_filters)
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

    def log(self, msg):
        self.logs.append(f"> {msg}")

    def _parse_numeric_value(self, value_text):
        return float(value_text.replace(",", "."))

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

    # WCZYTYWANIE PLIKU
    def load_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik", "",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        if not filename:
            return
        self._start_loader(filename=filename)

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
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
                    conn
                )["name"].tolist()
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można otworzyć bazy:\n{e}")
            return

        if not tables:
            QMessageBox.warning(self, "Brak tabel", "Baza danych nie zawiera żadnych tabel.")
            return

        # Pokaż listę tabel do wyboru bez znaku zapytania
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

    def _on_load_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.btn_load.setEnabled(True)
        self.btn_load_sql.setEnabled(True)
        QMessageBox.warning(self, "Błąd wczytywania", error_msg)
        self.log(f"Błąd wczytywania: {error_msg}")

    # TABLICA DANYCH
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

    # FILTRY
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

        col_cache = {}
        for col, op, val in self.filters:
            if col not in col_cache:
                series_str = self.df[col].astype(str)
                series_num = pd.to_numeric(
                    series_str.str.replace(",", ".", regex=False),
                    errors="coerce"
                )
                col_cache[col] = (series_str, series_num)

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

    # STATYSTYKI
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

    # WYKRES
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

    # ANALIZA WPŁYWU FILTRÓW
    def compare_filters(self):
        if self.df is None or self.df_filtered is None:
            QMessageBox.warning(self, "Brak danych", "Najpierw wczytaj dane.")
            return

        if not self.filters:
            QMessageBox.information(self, "Brak filtrów", "Najpierw dodaj i zastosuj filtry.")
            return

        try:
            # Podstawowe porównanie rekordów
            basic = compare_filter_impact(self.df, self.df_filtered)

            # Szczegółowa analiza wpływu na statystyki
            numeric_cols = self.df.select_dtypes(include="number").columns.tolist()
            detailed = analyze_filter_impact(self.df, self.df_filtered, numeric_cols)

            # Pokaż w osobnym oknie z możliwością scrollowania
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

    # EKSPORT CSV
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

    # EKSPORT PDF
    def export_pdf(self):
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Brak danych", "Brak danych do eksportu.")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.utils import ImageReader
        except Exception as e:
            QMessageBox.warning(
                self, "Brak biblioteki",
                "Do eksportu PDF potrzebny jest pakiet 'reportlab'.\nZainstaluj: pip install reportlab"
            )
            self.log(f"Brak reportlab: {e}")
            return

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
            c = rl_canvas.Canvas(filename, pagesize=A4)
            width, height = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Raport analizy danych CSV")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 70, "Wygenerowano przez Analizator danych pacjentów")

            stats_text = self.stats_text.toPlainText()
            if not stats_text and self.df_filtered is not None:
                try:
                    desc = self.df_filtered.describe(include="all")
                    stats_text = str(desc)
                except Exception:
                    stats_text = "Brak statystyk (nie udało się wygenerować)."

            c.setFont("Helvetica", 11)
            text_obj = c.beginText(50, height - 110)

            for line in stats_text.splitlines():
                if text_obj.getY() < 120:
                    c.drawText(text_obj)
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    text_obj = c.beginText(50, height - 50)
                text_obj.textLine(line)

            c.drawText(text_obj)

            if self.last_fig:
                buf = io.BytesIO()
                self.last_fig.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                img = ImageReader(buf)
                c.showPage()
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, height - 50, "Wykres")
                c.drawImage(img, 50, 150, width - 100, height - 250, preserveAspectRatio=True)
                buf.close()

            c.save()

            self.log(f"Zapisano raport: {filename}")
            QMessageBox.information(self, "Sukces", f"Raport zapisano jako:\n{filename}")

        except Exception as e:
            QMessageBox.warning(self, "Błąd PDF", f"Nie udało się zapisać raportu:\n{e}")
            self.log(f"Błąd eksportu PDF: {e}")