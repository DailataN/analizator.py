# =============================================================================
# IMPORT BIBLIOTEK
# =============================================================================
import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, Qt


# =============================================================================
# MODEL TABELI — DataFrameTableModel
# Klasa pośrednicząca między pandas DataFrame a widżetem QTableView.
# Dziedziczy po QAbstractTableModel, implementując interfejs wymagany przez Qt
# do wyświetlania danych w tabeli (MVC — warstwa Model).
# =============================================================================
class DataFrameTableModel(QAbstractTableModel):

    # -------------------------------------------------------------------------
    # INICJALIZACJA MODELU
    # Przyjmuje opcjonalny DataFrame. Jeśli nie podano — tworzy pusty DataFrame.
    # -------------------------------------------------------------------------
    def __init__(self, df=None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    # -------------------------------------------------------------------------
    # AKTUALIZACJA DANYCH MODELU
    # Zastępuje wewnętrzny DataFrame nowym zestawem danych.
    # beginResetModel / endResetModel powiadamia widok o pełnym odświeżeniu,
    # co zapobiega niespójnościom między modelem a wyświetlaną tabelą.
    # -------------------------------------------------------------------------
    def set_dataframe(self, df):
        self.beginResetModel()
        self._df = df if df is not None else pd.DataFrame()
        self.endResetModel()

    # -------------------------------------------------------------------------
    # LICZBA WIERSZY
    # Zwracana na podstawie shape[0] DataFrame.
    # -------------------------------------------------------------------------
    def rowCount(self, parent=None):
        return self._df.shape[0]

    # -------------------------------------------------------------------------
    # LICZBA KOLUMN
    # Zwracana na podstawie shape[1] DataFrame.
    # -------------------------------------------------------------------------
    def columnCount(self, parent=None):
        return self._df.shape[1]

    # -------------------------------------------------------------------------
    # DANE KOMÓRKI
    # Wywoływana przez Qt dla każdej komórki tabeli.
    # Obsługuje dwa role:
    #   DisplayRole      — tekst wyświetlany w komórce (NaN → pusty string)
    #   TextAlignmentRole — wyrównanie do lewej i pionowo do środka
    # Zwraca None dla nieważnych indeksów lub pustego DataFrame.
    # -------------------------------------------------------------------------
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df.empty:
            return None

        row = index.row()
        col = index.column()

        if row >= self._df.shape[0] or col >= self._df.shape[1]:
            return None

        value = self._df.iat[row, col]

        if role == Qt.DisplayRole:
            if pd.isna(value):
                return ""
            return str(value)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    # -------------------------------------------------------------------------
    # NAGŁÓWKI TABELI
    # Dostarcza etykiety dla nagłówków poziomych (nazwy kolumn DataFrame)
    # i pionowych (numery wierszy, liczone od 1).
    # Zwraca None dla pustego DataFrame lub indeksów poza zakresem.
    # -------------------------------------------------------------------------
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if self._df.empty:
            return None

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if 0 <= section < self._df.shape[1]:
                    return str(self._df.columns[section])
            elif orientation == Qt.Vertical:
                if 0 <= section < self._df.shape[0]:
                    return str(section + 1)

        return None