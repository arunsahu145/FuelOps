"""
Petrol Pump Finance Manager ERP — Styled Data Table
Clean table with proper row colors for readability, and optional delete button per row.
"""
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt, Signal
from ui.theme import (
    BG_SURFACE, BG_SURFACE_LIGHT, BG_MAIN, TEXT_PRIMARY, TEXT_SECONDARY,
    BORDER_COLOR, ACCENT_DANGER
)


class DataTable(QTableWidget):
    """Styled data table with optional per-row delete buttons."""

    row_delete_requested = Signal(int)  # Emits the row_id when delete is clicked

    def __init__(self, headers: list, parent=None, enable_delete: bool = False):
        self._enable_delete = enable_delete
        self._headers = list(headers)
        if enable_delete:
            self._headers.append("")  # Delete column header (empty)

        super().__init__(parent)
        self.setColumnCount(len(self._headers))
        self.setHorizontalHeaderLabels(self._headers)
        self._row_ids = []  # Stores the record IDs for each row
        self._init_style()

    def _init_style(self):
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(False)  # We use custom row colors
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.NoFocus)

        header = self.horizontalHeader()
        header.setHighlightSections(False)

        # Stretch all columns except the last one (delete button) if delete enabled
        if self._enable_delete:
            for i in range(len(self._headers) - 1):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            header.setSectionResizeMode(len(self._headers) - 1, QHeaderView.Fixed)
            self.setColumnWidth(len(self._headers) - 1, 50)
        else:
            header.setSectionResizeMode(QHeaderView.Stretch)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(38)

        # Clean table styles — uniform dark surface with subtle row separation
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                font-size: 13px;
                color: {TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {BG_SURFACE_LIGHT}50;
            }}
            QTableWidget::item:selected {{
                background-color: #3b82f620;
                color: {TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {BG_SURFACE_LIGHT};
                color: {TEXT_PRIMARY};
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid {BORDER_COLOR};
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 0.3px;
            }}
        """)

    def populate(self, rows_data: list, row_ids: list = None):
        """
        Populate rows dynamically.
        rows_data: list of tuples with column values.
        row_ids: optional list of record IDs (used for delete callbacks).
        """
        self.clearContents()
        self.setRowCount(len(rows_data))
        self._row_ids = row_ids or [None] * len(rows_data)

        for row_idx, row_values in enumerate(rows_data):
            # Alternate row background for readability
            is_even = row_idx % 2 == 0
            row_bg = BG_SURFACE if is_even else f"{BG_SURFACE_LIGHT}30"

            for col_idx, val in enumerate(row_values):
                item = QTableWidgetItem(str(val))
                # Right-align monetary/litre values
                if isinstance(val, str) and (val.startswith("₹") or val.endswith(" L")):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

                # Set subtle alternating background
                if not is_even:
                    from PySide6.QtGui import QColor
                    item.setBackground(QColor(51, 65, 85, 30))  # slate-700 with 12% opacity

                self.setItem(row_idx, col_idx, item)

            # Add delete button if enabled
            if self._enable_delete:
                delete_col = len(self._headers) - 1
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                btn_layout.setAlignment(Qt.AlignCenter)

                del_btn = QPushButton("🗑", btn_widget)
                del_btn.setFixedSize(28, 28)
                del_btn.setToolTip("Delete this entry")
                del_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid {BORDER_COLOR};
                        border-radius: 4px;
                        font-size: 13px;
                        padding: 0;
                    }}
                    QPushButton:hover {{
                        background-color: {ACCENT_DANGER}30;
                        border-color: {ACCENT_DANGER};
                    }}
                """)
                record_id = self._row_ids[row_idx] if row_idx < len(self._row_ids) else None
                del_btn.clicked.connect(
                    lambda checked, rid=record_id: self._on_delete_clicked(rid)
                )
                btn_layout.addWidget(del_btn)
                self.setCellWidget(row_idx, delete_col, btn_widget)

    def _on_delete_clicked(self, record_id):
        """Emit the row_delete_requested signal with the record ID."""
        if record_id is not None:
            self.row_delete_requested.emit(record_id)
