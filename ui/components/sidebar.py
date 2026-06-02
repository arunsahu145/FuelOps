"""
Petrol Pump Finance Manager ERP — Navigation Sidebar
Sleek sidebar with emoji icons and polished navigation.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Signal, Qt
from ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_DANGER


class Sidebar(QFrame):
    page_changed = Signal(str)  # Emits page name when a button is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        self.setFixedWidth(200)
        self.buttons = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(4)

        # ── Title / Logo ──
        self.title_label = QLabel("⛽  PETROL PUMP", self)
        self.title_label.setObjectName("SidebarTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        subtitle = QLabel("ERP Manager", self)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"font-size: 10px; color: {TEXT_SECONDARY}; padding-bottom: 8px;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # ── Navigation Buttons with Icons ──
        menu_items = [
            ("📊  Dashboard", "dashboard"),
            ("⛽  Fuel Prices", "fuel"),
            ("🔧  Nozzle Map", "nozzle"),
            ("📝  Shift Entry", "shift"),
            ("📈  Sales", "sales"),
            ("🛢️  Purchases", "purchase"),
            ("💰  Collections", "payment"),
            ("📋  Expenses", "expense"),
            ("👷  Employees", "employee"),
            ("📑  Reports", "report"),
            ("⚙️  Backup", "backup"),
        ]

        menu_items.insert(7, ("💳  Credit Ledger", "credit"))

        for display_name, page_id in menu_items:
            btn = QPushButton(f" {display_name}", self)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda checked, pid=page_id: self._on_btn_clicked(pid))
            layout.addWidget(btn)
            self.buttons[page_id] = btn

        # Select Dashboard by default
        if "dashboard" in self.buttons:
            self.buttons["dashboard"].setChecked(True)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # ── Logout Button ──
        self.logout_btn = QPushButton("  🚪  Sign Out", self)
        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                color: #f87171;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #ef444420;
            }}
        """)
        self.logout_btn.clicked.connect(lambda: self._on_btn_clicked("logout"))
        layout.addWidget(self.logout_btn)

    def _on_btn_clicked(self, page_id: str):
        self.page_changed.emit(page_id)

    def set_active_page(self, page_id: str):
        """Programmatically highlight a sidebar button."""
        if page_id in self.buttons:
            self.buttons[page_id].setChecked(True)
