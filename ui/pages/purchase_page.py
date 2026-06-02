"""
Petrol Pump Finance Manager ERP — Purchase Page (v2)
Collapsible history with delete support, full-width form, toast notifications.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox,
    QLineEdit, QPushButton, QMessageBox, QDateEdit, QScrollArea
)
from PySide6.QtCore import Qt, QDate
from ui.components.currency_input import IndianCurrencyLineEdit
from ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, BG_SURFACE, BORDER_COLOR
from ui.components.data_table import DataTable
from ui.api_client import client
from utils.helpers import format_currency, format_litres


class PurchasePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
        self.buying_price_cache = 0.0
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
        layout.setSpacing(20)

        # Header
        header_vbox = QVBoxLayout()
        title_lbl = QLabel("FUEL PURCHASES", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel("Record fuel acquisitions and track purchase history.", self)
        sub_lbl.setObjectName("SubHeaderLabel")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(sub_lbl)
        layout.addLayout(header_vbox)

        # Form Card
        form_frame = QFrame(self)
        form_frame.setObjectName("SmartCard")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(14)

        form_title = QLabel("RECORD NEW PURCHASE", self)
        form_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        form_layout.addWidget(form_title)

        row1 = QHBoxLayout()
        row1.setSpacing(16)

        d_vbox = QVBoxLayout()
        d_lbl = QLabel("PURCHASE DATE", self)
        d_lbl.setObjectName("FormLabel")
        d_vbox.addWidget(d_lbl)
        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        d_vbox.addWidget(self.date_edit)
        row1.addLayout(d_vbox)

        f_vbox = QVBoxLayout()
        fuel_lbl = QLabel("FUEL PRODUCT", self)
        fuel_lbl.setObjectName("FormLabel")
        f_vbox.addWidget(fuel_lbl)
        self.fuel_combo = QComboBox(self)
        self.fuel_combo.currentIndexChanged.connect(self._on_fuel_changed)
        f_vbox.addWidget(self.fuel_combo)
        row1.addLayout(f_vbox)

        sup_vbox = QVBoxLayout()
        sup_lbl = QLabel("SUPPLIER NAME", self)
        sup_lbl.setObjectName("FormLabel")
        sup_vbox.addWidget(sup_lbl)
        self.supplier_input = QLineEdit(self)
        self.supplier_input.setPlaceholderText("e.g., Bharat Petroleum...")
        sup_vbox.addWidget(self.supplier_input)
        row1.addLayout(sup_vbox)

        form_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(16)

        l_vbox = QVBoxLayout()
        litres_lbl = QLabel("LITRES ACQUIRED", self)
        litres_lbl.setObjectName("FormLabel")
        l_vbox.addWidget(litres_lbl)
        self.litres_input = IndianCurrencyLineEdit(self, placeholder="0.00")
        self.litres_input.textChanged.connect(self._on_litres_changed)
        l_vbox.addWidget(self.litres_input)
        row2.addLayout(l_vbox)

        c_vbox = QVBoxLayout()
        cost_lbl = QLabel("TOTAL COST (₹)", self)
        cost_lbl.setObjectName("FormLabel")
        c_vbox.addWidget(cost_lbl)
        self.cost_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.cost_input.textChanged.connect(self._on_cost_changed)
        c_vbox.addWidget(self.cost_input)
        row2.addLayout(c_vbox)

        n_vbox = QVBoxLayout()
        notes_lbl = QLabel("NOTES", self)
        notes_lbl.setObjectName("FormLabel")
        n_vbox.addWidget(notes_lbl)
        self.notes_input = QLineEdit(self)
        self.notes_input.setPlaceholderText("Optional details...")
        self.notes_input.returnPressed.connect(self._save_purchase)
        n_vbox.addWidget(self.notes_input)
        row2.addLayout(n_vbox)

        form_layout.addLayout(row2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.submit_btn = QPushButton("  Save Purchase Entry  ", self)
        self.submit_btn.setObjectName("ActionButton")
        self.submit_btn.clicked.connect(self._save_purchase)
        btn_row.addWidget(self.submit_btn)
        form_layout.addLayout(btn_row)

        layout.addWidget(form_frame)

        QWidget.setTabOrder(self.date_edit, self.fuel_combo)
        QWidget.setTabOrder(self.fuel_combo, self.supplier_input)
        QWidget.setTabOrder(self.supplier_input, self.litres_input)
        QWidget.setTabOrder(self.litres_input, self.cost_input)
        QWidget.setTabOrder(self.cost_input, self.notes_input)

        # Collapsible History with delete
        hist_row = QHBoxLayout()
        self.history_toggle = QPushButton("  📋 Show Recent Purchases ▼", self)
        self.history_toggle.setObjectName("ToggleHistoryBtn")
        self.history_toggle.setFixedWidth(260)
        self.history_toggle.clicked.connect(self._toggle_history)
        hist_row.addWidget(self.history_toggle)
        hist_row.addStretch()
        layout.addLayout(hist_row)

        self.history_frame = QFrame(self)
        self.history_frame.setObjectName("SmartCard")
        self.history_frame.setVisible(False)
        hl = QVBoxLayout(self.history_frame)
        hl.setContentsMargins(16, 16, 16, 16)

        self.table = DataTable(
            ["Date", "Product", "Litres", "Rate/Litre", "Total Cost", "Supplier"],
            self, enable_delete=True
        )
        self.table.setMinimumHeight(450)
        self.table.row_delete_requested.connect(self._delete_purchase)
        hl.addWidget(self.table)
        layout.addWidget(self.history_frame)

        layout.addStretch()
        self.is_calculating = False

    def load_data(self):
        try:
            fuels = client.get("/api/fuel/types")
            self.fuel_combo.blockSignals(True)
            self.fuel_combo.clear()
            for f in fuels:
                self.fuel_combo.addItem(f["name"], f["id"])
            self.fuel_combo.blockSignals(False)
            self._on_fuel_changed()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed loading purchase data: {e}")

    def _on_fuel_changed(self):
        fuel_id = self.fuel_combo.currentData()
        if not fuel_id:
            return
        try:
            fuel_data = client.get(f"/api/fuel/types/{fuel_id}")
            self.buying_price_cache = fuel_data.get("current_purchase_price") or 0.0
        except Exception:
            self.buying_price_cache = 0.0
        self._recalculate_cost()

    def _on_litres_changed(self):
        if not self.is_calculating:
            self._recalculate_cost()

    def _on_cost_changed(self):
        if not self.is_calculating:
            self._recalculate_litres()

    def _recalculate_cost(self):
        if self.buying_price_cache <= 0:
            return
        self.is_calculating = True
        try:
            litres = float(self.litres_input.text().replace(',', '') or "0")
            self.cost_input.set_value(litres * self.buying_price_cache)
        except ValueError:
            pass
        self.is_calculating = False

    def _recalculate_litres(self):
        if self.buying_price_cache <= 0:
            return
        self.is_calculating = True
        try:
            cost = float(self.cost_input.text().replace(',', '') or "0")
            self.litres_input.set_value(cost / self.buying_price_cache)
        except ValueError:
            pass
        self.is_calculating = False

    def _toggle_history(self):
        visible = not self.history_frame.isVisible()
        self.history_frame.setVisible(visible)
        self.history_toggle.setText(
            "  📋 Hide Recent Purchases ▲" if visible else "  📋 Show Recent Purchases ▼"
        )
        if visible:
            self._refresh_table()

    def _refresh_table(self):
        try:
            purchases = client.get("/api/purchase/list")
            rows = []
            ids = []
            for p in purchases:
                rows.append((
                    p["purchase_date"],
                    p["fuel_type_name"],
                    format_litres(p["litres_purchased"]),
                    format_currency(p["price_per_litre"]),
                    format_currency(p["total_cost"]),
                    p["supplier_name"] or "-"
                ))
                ids.append(p["id"])
            self.table.populate(rows, row_ids=ids)
        except Exception as e:
            print(f"Error loading purchases: {e}")

    def _delete_purchase(self, purchase_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete", "Delete this purchase entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/purchase/entry/{purchase_id}")
            if self._toast:
                self._toast.show_message("Purchase entry deleted", "success")
            self._refresh_table()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Delete failed: {e}", "error", 5000)

    def _save_purchase(self):
        fuel_id = self.fuel_combo.currentData()
        if not fuel_id:
            return
        try:
            litres = self.litres_input.get_value()
            cost = self.cost_input.get_value()
        except ValueError:
            return

        if litres <= 0 or cost <= 0:
            if self._toast:
                self._toast.show_message("Litres and cost must be positive!", "error")
            return

        if self.buying_price_cache <= 0:
            if self._toast:
                self._toast.show_message("Set a purchase rate for this fuel first!", "error")
            return

        pdate = self.date_edit.date().toString("yyyy-MM-dd")
        supplier = self.supplier_input.text().strip()
        notes = self.notes_input.text().strip()

        try:
            client.post("/api/purchase/entry", data={
                "fuel_type_id": fuel_id,
                "purchase_date": pdate,
                "litres_purchased": litres,
                "total_cost": cost,
                "supplier_name": supplier or None,
                "notes": notes or None
            })

            if self._toast:
                self._toast.show_message(
                    f"Purchase recorded: {format_litres(litres)} for {format_currency(cost)}",
                    "success"
                )

            self.litres_input.clear_value()
            self.cost_input.clear_value()
            self.supplier_input.clear()
            self.notes_input.clear()

            if self.history_frame.isVisible():
                self._refresh_table()

        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)
