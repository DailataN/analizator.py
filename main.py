# =============================================================================
# IMPORT BIBLIOTEK
# =============================================================================
from PyQt5.QtWidgets import QApplication
from ui.main_window import AnalizatorCSV
import sys


# =============================================================================
# PUNKT WEJŚCIA APLIKACJI
# Tworzy instancję QApplication (wymagana przez PyQt5 jako pierwsza),
# inicjalizuje główne okno AnalizatorCSV, wyświetla je
# i uruchamia pętlę zdarzeń Qt. sys.exit() zapewnia czysty kod wyjścia
# po zamknięciu okna.
# =============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnalizatorCSV()
    window.show()
    sys.exit(app.exec_())
