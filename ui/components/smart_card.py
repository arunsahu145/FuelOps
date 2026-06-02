"""
Petrol Pump Finance Manager ERP — Dashboard Smart Card
Stunning visual metric cards with click actions and micro-interactions.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Signal, Qt
from ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR, ACCENT_PRIMARY


class SmartCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, val: str, sub_val: str = "", color_accent: str = ACCENT_PRIMARY, parent=None):
        super().__init__(parent)
        self.setObjectName("SmartCard")
        self.setCursor(Qt.PointingHandCursor)
        self.color_accent = color_accent
        self._init_ui(title, val, sub_val)

    def _init_ui(self, title: str, val: str, sub_val: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        # Apply a subtle left colored accent border
        self.setStyleSheet(f"""
            QFrame#SmartCard {{
                background-color: #1e293b;
                border: 1px solid {BORDER_COLOR};
                border-left: 4px solid {self.color_accent};
                border-radius: 8px;
            }}
            QFrame#SmartCard:hover {{
                background-color: #33415550;
                border-color: {self.color_accent};
            }}
        """)

        # Title
        self.title_label = QLabel(title.upper(), self)
        self.title_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {TEXT_SECONDARY}; letter-spacing: 0.5px;")
        layout.addWidget(self.title_label)

        # Main Value
        self.val_label = QLabel(val, self)
        self.val_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        layout.addWidget(self.val_label)

        # Subtitle / Details
        self.sub_label = QLabel(sub_val, self)
        self.sub_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        self.sub_label.setWordWrap(True)
        layout.addWidget(self.sub_label)

    def update_data(self, val: str, sub_val: str = ""):
        """Update metrics in the card dynamically."""
        self.val_label.setText(val)
        if sub_val:
            self.sub_label.setText(sub_val)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
