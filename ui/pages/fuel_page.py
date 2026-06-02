"""
Petrol Pump Finance Manager ERP — Fuel Page (v2)
All 3 fuel types as inline cards. Price history with delete support.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QMessageBox, QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from ui.components.currency_input import IndianCurrencyLineEdit
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_SUCCESS,
    BG_MAIN, BG_SURFACE, BG_SURFACE_LIGHT, BORDER_COLOR
)
from ui.components.data_table import DataTable
from ui.api_client import client
from utils.helpers import format_currency, get_fuel_color


class FuelRateCard(QFrame):
    """A single fuel type card with inline purchase/selling rate editing."""

    def __init__(self, fuel_data: dict, parent_page=None, parent=None):
        super().__init__(parent)
        self.setObjectName("FuelRateCard")
        self.fuel_data = fuel_data
        self.fuel_id = fuel_data["id"]
        self.fuel_name = fuel_data["name"]
        self.parent_page = parent_page
        self._init_ui()

    def _init_ui(self):
        fuel_color = get_fuel_color(self.fuel_name)

        self.setStyleSheet(
            f"QFrame#FuelRateCard {{ background-color: {BG_SURFACE}; "
            f"border: 1px solid {BORDER_COLOR}; border-left: 4px solid {fuel_color}; "
            f"border-radius: 10px; }}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        name_lbl = QLabel(self.fuel_name.upper(), self)
        name_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {fuel_color}; "
            f"letter-spacing: 1px;"
        )
        layout.addWidget(name_lbl)

        self.current_prices_lbl = QLabel("", self)
        self.current_prices_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_SECONDARY}; padding: 2px 0;"
        )
        layout.addWidget(self.current_prices_lbl)

        # Purchase Rate
        p_lbl = QLabel("PURCHASE RATE (₹/L)", self)
        p_lbl.setObjectName("FormLabel")
        layout.addWidget(p_lbl)

        p_row = QHBoxLayout()
        p_row.setSpacing(8)
        self.purchase_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.purchase_input.setObjectName("ReadingInput")
        self.purchase_input.returnPressed.connect(self._save_purchase_rate)
        p_row.addWidget(self.purchase_input)
        self.save_p_btn = QPushButton("Save", self)
        self.save_p_btn.setObjectName("ActionButton")
        self.save_p_btn.setFixedWidth(70)
        self.save_p_btn.clicked.connect(self._save_purchase_rate)
        p_row.addWidget(self.save_p_btn)
        layout.addLayout(p_row)

        # Selling Rate
        s_lbl = QLabel("SELLING RATE (₹/L)", self)
        s_lbl.setObjectName("FormLabel")
        layout.addWidget(s_lbl)

        s_row = QHBoxLayout()
        s_row.setSpacing(8)
        self.selling_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.selling_input.setObjectName("ReadingInput")
        self.selling_input.returnPressed.connect(self._save_selling_rate)
        s_row.addWidget(self.selling_input)
        self.save_s_btn = QPushButton("Save", self)
        self.save_s_btn.setObjectName("SuccessButton")
        self.save_s_btn.setFixedWidth(70)
        self.save_s_btn.clicked.connect(self._save_selling_rate)
        s_row.addWidget(self.save_s_btn)
        layout.addLayout(s_row)

        self.margin_lbl = QLabel("", self)
        self.margin_lbl.setStyleSheet(
            f"font-size: 11px; color: {ACCENT_SUCCESS}; font-weight: 600; padding: 4px 0 0 0;"
        )
        layout.addWidget(self.margin_lbl)

        QWidget.setTabOrder(self.purchase_input, self.selling_input)

    def populate(self, fuel_data: dict):
        self.fuel_data = fuel_data
        p_price = fuel_data.get("current_purchase_price")
        s_price = fuel_data.get("current_selling_price")

        if p_price:
            self.purchase_input.set_value(p_price)
        else:
            self.purchase_input.clear_value()

        if s_price:
            self.selling_input.set_value(s_price)
        else:
            self.selling_input.clear_value()

        p_str = format_currency(p_price) if p_price else "Not set"
        s_str = format_currency(s_price) if s_price else "Not set"
        self.current_prices_lbl.setText(f"Current: Buy {p_str}  |  Sell {s_str}")

        if p_price and s_price and p_price > 0:
            margin = s_price - p_price
            margin_pct = (margin / p_price) * 100
            if margin >= 0:
                self.margin_lbl.setStyleSheet(
                    f"font-size: 11px; color: {ACCENT_SUCCESS}; font-weight: 600; padding: 4px 0 0 0;"
                )
                self.margin_lbl.setText(f"Margin: {format_currency(margin)}/L ({margin_pct:.1f}%)")
            else:
                self.margin_lbl.setStyleSheet(
                    "font-size: 11px; color: #ef4444; font-weight: 600; padding: 4px 0 0 0;"
                )
                self.margin_lbl.setText(f"Loss: {format_currency(abs(margin))}/L")
        else:
            self.margin_lbl.setText("")

    def _save_purchase_rate(self):
        price = self.purchase_input.get_value()
        if price <= 0:
            return
        try:
            client.post("/api/fuel/purchase-rate", data={
                "fuel_type_id": self.fuel_id,
                "price_per_litre": price
            })
            self._refresh_card_data()
            if self.parent_page and self.parent_page._toast:
                self.parent_page._toast.show_message(
                    f"{self.fuel_name} purchase rate → {format_currency(price)}/L", "success"
                )
        except Exception as e:
            if self.parent_page and self.parent_page._toast:
                self.parent_page._toast.show_message(f"Error: {e}", "error", 5000)

    def _save_selling_rate(self):
        price = self.selling_input.get_value()
        if price <= 0:
            return
        try:
            client.post("/api/fuel/selling-rate", data={
                "fuel_type_id": self.fuel_id,
                "price_per_litre": price
            })
            self._refresh_card_data()
            if self.parent_page and self.parent_page._toast:
                self.parent_page._toast.show_message(
                    f"{self.fuel_name} selling rate → {format_currency(price)}/L", "success"
                )
        except Exception as e:
            if self.parent_page and self.parent_page._toast:
                self.parent_page._toast.show_message(f"Error: {e}", "error", 5000)

    def _refresh_card_data(self):
        try:
            fuel_data = client.get(f"/api/fuel/types/{self.fuel_id}")
            self.populate(fuel_data)
        except Exception:
            pass


class FuelPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
        self.fuel_cards = []
        self._init_ui()

    def set_toast(self, toast):
        self._toast = toast

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(scroll)

        content_widget = QWidget()
        content_widget.setObjectName("PageContainer")
        scroll.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        header_vbox = QVBoxLayout()
        title_lbl = QLabel("FUEL RATES & PRICING", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel(
            "Set and update buying & selling prices. Changes save inline — no page navigation required.",
            self
        )
        sub_lbl.setObjectName("SubHeaderLabel")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(sub_lbl)
        layout.addLayout(header_vbox)

        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(16)
        layout.addLayout(self.cards_layout)

        # Collapsible History with delete support
        history_row = QHBoxLayout()
        self.history_toggle_btn = QPushButton("  📋 Show Price History ▼", self)
        self.history_toggle_btn.setObjectName("ToggleHistoryBtn")
        self.history_toggle_btn.setFixedWidth(240)
        self.history_toggle_btn.clicked.connect(self._toggle_history)
        history_row.addWidget(self.history_toggle_btn)
        history_row.addStretch()
        layout.addLayout(history_row)

        self.history_frame = QFrame(self)
        self.history_frame.setObjectName("SmartCard")
        self.history_frame.setVisible(False)
        history_layout = QVBoxLayout(self.history_frame)
        history_layout.setContentsMargins(16, 16, 16, 16)
        history_layout.setSpacing(10)

        hist_title = QLabel("PRICE CHANGE LOG", self)
        hist_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        history_layout.addWidget(hist_title)

        self.table = DataTable(
            ["Fuel", "Date Effective", "Type", "Rate per Litre"],
            self,
            enable_delete=True
        )
        self.table.setMinimumHeight(450)
        self.table.row_delete_requested.connect(self._delete_rate_entry)
        history_layout.addWidget(self.table)

        layout.addWidget(self.history_frame)
        layout.addStretch()

        # Store metadata for delete (type + id)
        self._rate_meta = []

    def load_data(self):
        try:
            fuels = client.get("/api/fuel/types")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load fuel types: {e}")
            return

        if not self.fuel_cards:
            for fuel in fuels:
                card = FuelRateCard(fuel, parent_page=self, parent=self)
                self.cards_layout.addWidget(card)
                self.fuel_cards.append(card)

        for i, fuel in enumerate(fuels):
            if i < len(self.fuel_cards):
                self.fuel_cards[i].populate(fuel)

    def _toggle_history(self):
        visible = not self.history_frame.isVisible()
        self.history_frame.setVisible(visible)
        self.history_toggle_btn.setText(
            "  📋 Hide Price History ▲" if visible else "  📋 Show Price History ▼"
        )
        if visible:
            self._refresh_history()

    def _refresh_history(self):
        try:
            fuels = client.get("/api/fuel/types")
            rows = []
            self._rate_meta = []  # (rate_type, rate_id)
            ids = []

            for fuel in fuels:
                p_history = client.get(f"/api/fuel/purchase-rates/{fuel['id']}")
                s_history = client.get(f"/api/fuel/selling-rates/{fuel['id']}")

                for p in p_history:
                    rows.append((
                        fuel["name"],
                        p["effective_from"][:16],
                        "Purchase Rate",
                        format_currency(p["price_per_litre"])
                    ))
                    self._rate_meta.append(("purchase", p["id"]))
                    ids.append(len(self._rate_meta) - 1)  # index into _rate_meta

                for s in s_history:
                    rows.append((
                        fuel["name"],
                        s["effective_from"][:16],
                        "Selling Rate",
                        format_currency(s["price_per_litre"])
                    ))
                    self._rate_meta.append(("selling", s["id"]))
                    ids.append(len(self._rate_meta) - 1)

            # Sort by date descending
            combined = list(zip(rows, ids, self._rate_meta))
            combined.sort(key=lambda x: x[0][1], reverse=True)
            rows = [c[0] for c in combined]
            self._rate_meta = [c[2] for c in combined]
            ids = list(range(len(self._rate_meta)))

            self.table.populate(rows, row_ids=ids)
        except Exception as e:
            print(f"Error loading price history: {e}")

    def _delete_rate_entry(self, meta_idx: int):
        """Delete a fuel rate entry from history."""
        if meta_idx < 0 or meta_idx >= len(self._rate_meta):
            return

        rate_type, rate_id = self._rate_meta[meta_idx]

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete this {rate_type} rate entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            if rate_type == "purchase":
                client.delete(f"/api/fuel/purchase-rate/{rate_id}")
            else:
                client.delete(f"/api/fuel/selling-rate/{rate_id}")

            if self._toast:
                self._toast.show_message(f"{rate_type.title()} rate deleted", "success")

            self._refresh_history()
            self.load_data()  # Refresh cards to show new current price
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Delete failed: {e}", "error", 5000)
