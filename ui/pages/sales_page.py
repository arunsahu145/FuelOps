"""
Petrol Pump Finance Manager ERP — Sales Analytics & Logs (v2)
Rich analytics dashboard with summary cards, fuel/shift/nozzle breakdowns,
daily trends, and filterable transaction log.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox,
    QPushButton, QMessageBox, QScrollArea, QGridLayout, QSizePolicy,
    QTabWidget
)
from PySide6.QtCore import Qt, QDate
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_SUCCESS,
    ACCENT_WARNING, ACCENT_DANGER, BG_SURFACE, BG_MAIN,
    BG_SURFACE_LIGHT, BORDER_COLOR
)
from ui.components.date_picker import DatePicker
from ui.components.data_table import DataTable
from ui.api_client import client
from utils.helpers import format_currency, format_litres, get_month_name


# ═══════════════════════════════════════════════════════════════════════════════
# STAT CARD — reusable compact metric for analytics
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyticsCard(QFrame):
    """Compact metric card for the analytics section."""
    def __init__(self, label: str, value: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("AnalyticsCard")
        self.setStyleSheet(f"""
            QFrame#AnalyticsCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-left: 4px solid {accent};
                border-radius: 8px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(85)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self.label_lbl = QLabel(label, self)
        self.label_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {TEXT_SECONDARY}; "
            f"letter-spacing: 0.5px; text-transform: uppercase;"
        )
        layout.addWidget(self.label_lbl)

        self.value_lbl = QLabel(value, self)
        self.value_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY}; "
            f"font-family: 'Consolas', monospace;"
        )
        layout.addWidget(self.value_lbl)

        self.sub_lbl = QLabel("", self)
        self.sub_lbl.setStyleSheet(
            f"font-size: 10px; color: {TEXT_SECONDARY};"
        )
        layout.addWidget(self.sub_lbl)

        layout.addStretch()

    def update_data(self, value: str, subtitle: str = ""):
        self.value_lbl.setText(value)
        self.sub_lbl.setText(subtitle)


# ═══════════════════════════════════════════════════════════════════════════════
# FUEL CARD — color-coded fuel performance widget
# ═══════════════════════════════════════════════════════════════════════════════

