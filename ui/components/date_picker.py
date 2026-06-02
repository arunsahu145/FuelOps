"""
Petrol Pump Finance Manager ERP — Enhanced Date Picker Widget
Clean horizontal navigation with Prev/Next buttons, Today shortcut, and day label.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QDateEdit, QAbstractButton
from PySide6.QtCore import Signal, QDate, Qt
from ui.theme import (
    ACCENT_PRIMARY, ACCENT_SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY,
    BG_SURFACE, BG_SURFACE_LIGHT, BG_MAIN, BORDER_COLOR
)


class ClickableDateEdit(QDateEdit):
    """Subclass of QDateEdit that opens the calendar popup when clicked anywhere."""
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Find the drop-down button and programmatically click it to open the calendar popup
        for button in self.findChildren(QAbstractButton):
            button.click()
            break


class DatePicker(QWidget):
    date_changed = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── "Today" quick-jump button ──
        self.today_btn = QPushButton("Today", self)
        self.today_btn.setFixedHeight(32)
        self.today_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_PRIMARY}20;
                color: {ACCENT_PRIMARY};
                border: 1px solid {ACCENT_PRIMARY}50;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_PRIMARY}40;
                border-color: {ACCENT_PRIMARY};
            }}
        """)
        self.today_btn.clicked.connect(self._go_today)
        layout.addWidget(self.today_btn)

        # ── Prev Day Button ──
        self.prev_btn = QPushButton("<", self)
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_SURFACE_LIGHT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_PRIMARY}30;
                border-color: {ACCENT_PRIMARY};
            }}
        """)
        self.prev_btn.clicked.connect(self._prev_day)
        layout.addWidget(self.prev_btn)

        # ── Date Editor with calendar popup ──
        self.date_edit = ClickableDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFixedWidth(140)
        self.date_edit.setFixedHeight(32)
        self.date_edit.setDisplayFormat("dd MMM yyyy")
        self.date_edit.setAlignment(Qt.AlignCenter)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        layout.addWidget(self.date_edit)

        # ── Next Day Button ──
        self.next_btn = QPushButton(">", self)
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_SURFACE_LIGHT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_PRIMARY}30;
                border-color: {ACCENT_PRIMARY};
            }}
        """)
        self.next_btn.clicked.connect(self._next_day)
        layout.addWidget(self.next_btn)

        # ── Day-of-week label ──
        self.day_label = QPushButton("", self)
        self.day_label.setFixedHeight(32)
        self.day_label.setEnabled(False)
        self._update_day_label()
        layout.addWidget(self.day_label)

    def _prev_day(self):
        self.date_edit.setDate(self.date_edit.date().addDays(-1))

    def _next_day(self):
        self.date_edit.setDate(self.date_edit.date().addDays(1))

    def _go_today(self):
        self.date_edit.setDate(QDate.currentDate())

    def _on_date_changed(self, qdate: QDate):
        self._update_day_label()
        self.date_changed.emit(qdate)

    def _update_day_label(self):
        """Show day-of-week or 'Today' if current date."""
        qdate = self.date_edit.date()
        is_today = qdate == QDate.currentDate()
        if is_today:
            text = "Today"
            color = ACCENT_SUCCESS
        else:
            text = qdate.toString("dddd")
            color = TEXT_SECONDARY

        self.day_label.setText(f"  {text}  ")
        self.day_label.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: none;
                font-size: 11px;
                font-weight: 600;
            }}
        """)

    def get_date(self) -> QDate:
        return self.date_edit.date()

    def get_date_str(self) -> str:
        """Returns date formatted as YYYY-MM-DD."""
        return self.date_edit.date().toString("yyyy-MM-dd")

    def set_date(self, qdate: QDate):
        self.date_edit.setDate(qdate)
