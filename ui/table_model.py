import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, Qt


class DataFrameTableModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    def set_dataframe(self, df):
        self.beginResetModel()
        self._df = df if df is not None else pd.DataFrame()
        self.endResetModel()

    def rowCount(self, parent=None):
        return self._df.shape[0]

    def columnCount(self, parent=None):
        return self._df.shape[1]

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