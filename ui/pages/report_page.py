"""
Petrol Pump Finance Manager ERP — Reports & Closings Page (v2)
Fixed: COLLECTIONS card, breakdown tables, monthly expense visibility,
load-from-employees auto-salary, and improved daily/monthly detail views.
"""
import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit,
    QPushButton, QMessageBox, QScrollArea, QComboBox, QSizePolicy,
    QGridLayout, QFileDialog, QTabWidget
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_SUCCESS,
    ACCENT_WARNING, ACCENT_DANGER, BG_MAIN, BG_SURFACE,
    BG_SURFACE_LIGHT, BORDER_COLOR
)
from ui.components.date_picker import DatePicker
from ui.components.data_table import DataTable
from ui.components.currency_input import IndianCurrencyLineEdit
from ui.api_client import client
from utils.helpers import format_currency, format_litres, get_month_name
from utils.pdf_generator import generate_daily_pdf, generate_monthly_pdf


# ═══════════════════════════════════════════════════════════════════════════════
# METRIC CARD — compact stat display for the report preview board
# ═══════════════════════════════════════════════════════════════════════════════

class ReportMetricCard(QFrame):
    """Small metric display card for report summary."""

    def __init__(self, label: str, value: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ReportMetric")
        self.setStyleSheet(f"""
            QFrame#ReportMetric {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-top: 3px solid {accent};
                border-radius: 8px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self.label_lbl = QLabel(label, self)
        self.label_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {TEXT_SECONDARY}; "
            f"letter-spacing: 0.5px;"
        )
        layout.addWidget(self.label_lbl)

        self.value_lbl = QLabel(value, self)
        self.value_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY}; "
            f"font-family: 'Consolas', monospace;"
        )
        layout.addWidget(self.value_lbl)

        layout.addStretch()

    def update_value(self, value: str):
        self.value_lbl.setText(value)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN REPORT PAGE
# ═══════════════════════════════════════════════════════════════════════════════

class ReportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
        self._daily_data = None
        self._monthly_data = None
        self._init_ui()

    def set_toast(self, toast):
        self._toast = toast

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(scroll)

        content = QWidget()
        content.setObjectName("PageContainer")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Header ──
        header = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_lbl = QLabel("REPORTS & CLOSINGS", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel(
            "Review daily/monthly financials, close periods, manage salaries & expenses, and export PDFs.",
            self
        )
        sub_lbl.setObjectName("SubHeaderLabel")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header.addLayout(title_vbox)
        header.addStretch()
        layout.addLayout(header)

        # ── Report Type Selector ──
        selector_frame = QFrame(self)
        selector_frame.setObjectName("SmartCard")
        selector_layout = QHBoxLayout(selector_frame)
        selector_layout.setContentsMargins(16, 12, 16, 12)
        selector_layout.setSpacing(16)

        type_lbl = QLabel("REPORT TYPE:", self)
        type_lbl.setStyleSheet(
            f"font-weight: bold; color: {TEXT_SECONDARY}; font-size: 12px;"
        )
        selector_layout.addWidget(type_lbl)

        self.report_type_combo = QComboBox(self)
        self.report_type_combo.addItems(["Daily Closing", "Monthly Summary"])
        self.report_type_combo.setMinimumWidth(180)
        self.report_type_combo.currentIndexChanged.connect(self._on_type_changed)
        selector_layout.addWidget(self.report_type_combo)

        # Daily: Date picker
        self.daily_date_picker = DatePicker(self)
        self.daily_date_picker.date_changed.connect(self._load_daily)
        selector_layout.addWidget(self.daily_date_picker)

        # Monthly: Month/Year selectors
        self.month_combo = QComboBox(self)
        for m in range(1, 13):
            self.month_combo.addItem(get_month_name(m), m)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_combo.setMinimumWidth(120)
        self.month_combo.currentIndexChanged.connect(self._load_monthly)
        selector_layout.addWidget(self.month_combo)

        self.year_combo = QComboBox(self)
        current_year = QDate.currentDate().year()
        for y in range(current_year - 2, current_year + 2):
            self.year_combo.addItem(str(y), y)
        self.year_combo.setCurrentIndex(2)  # current year
        self.year_combo.setMinimumWidth(80)
        self.year_combo.currentIndexChanged.connect(self._load_monthly)
        selector_layout.addWidget(self.year_combo)

        selector_layout.addStretch()

        # Load button
        self.load_btn = QPushButton("  🔄 Load Report  ", self)
        self.load_btn.setObjectName("ActionButton")
        self.load_btn.clicked.connect(self._load_current_report)
        selector_layout.addWidget(self.load_btn)

        layout.addWidget(selector_frame)

        # ── Metric Cards Grid ──
        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(12)

        self.m_sales = ReportMetricCard("TOTAL SALES", "₹0.00", ACCENT_PRIMARY, self)
        self.m_profit = ReportMetricCard("NET PROFIT", "₹0.00", ACCENT_SUCCESS, self)
        self.m_expenses = ReportMetricCard("TOTAL EXPENSES", "₹0.00", ACCENT_DANGER, self)
        self.m_payments = ReportMetricCard("COLLECTIONS", "₹0.00", ACCENT_WARNING, self)
        self.m_purchases = ReportMetricCard("PURCHASE COST", "₹0.00", "#a855f7", self)
        self.m_shortfall = ReportMetricCard("SHORTFALL", "₹0.00", ACCENT_DANGER, self)
        self.m_salaries = ReportMetricCard("SALARY GIVEN", "0.00", "#ec4899", self)
        self.m_credit_outstanding = ReportMetricCard("CREDIT OUTSTANDING", "₹0.00", "#f97316", self)
        self.m_credit_received = ReportMetricCard("CREDIT RECEIVED", "₹0.00", "#14b8a6", self)

        self.metrics_grid.addWidget(self.m_sales, 0, 0)
        self.metrics_grid.addWidget(self.m_profit, 0, 1)
        self.metrics_grid.addWidget(self.m_expenses, 0, 2)
        self.metrics_grid.addWidget(self.m_payments, 0, 3)
        self.metrics_grid.addWidget(self.m_purchases, 1, 0)
        self.metrics_grid.addWidget(self.m_shortfall, 1, 1)
        self.metrics_grid.addWidget(self.m_salaries, 1, 2)
        self.metrics_grid.addWidget(self.m_credit_outstanding, 1, 3)
        self.metrics_grid.addWidget(self.m_credit_received, 2, 0)
        self.m_salaries.setVisible(True)

        layout.addLayout(self.metrics_grid)

        # ── Status Banner ──
        self.status_banner = QFrame(self)
        self.status_banner.setVisible(False)
        self.status_banner.setFixedHeight(44)
        banner_layout = QHBoxLayout(self.status_banner)
        banner_layout.setContentsMargins(14, 6, 14, 6)
        self.status_icon = QLabel("", self)
        self.status_icon.setStyleSheet("font-size: 16px; border: none;")
        banner_layout.addWidget(self.status_icon)
        self.status_text = QLabel("", self)
        self.status_text.setStyleSheet("font-size: 13px; font-weight: 600; border: none;")
        banner_layout.addWidget(self.status_text)
        banner_layout.addStretch()
        layout.addWidget(self.status_banner)

        # ── BREAKDOWN DETAILS — Tabbed Layout ──
        self.detail_frame = QFrame(self)
        self.detail_frame.setObjectName("SmartCard")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

        self.detail_title = QLabel("BREAKDOWN DETAILS", self)
        self.detail_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; "
            f"letter-spacing: 0.5px;"
        )
        detail_layout.addWidget(self.detail_title)

        self.detail_tabs = QTabWidget(self)
        self.detail_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                background: {BG_SURFACE};
            }}
            QTabBar::tab {{
                background: {BG_MAIN};
                color: {TEXT_SECONDARY};
                padding: 8px 16px;
                border: 1px solid {BORDER_COLOR};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                border-bottom: 2px solid {ACCENT_PRIMARY};
            }}
        """)

        # Fuel Breakdown Tab
        fuel_tab = QWidget()
        fuel_tab_layout = QVBoxLayout(fuel_tab)
        fuel_tab_layout.setContentsMargins(8, 8, 8, 8)
        self.fuel_table = DataTable(
            ["Fuel Type", "Litres Sold", "Sales Amount", "Cost/L (or Cost)", "Profit"],
            self
        )
        self.fuel_table.setMinimumHeight(420)
        fuel_tab_layout.addWidget(self.fuel_table)
        self.detail_tabs.addTab(fuel_tab, "⛽ Fuel Breakdown")

        # Payment Breakdown Tab
        payment_tab = QWidget()
        payment_tab_layout = QVBoxLayout(payment_tab)
        payment_tab_layout.setContentsMargins(8, 8, 8, 8)
        self.payment_table = DataTable(
            ["Payment Method", "Amount Collected"],
            self
        )
        self.payment_table.setMinimumHeight(420)
        payment_tab_layout.addWidget(self.payment_table)
        self.detail_tabs.addTab(payment_tab, "💰 Collections Breakdown")

        # Expense Breakdown Tab
        expense_tab = QWidget()
        expense_tab_layout = QVBoxLayout(expense_tab)
        expense_tab_layout.setContentsMargins(8, 8, 8, 8)
        self.expense_table = DataTable(
            ["Category", "Amount"],
            self
        )
        self.expense_table.setMinimumHeight(420)
        expense_tab_layout.addWidget(self.expense_table)
        self.detail_tabs.addTab(expense_tab, "📋 Expense Breakdown")

        # Set minimum height for the entire tab widget so tables display
        self.detail_tabs.setMinimumHeight(500)
        detail_layout.addWidget(self.detail_tabs)
        layout.addWidget(self.detail_frame)

        # ── Monthly Extras: Salary & Monthly Expense Management ──
        self.monthly_mgmt_frame = QFrame(self)
        self.monthly_mgmt_frame.setObjectName("SmartCard")
        self.monthly_mgmt_frame.setVisible(False)
        mgmt_layout = QVBoxLayout(self.monthly_mgmt_frame)
        mgmt_layout.setContentsMargins(16, 16, 16, 16)
        mgmt_layout.setSpacing(12)

        mgmt_tabs = QTabWidget(self)
        mgmt_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                background: {BG_SURFACE};
            }}
            QTabBar::tab {{
                background: {BG_MAIN};
                color: {TEXT_SECONDARY};
                padding: 8px 16px;
                border: 1px solid {BORDER_COLOR};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                border-bottom: 2px solid {ACCENT_PRIMARY};
            }}
        """)

        # ── Salaries Tab ──
        salary_widget = QWidget()
        sal_layout = QVBoxLayout(salary_widget)
        sal_layout.setContentsMargins(14, 14, 14, 14)
        sal_layout.setSpacing(12)

        # Header row with Load From Employees button and total
        sal_header = QHBoxLayout()
        sal_header.setSpacing(12)

        sal_section_title = QLabel("SALARY PAYMENTS", self)
        sal_section_title.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {TEXT_SECONDARY}; "
            f"letter-spacing: 0.5px;"
        )
        sal_header.addWidget(sal_section_title)
        sal_header.addStretch()

        self.sal_total_label = QLabel("Total: ₹0.00", self)
        self.sal_total_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: #ec4899; "
            f"font-family: 'Consolas', monospace;"
        )
        sal_header.addWidget(self.sal_total_label)

        self.load_emp_btn = QPushButton("  📥 Load From Employees  ", self)
        self.load_emp_btn.setObjectName("ActionButton")
        self.load_emp_btn.setToolTip(
            "Auto-populate salaries from the Employee master register"
        )
        self.load_emp_btn.clicked.connect(self._load_from_employees)
        self.load_emp_btn.setVisible(False)
        sal_header.addWidget(self.load_emp_btn)

        sal_layout.addLayout(sal_header)

        # Manual add form
        sal_form = QHBoxLayout()
        sal_form.setSpacing(10)

        self.emp_name_input = QLineEdit(self)
        self.emp_name_input.setPlaceholderText("Employee Name")
        self.emp_name_input.setMinimumWidth(160)
        sal_form.addWidget(self.emp_name_input)

        self.emp_desg_input = QLineEdit(self)
        self.emp_desg_input.setPlaceholderText("Designation")
        self.emp_desg_input.setMinimumWidth(140)
        sal_form.addWidget(self.emp_desg_input)

        self.emp_salary_input = IndianCurrencyLineEdit(self, placeholder="₹ Salary")
        self.emp_salary_input.setMinimumWidth(140)
        sal_form.addWidget(self.emp_salary_input)

        add_sal_btn = QPushButton("  + Add Salary  ", self)
        add_sal_btn.setObjectName("SuccessButton")
        add_sal_btn.setMinimumHeight(34)
        add_sal_btn.clicked.connect(self._add_salary)
        sal_form.addWidget(add_sal_btn)
        self.emp_name_input.setVisible(False)
        self.emp_desg_input.setVisible(False)
        self.emp_salary_input.setVisible(False)
        add_sal_btn.setVisible(False)
        sal_form.addStretch()
        sal_layout.addLayout(sal_form)

        self.salary_table = DataTable(
            ["Employee", "Amount", "Date"],
            self
        )
        self.salary_table.setMinimumHeight(250)
        sal_layout.addWidget(self.salary_table)

        mgmt_tabs.addTab(salary_widget, "👷 Employee Salaries")

        # ── Monthly Expenses Tab ──
        mexp_widget = QWidget()
        mexp_layout = QVBoxLayout(mexp_widget)
        mexp_layout.setContentsMargins(14, 14, 14, 14)
        mexp_layout.setSpacing(12)

        # Header with total
        mexp_header = QHBoxLayout()
        mexp_header.setSpacing(12)

        mexp_section_title = QLabel("MONTHLY RECURRING EXPENSES", self)
        mexp_section_title.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {TEXT_SECONDARY}; "
            f"letter-spacing: 0.5px;"
        )
        mexp_header.addWidget(mexp_section_title)
        mexp_header.addStretch()

        self.mexp_total_label = QLabel("Total: ₹0.00", self)
        self.mexp_total_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {ACCENT_DANGER}; "
            f"font-family: 'Consolas', monospace;"
        )
        mexp_header.addWidget(self.mexp_total_label)

        mexp_layout.addLayout(mexp_header)

        # Add expense form
        mexp_form = QHBoxLayout()
        mexp_form.setSpacing(10)

        self.mexp_category_input = QComboBox(self)
        self.mexp_category_input.addItems([
            "Rent", "Electricity Bill", "Water Bill",
            "Insurance", "License Fee", "Maintenance",
            "Internet/Phone", "Stationery", "Other"
        ])
        self.mexp_category_input.setMinimumWidth(160)
        mexp_form.addWidget(self.mexp_category_input)

        self.mexp_amount_input = IndianCurrencyLineEdit(self, placeholder="₹ Amount")
        self.mexp_amount_input.setMinimumWidth(140)
        mexp_form.addWidget(self.mexp_amount_input)

        self.mexp_desc_input = QLineEdit(self)
        self.mexp_desc_input.setPlaceholderText("Description (optional)")
        self.mexp_desc_input.setMinimumWidth(180)
        mexp_form.addWidget(self.mexp_desc_input)

        add_mexp_btn = QPushButton("  + Add Expense  ", self)
        add_mexp_btn.setObjectName("SuccessButton")
        add_mexp_btn.setMinimumHeight(34)
        add_mexp_btn.clicked.connect(self._add_monthly_expense)
        mexp_form.addWidget(add_mexp_btn)

        mexp_form.addStretch()
        mexp_layout.addLayout(mexp_form)

        self.mexp_table = DataTable(
            ["Category", "Amount", "Description"],
            self, enable_delete=True
        )
        self.mexp_table.setMinimumHeight(250)
        self.mexp_table.row_delete_requested.connect(self._delete_monthly_expense)
        mexp_layout.addWidget(self.mexp_table)

        mgmt_tabs.addTab(mexp_widget, "🏢 Monthly Expenses")

        # ── Bank Deposits Tab ──
        bd_widget = QWidget()
        bd_layout = QVBoxLayout(bd_widget)
        bd_layout.setContentsMargins(14, 14, 14, 14)
        bd_layout.setSpacing(12)

        # Header with total
        bd_header = QHBoxLayout()
        bd_header.setSpacing(12)

        bd_section_title = QLabel("BANK DEPOSITS", self)
        bd_section_title.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {TEXT_SECONDARY}; "
            f"letter-spacing: 0.5px;"
        )
        bd_header.addWidget(bd_section_title)
        bd_header.addStretch()

        self.bd_total_label = QLabel("Total Deposited: ₹0.00", self)
        self.bd_total_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {ACCENT_PRIMARY}; "
            f"font-family: 'Consolas', monospace;"
        )
        bd_header.addWidget(self.bd_total_label)

        bd_layout.addLayout(bd_header)

        # Deposit form — 4 fields in a row
        bd_form = QHBoxLayout()
        bd_form.setSpacing(10)

        wc_vbox = QVBoxLayout()
        wc_lbl = QLabel("WORKING CAPITAL", self)
        wc_lbl.setObjectName("FormLabel")
        wc_vbox.addWidget(wc_lbl)
        self.bd_wc_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.bd_wc_input.setMinimumWidth(130)
        wc_vbox.addWidget(self.bd_wc_input)
        bd_form.addLayout(wc_vbox)

        solar_vbox = QVBoxLayout()
        solar_lbl = QLabel("SOLAR", self)
        solar_lbl.setObjectName("FormLabel")
        solar_vbox.addWidget(solar_lbl)
        self.bd_solar_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.bd_solar_input.setMinimumWidth(130)
        solar_vbox.addWidget(self.bd_solar_input)
        bd_form.addLayout(solar_vbox)

        truck_vbox = QVBoxLayout()
        truck_lbl = QLabel("TRUCK", self)
        truck_lbl.setObjectName("FormLabel")
        truck_vbox.addWidget(truck_lbl)
        self.bd_truck_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.bd_truck_input.setMinimumWidth(130)
        truck_vbox.addWidget(self.bd_truck_input)
        bd_form.addLayout(truck_vbox)

        topup_vbox = QVBoxLayout()
        topup_lbl = QLabel("TOP UP FINANCE", self)
        topup_lbl.setObjectName("FormLabel")
        topup_vbox.addWidget(topup_lbl)
        self.bd_topup_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.bd_topup_input.setMinimumWidth(130)
        topup_vbox.addWidget(self.bd_topup_input)
        bd_form.addLayout(topup_vbox)

        # Button row for Save / Update / Cancel
        bd_btn_vbox = QVBoxLayout()
        bd_btn_vbox.addStretch()

        self.bd_save_btn = QPushButton("  + Save Deposit  ", self)
        self.bd_save_btn.setObjectName("SuccessButton")
        self.bd_save_btn.setMinimumHeight(34)
        self.bd_save_btn.clicked.connect(self._save_bank_deposit)
        bd_btn_vbox.addWidget(self.bd_save_btn)

        self.bd_cancel_btn = QPushButton("  ✕ Cancel  ", self)
        self.bd_cancel_btn.setMinimumHeight(30)
        self.bd_cancel_btn.setStyleSheet(f"""
            QPushButton {{
                color: {ACCENT_DANGER};
                font-weight: 600;
                font-size: 11px;
                border: 1px solid {ACCENT_DANGER}40;
                border-radius: 4px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_DANGER}15;
            }}
        """)
        self.bd_cancel_btn.clicked.connect(self._cancel_bd_edit)
        self.bd_cancel_btn.setVisible(False)
        bd_btn_vbox.addWidget(self.bd_cancel_btn)

        bd_form.addLayout(bd_btn_vbox)
        self._bd_edit_id = None  # Track which entry is being edited

        bd_form.addStretch()
        bd_layout.addLayout(bd_form)

        # Breakdown summary card
        self.bd_breakdown_frame = QFrame(self)
        self.bd_breakdown_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_MAIN};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
        """)
        bdb_layout = QHBoxLayout(self.bd_breakdown_frame)
        bdb_layout.setContentsMargins(16, 10, 16, 10)
        bdb_layout.setSpacing(24)

        self.bd_wc_summary = QLabel("Working Capital: ₹0.00", self)
        self.bd_wc_summary.setStyleSheet(f"font-size: 12px; color: {TEXT_PRIMARY}; font-weight: 600;")
        bdb_layout.addWidget(self.bd_wc_summary)

        self.bd_solar_summary = QLabel("Solar: ₹0.00", self)
        self.bd_solar_summary.setStyleSheet(f"font-size: 12px; color: {TEXT_PRIMARY}; font-weight: 600;")
        bdb_layout.addWidget(self.bd_solar_summary)

        self.bd_truck_summary = QLabel("Truck: ₹0.00", self)
        self.bd_truck_summary.setStyleSheet(f"font-size: 12px; color: {TEXT_PRIMARY}; font-weight: 600;")
        bdb_layout.addWidget(self.bd_truck_summary)

        self.bd_topup_summary = QLabel("Top Up: ₹0.00", self)
        self.bd_topup_summary.setStyleSheet(f"font-size: 12px; color: {TEXT_PRIMARY}; font-weight: 600;")
        bdb_layout.addWidget(self.bd_topup_summary)

        bdb_layout.addStretch()
        bd_layout.addWidget(self.bd_breakdown_frame)

        # Deposit history table (click a row to edit)
        self.bd_table = DataTable(
            ["Working Capital", "Solar", "Truck", "Top Up Finance", "Total", "Date"],
            self, enable_delete=True
        )
        self.bd_table.setMinimumHeight(250)
        self.bd_table.row_delete_requested.connect(self._delete_bank_deposit)
        self.bd_table.cellClicked.connect(self._on_bd_row_clicked)
        bd_layout.addWidget(self.bd_table)

        bd_hint = QLabel("💡 Click a row to edit its values", self)
        bd_hint.setStyleSheet(f"font-size: 10px; color: {TEXT_SECONDARY}; font-style: italic;")
        bd_layout.addWidget(bd_hint)

        mgmt_tabs.addTab(bd_widget, "🏦 Bank Deposits")

        # Set minimum height for the management tabs to look spacious
        mgmt_tabs.setMinimumHeight(500)
        mgmt_layout.addWidget(mgmt_tabs)
        layout.addWidget(self.monthly_mgmt_frame)

        # ── Action Buttons ──
        actions_frame = QFrame(self)
        actions_frame.setObjectName("SmartCard")
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(16, 12, 16, 12)
        actions_layout.setSpacing(12)

        self.close_btn = QPushButton("  🔒 Close Period  ", self)
        self.close_btn.setObjectName("ActionButton")
        self.close_btn.setMinimumWidth(160)
        self.close_btn.clicked.connect(self._close_period)
        actions_layout.addWidget(self.close_btn)

        self.export_btn = QPushButton("  📄 Export PDF  ", self)
        self.export_btn.setObjectName("SuccessButton")
        self.export_btn.setMinimumWidth(160)
        self.export_btn.clicked.connect(self._export_pdf)
        actions_layout.addWidget(self.export_btn)

        actions_layout.addStretch()
        layout.addWidget(actions_frame)

        layout.addStretch()

        # Show daily by default
        self._on_type_changed(0)

    # ── Navigation Callbacks ──

    def load_data(self):
        """Called when page is navigated to."""
        self._load_current_report()

    def _on_type_changed(self, index):
        """Toggle between Daily and Monthly modes."""
        is_daily = index == 0
        self.daily_date_picker.setVisible(is_daily)
        self.month_combo.setVisible(not is_daily)
        self.year_combo.setVisible(not is_daily)
        self.monthly_mgmt_frame.setVisible(not is_daily)

        if is_daily:
            self.close_btn.setText("  🔒 Close Day  ")
            self.m_shortfall.setVisible(True)
            self.m_salaries.setVisible(True)
        else:
            self.close_btn.setText("  🔒 Close Month  ")
            self.m_shortfall.setVisible(True)
            self.m_salaries.setVisible(True)

        self._load_current_report()

    def _load_current_report(self):
        if self.report_type_combo.currentIndex() == 0:
            self._load_daily()
        else:
            self._load_monthly()

    # ── Daily Report ──

    def _load_daily(self):
        try:
            date_str = self.daily_date_picker.get_date_str()
            data = client.get("/api/report/daily/summary", params={
                "report_date": date_str
            })
            self._daily_data = data

            # Update metrics
            self.m_sales.update_value(format_currency(data.get("total_sales", 0)))
            self.m_profit.update_value(format_currency(data.get("net_profit", 0)))
            total_salary = data.get("total_salaries", 0)
            self.m_expenses.update_value(
                format_currency(data.get("total_expenses", 0) + total_salary)
            )
            self.m_salaries.update_value(format_currency(total_salary))
            self.m_payments.update_value(format_currency(data.get("total_payments", 0)))
            self.m_credit_outstanding.update_value(format_currency(data.get("credit_outstanding", 0)))
            self.m_credit_received.update_value(format_currency(data.get("credit_received", 0)))

            # Purchase cost = sum of fuel breakdown purchase costs
            total_purchase = sum(
                fb.get("litres_sold", 0) * fb.get("purchase_cost_per_litre", 0)
                for fb in data.get("fuel_breakdown", [])
            )
            self.m_purchases.label_lbl.setText("PURCHASE COST")
            self.m_purchases.update_value(format_currency(total_purchase))

            shortfall = data.get("payment_shortfall", 0)
            if shortfall < 0:
                self.m_shortfall.update_value(f"-{format_currency(abs(shortfall))}")
                self.m_shortfall.label_lbl.setText("⚠ SHORTFALL")
            else:
                self.m_shortfall.update_value(format_currency(shortfall))
                self.m_shortfall.label_lbl.setText("SURPLUS")

            self.m_shortfall.label_lbl.setText("CASH SURPLUS" if shortfall >= 0 else "CASH SHORTFALL")

            # Status banner
            if data.get("is_closed"):
                self._show_status("✅", "This day has been CLOSED and finalized.",
                                  ACCENT_SUCCESS)
                self.close_btn.setEnabled(False)
            else:
                self._show_status("📋", "This day is OPEN — review and close when ready.",
                                  ACCENT_WARNING)
                self.close_btn.setEnabled(True)

            # Fuel table
            fuel_rows = []
            total_fuel_profit = 0.0
            for fb in data.get("fuel_breakdown", []):
                profit = fb.get("profit", 0)
                total_fuel_profit += profit
                fuel_rows.append((
                    fb.get("fuel_type", ""),
                    format_litres(fb.get("litres_sold", 0)),
                    format_currency(fb.get("sales_amount", 0)),
                    f"{format_currency(fb.get('purchase_cost_per_litre', 0))}/L",
                    format_currency(profit),
                ))

            # Add mathematical transition rows for clarity
            fuel_rows.append(("—" * 20, "—" * 15, "—" * 15, "—" * 15, "—" * 15))

            # Total Fuel Gross Profit
            fuel_rows.append((
                "Total Fuel Gross Profit", "", "", "",
                format_currency(total_fuel_profit)
            ))

            # Less: Expenses
            total_exp = data.get("total_expenses", 0)
            if total_exp > 0:
                fuel_rows.append((
                    "Less: Expenses", "", "", "",
                    f"- {format_currency(total_exp)}"
                ))
            if total_salary > 0:
                fuel_rows.append((
                    "Less: Salary Given", "", "", "",
                    f"- {format_currency(total_salary)}"
                ))

            fuel_rows.append(("—" * 20, "—" * 15, "—" * 15, "—" * 15, "—" * 15))

            # Net Profit
            net_profit = data.get("net_profit", 0)
            fuel_rows.append((
                "Net Profit", "", "", "",
                format_currency(net_profit)
            ))

            self.fuel_table.populate(fuel_rows)

            # Payment table
            pay_rows = []
            for pb in data.get("payment_breakdown", []):
                pay_rows.append((
                    pb.get("method", ""),
                    format_currency(pb.get("amount", 0)),
                ))
            pay_rows.extend([
                ("Expected Cash Collection", format_currency(data.get("expected_cash_collection", 0))),
                ("Actual Cash Collection", format_currency(data.get("cash_collection", 0))),
                ("Cash Surplus / Shortfall", format_currency(data.get("payment_shortfall", 0))),
            ])
            self.payment_table.populate(pay_rows)

            # Expense table
            exp_rows = []
            for eb in data.get("expense_breakdown", []):
                exp_rows.append((
                    eb.get("category", ""),
                    format_currency(eb.get("amount", 0)),
                ))
            for sp in data.get("salary_breakdown", []):
                exp_rows.append((
                    f"Salary - {sp.get('employee_name', '')} ({sp.get('paid_date', '-')})",
                    format_currency(sp.get("amount", 0)),
                ))
            self.expense_table.populate(exp_rows)

        except Exception as e:
            print(f"Error loading daily report: {e}")

    # ── Monthly Report ──

    def _load_monthly(self):
        try:
            month = self.month_combo.currentData()
            year = self.year_combo.currentData()
            if not month or not year:
                return

            data = client.get("/api/report/monthly/summary", params={
                "year": year, "month": month
            })
            self._monthly_data = data

            # Update metrics — FIXED: COLLECTIONS shows actual payment collections
            self.m_sales.update_value(format_currency(data.get("total_sales", 0)))
            self.m_profit.update_value(format_currency(data.get("net_profit", 0)))

            total_exp = (data.get("total_daily_expenses", 0) +
                         data.get("total_monthly_expenses", 0) +
                         data.get("total_salaries", 0))
            self.m_expenses.update_value(format_currency(total_exp))

            # Show actual payment collections
            self.m_payments.update_value(
                format_currency(data.get("total_payments", 0))
            )
            self.m_credit_outstanding.update_value(format_currency(data.get("credit_outstanding", 0)))
            self.m_credit_received.update_value(format_currency(data.get("credit_received", 0)))

            # SALARIES card
            self.m_salaries.update_value(
                format_currency(data.get("total_salaries", 0))
            )
            self.m_purchases.label_lbl.setText("ACTUAL PURCHASES")
            self.m_purchases.update_value(
                format_currency(data.get("total_actual_purchases", 0))
            )
            shortfall = data.get("payment_shortfall", 0)
            self.m_shortfall.label_lbl.setText("CASH SURPLUS" if shortfall >= 0 else "CASH SHORTFALL")
            self.m_shortfall.update_value(
                format_currency(shortfall) if shortfall >= 0
                else f"-{format_currency(abs(shortfall))}"
            )

            # Status
            if data.get("is_closed"):
                self._show_status("✅", "This month has been CLOSED and finalized.",
                                  ACCENT_SUCCESS)
                self.close_btn.setEnabled(False)
            else:
                self._show_status("📋", "This month is OPEN - review payments and expenses, then close.",
                                  ACCENT_WARNING)
                self.close_btn.setEnabled(True)

            # Fuel table
            fuel_rows = []
            total_fuel_profit = 0.0
            for fb in data.get("fuel_breakdown", []):
                profit = fb.get("profit", 0)
                total_fuel_profit += profit
                fuel_rows.append((
                    fb.get("fuel_type", ""),
                    format_litres(fb.get("litres_sold", 0)),
                    format_currency(fb.get("sales_amount", 0)),
                    format_currency(fb.get("purchase_cost", 0)),
                    format_currency(profit),
                ))

            # Add mathematical transition rows for clarity
            fuel_rows.append(("—" * 20, "—" * 15, "—" * 15, "—" * 15, "—" * 15))

            # Total Fuel Gross Profit
            fuel_rows.append((
                "Total Fuel Gross Profit", "", "", "",
                format_currency(total_fuel_profit)
            ))

            # Deduct expenses
            daily_exp = data.get("total_daily_expenses", 0)
            monthly_exp = data.get("total_monthly_expenses", 0)
            total_sal = data.get("total_salaries", 0)

            if daily_exp > 0:
                fuel_rows.append((
                    "Less: Daily Operational Expenses", "", "", "",
                    f"- {format_currency(daily_exp)}"
                ))
            if monthly_exp > 0:
                fuel_rows.append((
                    "Less: Monthly Expenses", "", "", "",
                    f"- {format_currency(monthly_exp)}"
                ))
            if total_sal > 0:
                fuel_rows.append((
                    "Less: Employee Salaries", "", "", "",
                    f"- {format_currency(total_sal)}"
                ))

            fuel_rows.append(("—" * 20, "—" * 15, "—" * 15, "—" * 15, "—" * 15))

            # Net Profit
            net_profit = data.get("net_profit", 0)
            fuel_rows.append((
                "Net Profit", "", "", "",
                format_currency(net_profit)
            ))

            self.fuel_table.populate(fuel_rows)

            # Payment table — FIXED: Show monthly payment collections
            pay_rows = []
            for pb in data.get("payment_breakdown", []):
                pay_rows.append((
                    pb.get("method", ""),
                    format_currency(pb.get("amount", 0)),
                ))
            pay_rows.extend([
                ("Expected Cash Collection", format_currency(data.get("expected_cash_collection", 0))),
                ("Actual Cash Collection", format_currency(data.get("cash_collection", 0))),
                ("Cash Surplus / Shortfall", format_currency(data.get("payment_shortfall", 0))),
            ])
            self.payment_table.populate(pay_rows)

            # Expense table — show aggregated expenses info
            exp_rows = []
            # Daily operational expenses
            daily_exp = data.get("total_daily_expenses", 0)
            if daily_exp > 0:
                exp_rows.append(("Daily Operational Expenses", format_currency(daily_exp)))
            # Monthly expenses from the management table
            for me in data.get("monthly_expenses", []):
                exp_rows.append((
                    me.get("category", ""),
                    format_currency(me.get("amount", 0)),
                ))
            for sp in data.get("salaries", []):
                exp_rows.append((
                    f"Salary - {sp.get('employee_name', '')} ({sp.get('paid_date') or '-'})",
                    format_currency(sp.get("monthly_salary", 0)),
                ))
            self.expense_table.populate(exp_rows)

            # Load salaries, monthly expenses, and bank deposits
            self._refresh_salary_table()
            self._refresh_mexp_table()
            self._refresh_bank_deposits()

        except Exception as e:
            print(f"Error loading monthly report: {e}")

    def _show_status(self, icon: str, text: str, color):
        self.status_banner.setVisible(True)
        self.status_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {color}15;
                border: 1.5px solid {color}60;
                border-radius: 8px;
            }}
        """)
        self.status_icon.setText(icon)
        self.status_text.setText(text)
        self.status_text.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {color}; border: none;"
        )

    # ── Close Operations ──

    def _close_period(self):
        if self.report_type_combo.currentIndex() == 0:
            self._close_daily()
        else:
            self._close_monthly()

    def _close_daily(self):
        date_str = self.daily_date_picker.get_date_str()
        reply = QMessageBox.question(
            self, "Confirm Daily Close",
            f"Are you sure you want to CLOSE {date_str}?\n\n"
            "This will lock the day's records and finalize the profit report.\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            result = client.post(
                f"/api/report/daily/close?report_date={date_str}", data={}
            )
            if self._toast:
                self._toast.show_message(
                    f"Day closed! Net Profit: {format_currency(result.get('net_profit', 0))}",
                    "success"
                )
            self._load_daily()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _close_monthly(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        month_name = get_month_name(month)

        reply = QMessageBox.question(
            self, "Confirm Monthly Close",
            f"Are you sure you want to CLOSE {month_name} {year}?\n\n"
            "Ensure salary payments and monthly expenses are recorded.\n"
            "This will lock the month's ledger and compute final profit.\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            result = client.post(
                f"/api/report/monthly/close?year={year}&month={month}", data={}
            )
            if self._toast:
                self._toast.show_message(
                    f"{month_name} {year} closed! Net Profit: "
                    f"{format_currency(result.get('net_profit', 0))}",
                    "success"
                )
            self._load_monthly()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    # ── PDF Export ──

    def _export_pdf(self):
        try:
            if self.report_type_combo.currentIndex() == 0:
                # Daily
                if not self._daily_data:
                    self._load_daily()
                if not self._daily_data:
                    return
                filepath = generate_daily_pdf(self._daily_data)
                default_name = os.path.basename(filepath)
            else:
                # Monthly
                if not self._monthly_data:
                    self._load_monthly()
                if not self._monthly_data:
                    return
                filepath = generate_monthly_pdf(self._monthly_data)
                default_name = os.path.basename(filepath)

            # Ask user where to save
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report",
                default_name,
                "PDF Files (*.pdf)"
            )

            if save_path:
                import shutil
                shutil.copy2(filepath, save_path)

                if self._toast:
                    self._toast.show_message(
                        f"PDF saved: {os.path.basename(save_path)}", "success"
                    )

                try:
                    os.startfile(save_path)
                except Exception:
                    pass
            else:
                if self._toast:
                    self._toast.show_message("PDF export cancelled", "info")

        except Exception as e:
            if self._toast:
                self._toast.show_message(f"PDF Error: {e}", "error", 5000)

    # ── Load From Employees ──

    def _load_from_employees(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        if not month or not year:
            return

        reply = QMessageBox.question(
            self, "Load Employee Salaries",
            f"Load all active employee salaries for {get_month_name(month)} {year}?\n\n"
            "Existing salary entries for employees already loaded will be skipped.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            result = client.post(
                f"/api/report/salaries/load-from-employees?year={year}&month={month}",
                data={}
            )
            added = result.get("added", 0)
            skipped = result.get("skipped", 0)
            if self._toast:
                self._toast.show_message(
                    f"Loaded {added} salaries ({skipped} already existed)", "success"
                )
            self._refresh_salary_table()
            self._load_monthly()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    # ── Salary Management ──

    def _add_salary(self):
        name = self.emp_name_input.text().strip()
        desg = self.emp_desg_input.text().strip()
        salary = self.emp_salary_input.get_value()

        if not name:
            if self._toast:
                self._toast.show_message("Enter employee name!", "error")
            return
        if salary <= 0:
            if self._toast:
                self._toast.show_message("Enter a valid salary!", "error")
            return

        month = self.month_combo.currentData()
        year = self.year_combo.currentData()

        try:
            client.post(
                f"/api/report/salaries?year={year}&month={month}",
                data={
                    "employee_name": name,
                    "designation": desg or None,
                    "monthly_salary": salary,
                }
            )
            self.emp_name_input.clear()
            self.emp_desg_input.clear()
            self.emp_salary_input.clear_value()

            if self._toast:
                self._toast.show_message(f"Salary added for {name}", "success")

            self._refresh_salary_table()
            self._load_monthly()  # Refresh summary metrics
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _delete_salary(self, salary_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete", "Delete this salary record?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/report/salaries/{salary_id}")
            if self._toast:
                self._toast.show_message("Salary record deleted", "success")
            self._refresh_salary_table()
            self._load_monthly()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _refresh_salary_table(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        if not month or not year:
            return
        try:
            salaries = client.get(
                "/api/report/salaries",
                params={"year": year, "month": month}
            )
            rows = []
            ids = []
            total_sal = 0.0
            for s in salaries:
                rows.append((
                    s["employee_name"],
                    format_currency(s["monthly_salary"]),
                    s.get("paid_date") or "-",
                ))
                ids.append(s["id"])
                total_sal += s["monthly_salary"]
            self.salary_table.populate(rows, row_ids=ids)
            self.sal_total_label.setText(f"Total: {format_currency(total_sal)}")
        except Exception as e:
            print(f"Error loading salaries: {e}")

    # ── Monthly Expense Management ──

    def _add_monthly_expense(self):
        category = self.mexp_category_input.currentText()
        amount = self.mexp_amount_input.get_value()
        desc = self.mexp_desc_input.text().strip()

        if amount <= 0:
            if self._toast:
                self._toast.show_message("Enter a valid amount!", "error")
            return

        month = self.month_combo.currentData()
        year = self.year_combo.currentData()

        try:
            client.post(
                f"/api/report/monthly-expenses?year={year}&month={month}",
                data={
                    "category": category,
                    "amount": amount,
                    "description": desc or None,
                }
            )
            self.mexp_amount_input.clear_value()
            self.mexp_desc_input.clear()

            if self._toast:
                self._toast.show_message(
                    f"{category} expense added: {format_currency(amount)}", "success"
                )

            self._refresh_mexp_table()
            self._load_monthly()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _delete_monthly_expense(self, expense_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete", "Delete this monthly expense?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/report/monthly-expenses/{expense_id}")
            if self._toast:
                self._toast.show_message("Monthly expense deleted", "success")
            self._refresh_mexp_table()
            self._load_monthly()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _refresh_mexp_table(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        if not month or not year:
            return
        try:
            expenses = client.get(
                "/api/report/monthly-expenses",
                params={"year": year, "month": month}
            )
            rows = []
            ids = []
            total_mexp = 0.0
            for me in expenses:
                rows.append((
                    me["category"],
                    format_currency(me["amount"]),
                    me.get("description") or "-",
                ))
                ids.append(me["id"])
                total_mexp += me["amount"]
            self.mexp_table.populate(rows, row_ids=ids)
            self.mexp_total_label.setText(f"Total: {format_currency(total_mexp)}")
        except Exception as e:
            print(f"Error loading monthly expenses: {e}")

    # ── Bank Deposit Management ──

    def _save_bank_deposit(self):
        wc = self.bd_wc_input.get_value()
        solar = self.bd_solar_input.get_value()
        truck = self.bd_truck_input.get_value()
        topup = self.bd_topup_input.get_value()

        total = wc + solar + truck + topup
        if total <= 0:
            if self._toast:
                self._toast.show_message("Enter at least one deposit amount!", "error")
            return

        month = self.month_combo.currentData()
        year = self.year_combo.currentData()

        try:
            from datetime import date as dt_date
            data = {
                "month": month,
                "year": year,
                "working_capital": wc,
                "solar": solar,
                "truck": truck,
                "top_up_finance": topup,
            }
            if self._bd_edit_id:
                client.put(f"/api/bank-deposit/entry/{self._bd_edit_id}", data=data)
            else:
                data["deposit_date"] = dt_date.today().isoformat()
                client.post("/api/bank-deposit/entry", data=data)

            # Clear inputs
            self._cancel_bd_edit()

            if self._toast:
                self._toast.show_message(
                    f"Bank deposit saved: {format_currency(total)}", "success"
                )

            self._refresh_bank_deposits()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _cancel_bd_edit(self):
        self._bd_edit_id = None
        self.bd_wc_input.clear_value()
        self.bd_solar_input.clear_value()
        self.bd_truck_input.clear_value()
        self.bd_topup_input.clear_value()
        self.bd_save_btn.setText("  + Save Deposit  ")
        self.bd_cancel_btn.setVisible(False)

    def _on_bd_row_clicked(self, row, col):
        if col == self.bd_table.columnCount() - 1 and self.bd_table._enable_delete:
            return # Ignore delete button clicks

        if row >= len(self.bd_table._row_ids):
            return

        deposit_id = self.bd_table._row_ids[row]
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()

        try:
            # Find the specific deposit
            deposits = client.get("/api/bank-deposit/list", params={"month": month, "year": year})
            deposit = next((d for d in deposits if d["id"] == deposit_id), None)
            
            if deposit:
                self._bd_edit_id = deposit_id
                self.bd_wc_input.set_value(deposit.get("working_capital", 0))
                self.bd_solar_input.set_value(deposit.get("solar", 0))
                self.bd_truck_input.set_value(deposit.get("truck", 0))
                self.bd_topup_input.set_value(deposit.get("top_up_finance", 0))

                self.bd_save_btn.setText("  Update Deposit  ")
                self.bd_cancel_btn.setVisible(True)
        except Exception as e:
            print(f"Error loading deposit for edit: {e}")

    def _delete_bank_deposit(self, deposit_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete", "Delete this bank deposit entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/bank-deposit/entry/{deposit_id}")
            if self._toast:
                self._toast.show_message("Bank deposit deleted", "success")
            self._refresh_bank_deposits()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _refresh_bank_deposits(self):
        month = self.month_combo.currentData()
        year = self.year_combo.currentData()
        if not month or not year:
            return
        try:
            # Get summary for breakdown
            summary = client.get("/api/bank-deposit/summary", params={
                "month": month, "year": year
            })
            self.bd_wc_summary.setText(
                f"Working Capital: {format_currency(summary.get('total_working_capital', 0))}"
            )
            self.bd_solar_summary.setText(
                f"Solar: {format_currency(summary.get('total_solar', 0))}"
            )
            self.bd_truck_summary.setText(
                f"Truck: {format_currency(summary.get('total_truck', 0))}"
            )
            self.bd_topup_summary.setText(
                f"Top Up: {format_currency(summary.get('total_top_up_finance', 0))}"
            )
            self.bd_total_label.setText(
                f"Total Deposited: {format_currency(summary.get('grand_total', 0))}"
            )

            # Get individual entries for history table
            deposits = client.get("/api/bank-deposit/list", params={
                "month": month, "year": year
            })
            rows = []
            ids = []
            for d in deposits:
                rows.append((
                    format_currency(d.get("working_capital", 0)),
                    format_currency(d.get("solar", 0)),
                    format_currency(d.get("truck", 0)),
                    format_currency(d.get("top_up_finance", 0)),
                    format_currency(d.get("total", 0)),
                    d.get("deposit_date") or "-",
                ))
                ids.append(d["id"])
            self.bd_table.populate(rows, row_ids=ids)

        except Exception as e:
            print(f"Error loading bank deposits: {e}")