class FuelBreakdownCard(QFrame):
    """Color-coded card for fuel-wise breakdown."""
    def __init__(self, fuel_type: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("FuelCard")
        self.setStyleSheet(f"""
            QFrame#FuelCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-top: 3px solid {color};
                border-radius: 8px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        self.name_lbl = QLabel(fuel_type, self)
        self.name_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {color}; "
            f"letter-spacing: 0.5px;"
        )
        layout.addWidget(self.name_lbl)

        self.sales_lbl = QLabel("₹0.00", self)
        self.sales_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY}; "
            f"font-family: 'Consolas', monospace;"
        )
        layout.addWidget(self.sales_lbl)

        self.litres_lbl = QLabel("0.00 L", self)
        self.litres_lbl.setStyleSheet(
            f"font-size: 10px; color: {TEXT_SECONDARY};"
        )
        layout.addWidget(self.litres_lbl)

        layout.addStretch()

    def update_data(self, sales: str, litres: str):
        self.sales_lbl.setText(sales)
        self.litres_lbl.setText(litres)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SALES PAGE
# ═══════════════════════════════════════════════════════════════════════════════

FUEL_COLORS = {
    "Petrol": "#10b981",
    "Power Petrol": "#0ea5e9",
    "Diesel": "#f59e0b",
}


class SalesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
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
        title_lbl = QLabel("SALES ANALYTICS & INSIGHTS", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel(
            "Comprehensive sales performance metrics, fuel breakdowns, and transaction logs.",
            self
        )
        sub_lbl.setObjectName("SubHeaderLabel")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header.addLayout(title_vbox)
        header.addStretch()
        layout.addLayout(header)

        # ── View Selector ──
        selector_frame = QFrame(self)
        selector_frame.setObjectName("SmartCard")
        sel_layout = QHBoxLayout(selector_frame)
        sel_layout.setContentsMargins(16, 12, 16, 12)
        sel_layout.setSpacing(16)

        view_lbl = QLabel("VIEW:", self)
        view_lbl.setStyleSheet(
            f"font-weight: bold; color: {TEXT_SECONDARY}; font-size: 12px;"
        )
        sel_layout.addWidget(view_lbl)

        self.view_combo = QComboBox(self)
        self.view_combo.addItems(["Daily View", "Monthly View"])
        self.view_combo.setMinimumWidth(140)
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)
        sel_layout.addWidget(self.view_combo)

        # Daily date picker
        self.date_picker = DatePicker(self)
        self.date_picker.date_changed.connect(lambda: self._load_data())
        sel_layout.addWidget(self.date_picker)

        # Monthly selectors
        self.month_combo = QComboBox(self)
        for m in range(1, 13):
            self.month_combo.addItem(get_month_name(m), m)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_combo.setMinimumWidth(120)
        self.month_combo.currentIndexChanged.connect(lambda: self._load_data())
        sel_layout.addWidget(self.month_combo)

        self.year_combo = QComboBox(self)
        current_year = QDate.currentDate().year()
        for y in range(current_year - 2, current_year + 2):
            self.year_combo.addItem(str(y), y)
        self.year_combo.setCurrentIndex(2)
        self.year_combo.setMinimumWidth(80)
        self.year_combo.currentIndexChanged.connect(lambda: self._load_data())
        sel_layout.addWidget(self.year_combo)

        # Fuel filter
        self.fuel_filter = QComboBox(self)
        self.fuel_filter.addItem("All Products", None)
        self.fuel_filter.setMinimumWidth(140)
        sel_layout.addWidget(self.fuel_filter)

        sel_layout.addStretch()

        self.refresh_btn = QPushButton("  🔄 Refresh  ", self)
        self.refresh_btn.setObjectName("ActionButton")
        self.refresh_btn.clicked.connect(self._load_data)
        sel_layout.addWidget(self.refresh_btn)

        layout.addWidget(selector_frame)

        # ── Summary Cards ──
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)

        self.card_sales = AnalyticsCard("TOTAL SALES", "₹0.00", ACCENT_PRIMARY, self)
        self.card_litres = AnalyticsCard("TOTAL LITRES", "0.00 L", ACCENT_SUCCESS, self)
        self.card_avg = AnalyticsCard("AVG ₹/LITRE", "₹0.00", ACCENT_WARNING, self)
        self.card_top = AnalyticsCard("TOP PRODUCT", "-", "#a855f7", self)

        cards_grid.addWidget(self.card_sales, 0, 0)
        cards_grid.addWidget(self.card_litres, 0, 1)
        cards_grid.addWidget(self.card_avg, 0, 2)
        cards_grid.addWidget(self.card_top, 0, 3)

        layout.addLayout(cards_grid)

        # ── Fuel-wise Breakdown Cards ──
        self.fuel_cards_layout = QHBoxLayout()
        self.fuel_cards_layout.setSpacing(12)

        self.fuel_cards = {}
        for fuel_type, color in FUEL_COLORS.items():
            card = FuelBreakdownCard(fuel_type, color, self)
            self.fuel_cards[fuel_type] = card
            self.fuel_cards_layout.addWidget(card)

        layout.addLayout(self.fuel_cards_layout)

        # ── Detail Tables (Tabbed) ──
        self.detail_frame = QFrame(self)
        self.detail_frame.setObjectName("SmartCard")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

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

        # Shift Breakdown Tab
        shift_tab = QWidget()
        shift_layout = QVBoxLayout(shift_tab)
        shift_layout.setContentsMargins(8, 8, 8, 8)
        self.shift_table = DataTable(
            ["Shift", "Litres Sold", "Sales Amount"],
            self
        )
        self.shift_table.setMinimumHeight(420)
        shift_layout.addWidget(self.shift_table)
        self.detail_tabs.addTab(shift_tab, "📝 Shift Breakdown")

        # Nozzle Breakdown Tab
        nozzle_tab = QWidget()
        nozzle_layout = QVBoxLayout(nozzle_tab)
        nozzle_layout.setContentsMargins(8, 8, 8, 8)
        self.nozzle_table = DataTable(
            ["Nozzle", "Litres Sold", "Sales Amount"],
            self
        )
        self.nozzle_table.setMinimumHeight(420)
        nozzle_layout.addWidget(self.nozzle_table)
        self.detail_tabs.addTab(nozzle_tab, "🔧 Nozzle Breakdown")

        # Daily Trend Tab (Monthly view)
        trend_tab = QWidget()
        trend_layout = QVBoxLayout(trend_tab)
        trend_layout.setContentsMargins(8, 8, 8, 8)
        self.trend_table = DataTable(
            ["Date", "Total Litres", "Total Sales"],
            self
        )
        self.trend_table.setMinimumHeight(420)
        trend_layout.addWidget(self.trend_table)
        self.detail_tabs.addTab(trend_tab, "📈 Daily Trend")

        # Transaction Log Tab
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(8, 8, 8, 8)
        self.log_table = DataTable(
            ["Date", "Fuel", "Nozzle", "Shift", "Litres", "Rate", "Amount"],
            self
        )
        self.log_table.setMinimumHeight(420)
        log_layout.addWidget(self.log_table)
        self.detail_tabs.addTab(log_tab, "📋 Transaction Log")

        self.detail_tabs.setMinimumHeight(500)
        detail_layout.addWidget(self.detail_tabs)
        layout.addWidget(self.detail_frame)

        layout.addStretch()

        # Initialize visibility
        self._on_view_changed(0)

    def _on_view_changed(self, index):
        """Toggle between Daily and Monthly views."""
        is_daily = index == 0
        self.date_picker.setVisible(is_daily)
        self.month_combo.setVisible(not is_daily)
        self.year_combo.setVisible(not is_daily)

    # ── Data Loading ──

    def load_data(self):
        """Called when page is navigated to."""
        # Load fuel types for filter
        try:
            fuels = client.get("/api/fuel/types")
            self.fuel_filter.blockSignals(True)
            self.fuel_filter.clear()
            self.fuel_filter.addItem("All Products", None)
            for f in fuels:
                self.fuel_filter.addItem(f["name"], f["id"])
            self.fuel_filter.blockSignals(False)
        except Exception:
            pass

        self._load_data()

    def _load_data(self):
        if self.view_combo.currentIndex() == 0:
            self._load_daily()
        else:
            self._load_monthly()

    def _load_daily(self):
        try:
            date_str = self.date_picker.get_date_str()
            fuel_id = self.fuel_filter.currentData()

            params = {"sale_date": date_str}
            if fuel_id:
                params["fuel_type_id"] = fuel_id

            data = client.get("/api/sales/daily", params=params)

            total_litres = data.get("total_litres", 0)
            total_amount = data.get("total_amount", 0)
            avg_price = (total_amount / total_litres) if total_litres > 0 else 0

            # Summary cards
            self.card_sales.update_data(format_currency(total_amount), "Today's total")
            self.card_litres.update_data(format_litres(total_litres), "Litres dispensed")
            self.card_avg.update_data(format_currency(avg_price), "Average per litre")

            # Find top fuel
            fuel_bd = data.get("fuel_breakdown", [])
            if fuel_bd:
                top = max(fuel_bd, key=lambda x: x.get("amount", 0))
                self.card_top.update_data(
                    top.get("fuel_type", "-"),
                    format_currency(top.get("amount", 0))
                )
            else:
                self.card_top.update_data("-", "No sales")

            # Fuel breakdown cards
            for fuel_name, card in self.fuel_cards.items():
                found = False
                for fb in fuel_bd:
                    if fb.get("fuel_type") == fuel_name:
                        card.update_data(
                            format_currency(fb.get("amount", 0)),
                            format_litres(fb.get("litres", 0))
                        )
                        found = True
                        break
                if not found:
                    card.update_data("₹0.00", "0.00 L")

            # Shift breakdown table
            shift_bd = data.get("shift_breakdown", [])
            shift_rows = []
            for sb in shift_bd:
                shift_num = sb.get("shift", 0)
                label = f"Shift {shift_num}" if shift_num > 0 else "Unassigned"
                shift_rows.append((
                    label,
                    format_litres(sb.get("litres", 0)),
                    format_currency(sb.get("amount", 0)),
                ))
            self.shift_table.populate(shift_rows)

            # Nozzle breakdown table
            nozzle_bd = data.get("nozzle_breakdown", [])
            nozzle_rows = []
            for nb in sorted(nozzle_bd, key=lambda x: x.get("nozzle", 0)):
                nn = nb.get("nozzle", 0)
                label = f"Nozzle {nn}" if nn > 0 else "Unknown"
                nozzle_rows.append((
                    label,
                    format_litres(nb.get("litres", 0)),
                    format_currency(nb.get("amount", 0)),
                ))
            self.nozzle_table.populate(nozzle_rows)

            # Daily trend — not applicable for daily view, clear it
            self.trend_table.populate([])

            # Transaction log
            self._load_transaction_log()

        except Exception as e:
            print(f"Error loading daily sales: {e}")

    def _load_monthly(self):
        try:
            month = self.month_combo.currentData()
            year = self.year_combo.currentData()
            if not month or not year:
                return

            fuel_id = self.fuel_filter.currentData()
            params = {"year": year, "month": month}
            if fuel_id:
                params["fuel_type_id"] = fuel_id

            data = client.get("/api/sales/monthly", params=params)

            total_litres = data.get("total_litres", 0)
            total_amount = data.get("total_amount", 0)
            avg_price = (total_amount / total_litres) if total_litres > 0 else 0

            month_name = get_month_name(month)

            # Summary cards
            self.card_sales.update_data(format_currency(total_amount), f"{month_name} total")
            self.card_litres.update_data(format_litres(total_litres), f"Litres in {month_name}")
            self.card_avg.update_data(format_currency(avg_price), "Average per litre")

            # Find top fuel
            fuel_bd = data.get("fuel_breakdown", [])
            if fuel_bd:
                top = max(fuel_bd, key=lambda x: x.get("amount", 0))
                self.card_top.update_data(
                    top.get("fuel_type", "-"),
                    format_currency(top.get("amount", 0))
                )
            else:
                self.card_top.update_data("-", "No sales")

            # Fuel breakdown cards
            for fuel_name, card in self.fuel_cards.items():
                found = False
                for fb in fuel_bd:
                    if fb.get("fuel_type") == fuel_name:
                        card.update_data(
                            format_currency(fb.get("amount", 0)),
                            format_litres(fb.get("litres", 0))
                        )
                        found = True
                        break
                if not found:
                    card.update_data("₹0.00", "0.00 L")

            # Shift breakdown — N/A for monthly (no aggregation), clear
            self.shift_table.populate([])

            # Nozzle breakdown — N/A for monthly, clear
            self.nozzle_table.populate([])

            # Daily trend
            daily_totals = data.get("daily_totals", [])
            trend_rows = []
            for dt in sorted(daily_totals, key=lambda x: x.get("date", "")):
                trend_rows.append((
                    dt.get("date", ""),
                    format_litres(dt.get("litres", 0)),
                    format_currency(dt.get("amount", 0)),
                ))
            self.trend_table.populate(trend_rows)

            # Transaction log
            self._load_transaction_log_monthly(year, month)

        except Exception as e:
            print(f"Error loading monthly sales: {e}")

    def _load_transaction_log(self):
        """Load daily transaction log."""
        try:
            date_str = self.date_picker.get_date_str()
            fuel_id = self.fuel_filter.currentData()

            params = {"start_date": date_str, "end_date": date_str}
            if fuel_id:
                params["fuel_type_id"] = fuel_id

            sales = client.get("/api/sales/list", params=params)
            rows = []
            for s in sales:
                rows.append((
                    s["sale_date"],
                    s["fuel_type_name"],
                    f"Nozzle {s['nozzle_number']}" if s.get("nozzle_number") else "-",
                    f"Shift {s['shift_number']}" if s.get("shift_number") else "-",
                    format_litres(s["litres_sold"]),
                    format_currency(s["selling_price"]),
                    format_currency(s["total_amount"]),
                ))
            self.log_table.populate(rows)
        except Exception as e:
            print(f"Error loading transaction log: {e}")

    def _load_transaction_log_monthly(self, year: int, month: int):
        """Load monthly transaction log."""
        try:
            from utils.helpers import get_month_range
            first_day, last_day = get_month_range(year, month)

            fuel_id = self.fuel_filter.currentData()
            params = {
                "start_date": str(first_day),
                "end_date": str(last_day),
            }
            if fuel_id:
                params["fuel_type_id"] = fuel_id

            sales = client.get("/api/sales/list", params=params)
            rows = []
            for s in sales:
                rows.append((
                    s["sale_date"],
                    s["fuel_type_name"],
                    f"Nozzle {s['nozzle_number']}" if s.get("nozzle_number") else "-",
                    f"Shift {s['shift_number']}" if s.get("shift_number") else "-",
                    format_litres(s["litres_sold"]),
                    format_currency(s["selling_price"]),
                    format_currency(s["total_amount"]),
                ))
            self.log_table.populate(rows)
        except Exception as e:
            print(f"Error loading monthly transaction log: {e}")
