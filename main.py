from PyQt5.QtWidgets import QApplication
from ui.main_window import AnalizatorCSV
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnalizatorCSV()
    window.show()
    sys.exit(app.exec_())