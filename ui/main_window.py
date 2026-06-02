"""
Petrol Pump Finance Manager ERP — Main Window
Coordinates multi-screen layout containing Sidebar navigation and page stack.
Integrates toast notifications across all pages.
Includes header bar with alert notification bell (Phase 3).
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QVBoxLayout,
    QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from ui.theme import (
    MAIN_STYLE, BG_MAIN, BG_SURFACE, BG_SURFACE_LIGHT, TEXT_PRIMARY,
    TEXT_SECONDARY, BORDER_COLOR, ACCENT_PRIMARY
)
from ui.components.sidebar import Sidebar
from ui.components.toast import Toast
from ui.components.alerts_panel import AlertBellButton, AlertsPanel
from ui.api_client import client

# Import pages
from ui.pages.login_page import LoginPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.fuel_page import FuelPage
from ui.pages.nozzle_page import NozzlePage
from ui.pages.shift_page import ShiftPage
from ui.pages.sales_page import SalesPage
from ui.pages.purchase_page import PurchasePage
from ui.pages.payment_page import PaymentPage
from ui.pages.credit_page import CreditPage
from ui.pages.expense_page import ExpensePage
from ui.pages.employee_page import EmployeePage
from ui.pages.report_page import ReportPage
from ui.pages.backup_page import BackupPage
# TankPage removed per user request


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Petrol Pump Finance Manager ERP")
        self.resize(1280, 800)
        self.setStyleSheet(MAIN_STYLE)
        self._init_ui()

    def _init_ui(self):
        # Outer-most Stacked Widget (toggles between Login and Main ERP views)
        self.main_stack = QStackedWidget(self)
        self.setCentralWidget(self.main_stack)

        # ── 1. LOGIN SCREEN ──
        self.login_page = LoginPage(self)
        self.login_page.login_success.connect(self._on_login_success)
        self.main_stack.addWidget(self.login_page)

        # ── 2. MAIN ERP OPERATIONS SCREEN ──
        self.operations_widget = QWidget(self)
        ops_layout = QHBoxLayout(self.operations_widget)
        ops_layout.setContentsMargins(0, 0, 0, 0)
        ops_layout.setSpacing(0)

        # Sidebar Left
        self.sidebar = Sidebar(self.operations_widget)
        self.sidebar.page_changed.connect(self._handle_navigation)
        ops_layout.addWidget(self.sidebar)

        # ── Right Panel (Header Bar + Pages Stack) ──
        right_panel = QWidget(self.operations_widget)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # ── Header Bar ──
        self.header_bar = QWidget(right_panel)
        self.header_bar.setFixedHeight(52)
        self.header_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_SURFACE};
                border-bottom: 1px solid {BORDER_COLOR};
            }}
        """)

        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(20, 0, 16, 0)
        header_layout.setSpacing(12)

        # App title in header
        header_title = QLabel("⛽  Petrol Pump ERP")
        header_title.setStyleSheet(f"""
            font-size: 15px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(header_title)

        # Current page indicator
        self.page_indicator = QLabel("")
        self.page_indicator.setStyleSheet(f"""
            font-size: 12px;
            color: {TEXT_SECONDARY};
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(self.page_indicator)

        header_layout.addStretch()

        # Alert Bell Button
        self.alert_bell = AlertBellButton(self.header_bar)
        self.alert_bell.clicked.connect(self._toggle_alerts_panel)
        header_layout.addWidget(self.alert_bell)

        right_layout.addWidget(self.header_bar)

        # ── Pages Stack ──
        self.pages_stack = QStackedWidget(right_panel)
        right_layout.addWidget(self.pages_stack)

        ops_layout.addWidget(right_panel)

        # Instantiate operation pages
        self.pages = {
            "dashboard": DashboardPage(self),
            "fuel": FuelPage(self),
            "nozzle": NozzlePage(self),
            "shift": ShiftPage(self),
            "sales": SalesPage(self),
            "purchase": PurchasePage(self),
            "payment": PaymentPage(self),
            "credit": CreditPage(self),
            "expense": ExpensePage(self),
            "employee": EmployeePage(self),
            "report": ReportPage(self),
            "backup": BackupPage(self),
        }

        # Page display names for the header indicator
        self._page_names = {
            "dashboard": "📊 Dashboard",
            "fuel": "⛽ Fuel Prices",
            "nozzle": "🔧 Nozzle Map",
            "shift": "📝 Shift Entry",
            "sales": "📈 Sales",
            "purchase": "🛢️ Purchases",
            "payment": "💰 Collections",
            "expense": "📋 Expenses",
            "employee": "👷 Employees",
            "report": "📑 Reports",
            "backup": "⚙️ Backup & Restore",
        }

        self._page_names["credit"] = "Customer Credit"

        # Register operation pages to stack
        for page_id, page_widget in self.pages.items():
            self.pages_stack.addWidget(page_widget)

        # Hook dashboard card navigation triggers
        self.pages["dashboard"].navigate_to_page.connect(self._navigate_from_dashboard)

        self.main_stack.addWidget(self.operations_widget)

        # ── Toast Notification (overlays the operations area) ──
        self.toast = Toast(self.operations_widget)

        # Wire toast to all pages that support it
        for page_id, page_widget in self.pages.items():
            if hasattr(page_widget, "set_toast"):
                page_widget.set_toast(self.toast)

        # ── Alerts Panel (overlay, positioned below header bar) ──
        self.alerts_panel = AlertsPanel(right_panel)
        self.alerts_panel.panel_closed.connect(self._on_alerts_panel_closed)
        self.alerts_panel.alerts_changed.connect(self.alert_bell.set_count)

        # Start with Login screen
        self.main_stack.setCurrentIndex(0)

    def _on_login_success(self, login_data: dict):
        """Transition from Login to operations panel and pre-load default page."""
        self.main_stack.setCurrentIndex(1)
        self._handle_navigation("dashboard")

    def _navigate_from_dashboard(self, page_id: str):
        """Handle internal click navigations from dashboard card metrics."""
        self.sidebar.set_active_page(page_id)
        self._handle_navigation(page_id)

    def _handle_navigation(self, page_id: str):
        """Primary navigation orchestrator."""
        if page_id == "logout":
            self._handle_logout()
            return

        if page_id in self.pages:
            target_widget = self.pages[page_id]
            self.pages_stack.setCurrentWidget(target_widget)
            # Call load_data() hook on the target page if it exists
            if hasattr(target_widget, "load_data"):
                target_widget.load_data()

            # Update header page indicator
            display_name = self._page_names.get(page_id, "")
            self.page_indicator.setText(f"  /  {display_name}")

            # Refresh alert count on dashboard navigation
            if page_id == "dashboard":
                self._refresh_alert_count()

            # Hide alerts panel on navigation
            if self.alerts_panel.isVisible():
                self.alerts_panel.hide()

    def _handle_logout(self):
        reply = QMessageBox.question(
            self, "Confirm Logout", "Are you sure you want to sign out?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            client.clear_token()
            self.login_page.clear_inputs()
            self.main_stack.setCurrentIndex(0)
            self.sidebar.set_active_page("dashboard")

    def _toggle_alerts_panel(self):
        """Toggle the alerts overlay panel."""
        self.alerts_panel.toggle()
        if self.alerts_panel.isVisible():
            # Position the panel below the header, right-aligned
            panel_x = self.header_bar.width() - self.alerts_panel.width() - 12
            panel_y = self.header_bar.height() + 4
            self.alerts_panel.move(panel_x, panel_y)
            self.alerts_panel.raise_()

    def _on_alerts_panel_closed(self):
        """Handle alerts panel close."""
        pass

    def _refresh_alert_count(self):
        """Fetch alert count from API and update the bell badge."""
        try:
            data = client.get("/api/alerts")
            total = data.get("total_count", 0)
            critical = data.get("critical_count", 0)
            self.alert_bell.set_count(total, critical)
        except Exception as e:
            print(f"[Alerts] Error refreshing count: {e}")
            self.alert_bell.set_count(0, 0)
