"""
Petrol Pump Finance Manager ERP — Tank Stock Page (Improved)
Full-width form, toast notifications, cleaner UX.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox,
    QLineEdit, QPushButton, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_SUCCESS
from ui.components.data_table import DataTable
from ui.api_client import client
from utils.helpers import format_litres


class TankPage(QWidget):
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
        layout.setSpacing(20)

        # ── Header ──
        header_vbox = QVBoxLayout()
        title_lbl = QLabel("TANK STOCK MONITOR", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel("Live tank volumes. Reconcile with dip-stick calibrations.", self)
        sub_lbl.setObjectName("SubHeaderLabel")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(sub_lbl)
        layout.addLayout(header_vbox)

        # ── Current Stock Table (always visible) ──
        table_frame = QFrame(self)
        table_frame.setObjectName("SmartCard")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 16, 16, 16)
        table_layout.setSpacing(12)

        table_title = QLabel("CURRENT TANK VOLUMES", self)
        table_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        table_layout.addWidget(table_title)

        self.table = DataTable(["Fuel Tank", "Current Stock (Litres)", "Last Updated"], self)
        self.table.setMaximumHeight(180)
        table_layout.addWidget(self.table)

        layout.addWidget(table_frame)

        # ── Reconciliation Form (horizontal) ──
        form_frame = QFrame(self)
        form_frame.setObjectName("SmartCard")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 16, 20, 16)
        form_layout.setSpacing(12)

        form_title = QLabel("RECONCILE / CALIBRATE TANK", self)
        form_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        form_layout.addWidget(form_title)

        row = QHBoxLayout()
        row.setSpacing(16)

        f_vbox = QVBoxLayout()
        fuel_lbl = QLabel("FUEL TANK", self)
        fuel_lbl.setObjectName("FormLabel")
        f_vbox.addWidget(fuel_lbl)
        self.fuel_combo = QComboBox(self)
        f_vbox.addWidget(self.fuel_combo)
        row.addLayout(f_vbox)

        l_vbox = QVBoxLayout()
        litres_lbl = QLabel("ACTUAL CALIBRATED LITRES", self)
        litres_lbl.setObjectName("FormLabel")
        l_vbox.addWidget(litres_lbl)
        self.litres_input = QLineEdit(self)
        self.litres_input.setPlaceholderText("0.00 L")
        self.litres_input.setValidator(QDoubleValidator(0.0, 999999.9, 2, self))
        self.litres_input.returnPressed.connect(self._reconcile_tank)
        l_vbox.addWidget(self.litres_input)
        row.addLayout(l_vbox)

        self.submit_btn = QPushButton("  Reconcile  ", self)
        self.submit_btn.setObjectName("SuccessButton")
        self.submit_btn.clicked.connect(self._reconcile_tank)
        row.addWidget(self.submit_btn, alignment=Qt.AlignBottom)

        row.addStretch()
        form_layout.addLayout(row)

        layout.addWidget(form_frame)
        layout.addStretch()

    def load_data(self):
        try:
            fuels = client.get("/api/fuel/types")
            self.fuel_combo.blockSignals(True)
            self.fuel_combo.clear()
            for f in fuels:
                self.fuel_combo.addItem(f["name"], f["id"])
            self.fuel_combo.blockSignals(False)
            self._refresh_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed loading tank data: {e}")

    def _refresh_table(self):
        try:
            stocks = client.get("/api/tank/stock")
            rows = []
            for s in stocks:
                rows.append((
                    s["fuel_type_name"],
                    format_litres(s["current_stock_litres"]),
                    s["last_updated"] or "Never"
                ))
            self.table.populate(rows)
        except Exception as e:
            print(f"Error loading tank stocks: {e}")

    def _reconcile_tank(self):
        fuel_id = self.fuel_combo.currentData()
        if not fuel_id:
            return

        litres_text = self.litres_input.text().strip()
        if not litres_text:
            if self._toast:
                self._toast.show_message("Enter calibrated litres!", "error")
            return

        try:
            litres = float(litres_text)
        except ValueError:
            return

        if litres < 0:
            if self._toast:
                self._toast.show_message("Volume cannot be negative!", "error")
            return

        try:
            client.post(f"/api/tank/reconcile/{fuel_id}?litres={litres}")

            fuel_name = self.fuel_combo.currentText()
            if self._toast:
                self._toast.show_message(
                    f"{fuel_name} tank reconciled to {format_litres(litres)}", "success"
                )

            self.litres_input.clear()
            self._refresh_table()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)
