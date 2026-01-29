from PyQt5.QtCore import QAbstractTableModel, Qt


class pandasModel(QAbstractTableModel):
    def __init__(self, data, editable=False):
        QAbstractTableModel.__init__(self)
        self._data = data
        self.editable = editable

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parnet=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
            elif role == Qt.TextAlignmentRole:
                return Qt.AlignCenter


    def setData(self, index, value, role):
        if role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            return True
        return False

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]

    def flags(self, index):
        if self.editable:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def sort(self, col, order):
        """sort table by given column number col"""
        self.layoutAboutToBeChanged.emit()
        self._data = self._data.sort_values(
            self._data.columns[col], ascending=order == Qt.AscendingOrder)
        self.layoutChanged.emit()

    def updateData(self, listt):
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                if self._data.iloc[row, col] != listt.iloc[row, col]:
                    self._data.iloc[row, col] = listt.iloc[row, col]
                    self.dataChanged.emit(self.index(
                        row, col), self.index(row, col))