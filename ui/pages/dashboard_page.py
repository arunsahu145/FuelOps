"""
Petrol Pump Finance Manager ERP — Dashboard Page
Stunning, high-end dashboard grid displaying real-time metrics.
Includes payment shortfall warning banner.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Signal, Qt
from ui.theme import ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_DANGER, TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR, BG_SURFACE
from ui.components.smart_card import SmartCard
from ui.components.date_picker import DatePicker
from ui.api_client import client
from utils.helpers import format_currency, format_litres, get_fuel_color


class DashboardPage(QWidget):
    navigate_to_page = Signal(str)  # Emits target page name on card click

    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
        self._init_ui()

    def set_toast(self, toast):
        self._toast = toast

    def _init_ui(self):
        # Outer main container with dark background
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area for responsive sizing
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(scroll)

        content_widget = QWidget()
        content_widget.setObjectName("PageContainer")
        scroll.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ── Header Section (Title + Date Picker) ──
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        self.title_lbl = QLabel("DASHBOARD OVERVIEW", self)
        self.title_lbl.setObjectName("HeaderLabel")
        self.subtitle_lbl = QLabel("Live aggregations of sales, profit, expenses, and payment collections.", self)
        self.subtitle_lbl.setObjectName("SubHeaderLabel")
        title_vbox.addWidget(self.title_lbl)
        title_vbox.addWidget(self.subtitle_lbl)

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.date_picker = DatePicker(self)
        self.date_picker.date_changed.connect(self.load_data)
        header_layout.addWidget(self.date_picker)
        layout.addLayout(header_layout)

        # ── Payment Shortfall Warning Banner (hidden by default) ──
        self.shortfall_banner = QFrame(self)
        self.shortfall_banner.setVisible(False)
        self.shortfall_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {ACCENT_DANGER}18;
                border: 1.5px solid {ACCENT_DANGER}60;
                border-radius: 8px;
                padding: 10px 16px;
            }}
        """)
        banner_layout = QHBoxLayout(self.shortfall_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(10)

        warning_icon = QLabel("⚠️", self)
        warning_icon.setStyleSheet("font-size: 18px; border: none;")
        banner_layout.addWidget(warning_icon)

        self.shortfall_label = QLabel("", self)
        self.shortfall_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {ACCENT_DANGER}; border: none;")
        self.shortfall_label.setWordWrap(True)
        banner_layout.addWidget(self.shortfall_label)
        banner_layout.addStretch()

        layout.addWidget(self.shortfall_banner)

        # ── 5 Smart Cards Grid Section ──
        grid = QGridLayout()
        grid.setSpacing(15)

        # Card 1: Today's Sales
        self.sales_card = SmartCard("Today's Sales", "₹0.00", "0.00 L sold today", ACCENT_PRIMARY, self)
        self.sales_card.clicked.connect(lambda: self.navigate_to_page.emit("sales"))
        grid.addWidget(self.sales_card, 0, 0)

        # Card 2: Estimated Profit
        self.profit_card = SmartCard("Estimated Profit", "₹0.00", "Net margins from sales", ACCENT_SUCCESS, self)
        self.profit_card.clicked.connect(lambda: self.navigate_to_page.emit("sales"))
        grid.addWidget(self.profit_card, 0, 1)

        # Card 3: Today's Expenses
        self.expense_card = SmartCard("Today's Expenses", "₹0.00", "Operational expense bills", ACCENT_DANGER, self)
        self.expense_card.clicked.connect(lambda: self.navigate_to_page.emit("expense"))
        grid.addWidget(self.expense_card, 0, 2)

        # Card 4: Payments Collection
        self.payment_card = SmartCard("Collections Today", "₹0.00", "Cash/UPI method collections", ACCENT_WARNING, self)
        self.payment_card.clicked.connect(lambda: self.navigate_to_page.emit("payment"))
        grid.addWidget(self.payment_card, 1, 0)

        # Card 5: Today's Purchases (replaced Tank Stock)
        self.purchase_card = SmartCard("Today's Purchases", "₹0.00", "Fuel acquisition cost", "#a855f7", self)
        self.purchase_card.clicked.connect(lambda: self.navigate_to_page.emit("purchase"))
        grid.addWidget(self.purchase_card, 1, 1)

        self.credit_today_card = SmartCard("Credit Given Today", "₹0.00", "Customer credit entries", "#f97316", self)
        self.credit_today_card.clicked.connect(lambda: self.navigate_to_page.emit("credit"))
        grid.addWidget(self.credit_today_card, 1, 2)

        self.credit_outstanding_card = SmartCard("Credit Outstanding", "₹0.00", "Open customer balances", "#ef4444", self)
        self.credit_outstanding_card.clicked.connect(lambda: self.navigate_to_page.emit("credit"))
        grid.addWidget(self.credit_outstanding_card, 2, 0)

        self.credit_repay_card = SmartCard("Credit Repayments", "₹0.00", "Repayments received today", "#14b8a6", self)
        self.credit_repay_card.clicked.connect(lambda: self.navigate_to_page.emit("credit"))
        grid.addWidget(self.credit_repay_card, 2, 1)

        self.overdue_card = SmartCard("Overdue Customers", "0", "Late credit accounts", "#f59e0b", self)
        self.overdue_card.clicked.connect(lambda: self.navigate_to_page.emit("credit"))
        grid.addWidget(self.overdue_card, 2, 2)

        # Grid spacing/stretching
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)

        # ── Lower Breakdown Section ──
        breakdown_layout = QHBoxLayout()
        breakdown_layout.setSpacing(15)

        # Fuel Wise Split Card
        self.fuel_split_frame = QFrame(self)
        self.fuel_split_frame.setObjectName("SmartCard")
        fs_layout = QVBoxLayout(self.fuel_split_frame)
        fs_layout.setContentsMargins(15, 15, 15, 15)
        self.fs_title = QLabel("SALES BY FUEL TYPE", self)
        self.fs_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {TEXT_SECONDARY};")
        fs_layout.addWidget(self.fs_title)
        self.fs_content = QLabel("No sales recorded for this date.", self)
        self.fs_content.setStyleSheet("font-size: 13px; color: #ffffff;")
        self.fs_content.setWordWrap(True)
        fs_layout.addWidget(self.fs_content)
        fs_layout.addStretch()
        breakdown_layout.addWidget(self.fuel_split_frame)

        # Payments Method Split Card
        self.pay_split_frame = QFrame(self)
        self.pay_split_frame.setObjectName("SmartCard")
        ps_layout = QVBoxLayout(self.pay_split_frame)
        ps_layout.setContentsMargins(15, 15, 15, 15)
        self.ps_title = QLabel("PAYMENT MODE SPLIT", self)
        self.ps_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {TEXT_SECONDARY};")
        ps_layout.addWidget(self.ps_title)
        self.ps_content = QLabel("No payments collected for this date.", self)
        self.ps_content.setStyleSheet("font-size: 13px; color: #ffffff;")
        self.ps_content.setWordWrap(True)
        ps_layout.addWidget(self.ps_content)
        ps_layout.addStretch()
        breakdown_layout.addWidget(self.pay_split_frame)

        layout.addLayout(breakdown_layout)
        layout.addStretch()

    def load_data(self, *args):
        """Fetch real-time stats from FastAPI. Accepts optional args for signal compatibility."""
        try:
            date_str = self.date_picker.get_date_str()
            data = client.get("/api/dashboard/summary", params={"dashboard_date": date_str})

            # Update Sales
            total_sales = data.get("today_total_sales", 0.0)
            self.sales_card.update_data(
                format_currency(total_sales),
                f"{format_litres(data.get('today_litres_sold', 0.0))} sold today"
            )

            # Update Profit
            self.profit_card.update_data(
                format_currency(data.get("today_estimated_profit", 0.0)),
                "Net margins from sales"
            )

            # Update Expenses
            self.expense_card.update_data(
                format_currency(data.get("today_total_expenses", 0.0)),
                "Operational bills & payouts"
            )

            # Update Payments
            total_payments = data.get("today_total_payments", 0.0)
            self.payment_card.update_data(
                format_currency(total_payments),
                "UPI and Cash entries"
            )

            # Update Purchases Card
            self.purchase_card.update_data(
                format_currency(data.get("today_total_purchases", 0.0)),
                f"{format_litres(data.get('today_litres_purchased', 0.0))} purchased"
            )

            self.credit_today_card.update_data(
                format_currency(data.get("total_credits_given_today", 0.0)),
                "Customer credit entries"
            )
            self.credit_outstanding_card.update_data(
                format_currency(data.get("total_credits_outstanding", 0.0)),
                "Open customer balances"
            )
            self.credit_repay_card.update_data(
                format_currency(data.get("total_repayment_amount_done", 0.0)),
                "Received today"
            )
            self.overdue_card.update_data(
                str(data.get("overdue_customers", 0)),
                "Late credit accounts"
            )

            # Update Fuel Split
            fuels = data.get("today_sales_by_fuel", [])
            if fuels:
                fuel_text = ""
                for f in fuels:
                    fuel_text += f"• {f['fuel_type']}: {format_currency(f['amount'])}\n"
                self.fs_content.setText(fuel_text.strip())
            else:
                self.fs_content.setText("No sales recorded for this date.")

            # Update Payments Mode Split
            pmethods = data.get("today_payments_by_method", [])
            if pmethods:
                pm_text = ""
                for p in pmethods:
                    pm_text += f"• {p['method']}: {format_currency(p['amount'])}\n"
                self.ps_content.setText(pm_text.strip())
            else:
                self.ps_content.setText("No payments collected for this date.")

            # ── Payment Shortfall Warning ──
            shortfall = data.get("payment_shortfall", 0.0)
            expected_cash = data.get("expected_cash_collection", 0.0)
            cash_collection = data.get("cash_collection", 0.0)
            if total_sales > 0 and shortfall < 0:
                deficit = abs(shortfall)
                self.shortfall_label.setText(
                    f"Cash shortfall detected! Cash collection ({format_currency(cash_collection)}) "
                    f"is {format_currency(deficit)} less than expected cash "
                    f"({format_currency(expected_cash)}). Please verify all payment entries."
                )
                self.shortfall_banner.setVisible(True)
            else:
                self.shortfall_banner.setVisible(False)

        except Exception as e:
            # Silent fallback / placeholder in case server is starting up
            print(f"Error loading dashboard: {e}")
