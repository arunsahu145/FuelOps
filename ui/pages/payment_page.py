"""
Petrol Pump Finance Manager ERP — Collections Page (v4)
Shift-wise layout: All 4 payment methods listed inline per shift.
Commission entry for expected cash adjustment.
Collapsible history with delete support. Toast notifications.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QMessageBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from ui.components.currency_input import IndianCurrencyLineEdit
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_SUCCESS,
    ACCENT_WARNING, BG_MAIN, BG_SURFACE, BG_SURFACE_LIGHT, BORDER_COLOR
)
from ui.components.date_picker import DatePicker
from ui.components.data_table import DataTable
from ui.api_client import client
from utils.helpers import format_currency

PAYMENT_METHODS = ["Cash", "Paytm", "PhonePe", "CCMS"]
METHOD_ICONS = {
    "Cash": "💵",
    "Paytm": "📱",
    "PhonePe": "📲",
    "CCMS": "🏢",
}
METHOD_COLORS = {
    "Cash": "#10b981",
    "Paytm": "#3b82f6",
    "PhonePe": "#a855f7",
    "CCMS": "#f59e0b",
}

COMMISSION_COLOR = "#ec4899"  # Pink accent for commission


class PaymentMethodRow(QFrame):
    """A single payment method row with icon, label, amount input, and save status."""

    def __init__(self, method_name: str, parent=None):
        super().__init__(parent)
        self.method_name = method_name
        self.is_saved = False
        self.saved_amount = 0.0
        self.record_id = None  # For delete support
        self._init_ui()

    def _init_ui(self):
        color = METHOD_COLORS.get(self.method_name, ACCENT_PRIMARY)
        icon = METHOD_ICONS.get(self.method_name, "💳")

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
        """)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Icon + Method name
        icon_lbl = QLabel(icon, self)
        icon_lbl.setFixedWidth(24)
        icon_lbl.setStyleSheet("font-size: 18px; border: none;")
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(self.method_name, self)
        name_lbl.setFixedWidth(80)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {color}; border: none;")
        layout.addWidget(name_lbl)

        # Amount input
        self.amount_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.amount_input.setFixedWidth(160)
        self.amount_input.setFixedHeight(34)
        self.amount_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_MAIN};
                border: 1.5px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 10px;
                color: {TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 600;
                font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{
                border-color: {color};
                background-color: {BG_SURFACE};
            }}
        """)
        layout.addWidget(self.amount_input)

        # Status label (shows saved amount or nothing)
        self.status_lbl = QLabel("", self)
        self.status_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; border: none;")
        layout.addWidget(self.status_lbl)

        layout.addStretch()

    def get_amount(self) -> float:
        return self.amount_input.get_value()

    def set_saved(self, amount: float, record_id: int):
        """Mark this row as already saved."""
        self.is_saved = True
        self.saved_amount = amount
        self.record_id = record_id
        self.amount_input.set_value(amount)
        self.amount_input.setReadOnly(True)
        color = METHOD_COLORS.get(self.method_name, ACCENT_PRIMARY)
        self.amount_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_SURFACE_LIGHT}40;
                border: 1px solid {ACCENT_SUCCESS}60;
                border-radius: 6px;
                padding: 4px 10px;
                color: {TEXT_SECONDARY};
                font-size: 14px;
                font-weight: 600;
                font-family: 'Consolas', monospace;
            }}
        """)
        self.status_lbl.setText(f"✓ {format_currency(amount)}")
        self.status_lbl.setStyleSheet(f"font-size: 12px; color: {ACCENT_SUCCESS}; font-weight: 600; border: none;")

    def reset(self):
        """Reset to editable state."""
        self.is_saved = False
        self.saved_amount = 0.0
        self.record_id = None
        self.amount_input.clear()
        self.amount_input.setReadOnly(False)
        color = METHOD_COLORS.get(self.method_name, ACCENT_PRIMARY)
        self.amount_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_MAIN};
                border: 1.5px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 10px;
                color: {TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 600;
                font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{
                border-color: {color};
                background-color: {BG_SURFACE};
            }}
        """)
        self.status_lbl.setText("")
        self.status_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; border: none;")


class ShiftPaymentSection(QFrame):
    """A shift section containing all 4 payment methods with inline inputs."""

    def __init__(self, shift_number: int, parent_page=None, parent=None):
        super().__init__(parent)
        self.shift_number = shift_number
        self.parent_page = parent_page
        self.method_rows = {}
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("SmartCard")
        shift_color = ACCENT_PRIMARY if self.shift_number == 1 else ACCENT_WARNING
        self.setStyleSheet(f"""
            QFrame#SmartCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        indicator = QLabel("●", self)
        indicator.setStyleSheet(f"font-size: 14px; color: {shift_color};")
        header.addWidget(indicator)

        title = QLabel(f"SHIFT {self.shift_number}", self)
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY}; letter-spacing: 0.5px;")
        header.addWidget(title)

        time_lbl = QLabel(
            "(8 AM – 7 PM)" if self.shift_number == 1 else "(7 PM – 8 AM)", self
        )
        time_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; padding-top: 3px;")
        header.addWidget(time_lbl)

        header.addStretch()

        # Shift total label
        self.shift_total = QLabel("Total: ₹0.00", self)
        self.shift_total.setStyleSheet(f"""
            font-size: 13px; font-weight: bold; color: {shift_color};
            background-color: {shift_color}15;
            padding: 4px 12px; border-radius: 6px;
        """)
        header.addWidget(self.shift_total)

        save_btn = QPushButton(f"  Save Shift {self.shift_number}  ", self)
        save_btn.setObjectName("SuccessButton")
        save_btn.clicked.connect(self._save_shift)
        header.addWidget(save_btn)

        outer.addLayout(header)

        # Payment method rows
        for method in PAYMENT_METHODS:
            row = PaymentMethodRow(method, self)
            row.amount_input.textChanged.connect(self._update_total)
            self.method_rows[method] = row
            outer.addWidget(row)

        # Set tab order between method inputs
        inputs = [self.method_rows[m].amount_input for m in PAYMENT_METHODS]
        for i in range(len(inputs) - 1):
            QWidget.setTabOrder(inputs[i], inputs[i + 1])

    def _update_total(self):
        total = sum(row.get_amount() for row in self.method_rows.values())
        shift_color = ACCENT_PRIMARY if self.shift_number == 1 else ACCENT_WARNING
        self.shift_total.setText(f"Total: {format_currency(total)}")

    def load_existing_entries(self, payments: list):
        """Load already-saved payment entries for this shift."""
        # Reset all rows first
        for row in self.method_rows.values():
            row.reset()

        for p in payments:
            if p.get("shift_number") == self.shift_number:
                method = p["payment_method"]
                if method in self.method_rows:
                    self.method_rows[method].set_saved(p["amount"], p["id"])

        self._update_total()

    def _save_shift(self):
        """Save all non-zero, non-saved payment entries for this shift."""
        toast = self.parent_page._toast if self.parent_page else None
        date_str = self.parent_page.date_picker.get_date_str() if self.parent_page else None
        if not date_str:
            return

        saved = 0
        errors = 0

        for method, row in self.method_rows.items():
            if row.is_saved:
                continue
            amount = row.get_amount()
            if amount <= 0:
                continue

            try:
                resp = client.post("/api/payment/entry", data={
                    "payment_date": date_str,
                    "shift_number": self.shift_number,
                    "payment_method": method,
                    "amount": amount,
                    "notes": None
                })
                row.set_saved(amount, resp["id"])
                saved += 1
            except Exception as e:
                errors += 1
                if toast:
                    toast.show_message(f"{method}: {e}", "error", 4000)

        if toast:
            if saved > 0 and errors == 0:
                toast.show_message(
                    f"Shift {self.shift_number}: {saved} payment(s) saved ✓", "success"
                )
            elif saved > 0:
                toast.show_message(
                    f"Shift {self.shift_number}: {saved} saved, {errors} error(s)", "warning"
                )
            elif errors == 0:
                toast.show_message(
                    f"Shift {self.shift_number}: No new amounts to save", "info"
                )

        self._update_total()

        # Refresh history if visible
        if self.parent_page and self.parent_page.history_frame.isVisible():
            self.parent_page._refresh_table()


class PaymentPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
        self._commission_record_id = None
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

        # Header with date picker
        header = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_lbl = QLabel("COLLECTIONS", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel(
            "Record Cash, UPI & CCMS collections per shift. All methods listed — enter amounts and save.",
            self
        )
        sub_lbl.setObjectName("SubHeaderLabel")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header.addLayout(title_vbox)
        header.addStretch()

        self.date_picker = DatePicker(self)
        self.date_picker.date_changed.connect(self._on_date_changed)
        header.addWidget(self.date_picker)
        layout.addLayout(header)

        # ── Commission Section ──
        comm_frame = QFrame(self)
        comm_frame.setObjectName("CommissionCard")
        comm_frame.setStyleSheet(f"""
            QFrame#CommissionCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-left: 4px solid {COMMISSION_COLOR};
                border-radius: 12px;
            }}
        """)
        comm_layout = QHBoxLayout(comm_frame)
        comm_layout.setContentsMargins(20, 14, 20, 14)
        comm_layout.setSpacing(16)

        comm_icon = QLabel("💰", self)
        comm_icon.setStyleSheet("font-size: 22px;")
        comm_layout.addWidget(comm_icon)

        comm_title_vbox = QVBoxLayout()
        comm_title_vbox.setSpacing(2)
        comm_title = QLabel("COMMISSION", self)
        comm_title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COMMISSION_COLOR}; "
            f"letter-spacing: 0.5px;"
        )
        comm_subtitle = QLabel(
            "Extra cash received (added to expected cash collection)", self
        )
        comm_subtitle.setStyleSheet(
            f"font-size: 10px; color: {TEXT_SECONDARY};"
        )
        comm_title_vbox.addWidget(comm_title)
        comm_title_vbox.addWidget(comm_subtitle)
        comm_layout.addLayout(comm_title_vbox)

        comm_layout.addStretch()

        self.commission_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        self.commission_input.setFixedWidth(180)
        self.commission_input.setFixedHeight(36)
        self.commission_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_MAIN};
                border: 1.5px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 10px;
                color: {TEXT_PRIMARY};
                font-size: 15px;
                font-weight: 600;
                font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{
                border-color: {COMMISSION_COLOR};
                background-color: {BG_SURFACE};
            }}
        """)
        comm_layout.addWidget(self.commission_input)

        self.commission_status = QLabel("", self)
        self.commission_status.setStyleSheet(
            f"font-size: 12px; color: {TEXT_SECONDARY};"
        )
        comm_layout.addWidget(self.commission_status)

        self.commission_save_btn = QPushButton("  Save  ", self)
        self.commission_save_btn.setObjectName("SuccessButton")
        self.commission_save_btn.setFixedHeight(36)
        self.commission_save_btn.clicked.connect(self._save_commission)
        comm_layout.addWidget(self.commission_save_btn)

        layout.addWidget(comm_frame)

        # Shift 1 Section
        self.shift1_section = ShiftPaymentSection(1, parent_page=self, parent=self)
        layout.addWidget(self.shift1_section)

        # Shift 2 Section
        self.shift2_section = ShiftPaymentSection(2, parent_page=self, parent=self)
        layout.addWidget(self.shift2_section)

        # Collapsible History with delete
        hist_row = QHBoxLayout()
        self.history_toggle = QPushButton("  📋 Show Collection Log ▼", self)
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
            ["Date", "Shift", "Payment Mode", "Amount"],
            self, enable_delete=True
        )
        self.table.setMinimumHeight(450)
        self.table.row_delete_requested.connect(self._delete_payment)
        hl.addWidget(self.table)
        layout.addWidget(self.history_frame)

        layout.addStretch()

    # ── Commission Methods ──

    def _save_commission(self):
        """Save or update the commission entry for the selected date."""
        amount = self.commission_input.get_value()
        date_str = self.date_picker.get_date_str()

        if amount <= 0:
            if self._toast:
                self._toast.show_message("Enter a positive commission amount!", "error")
            return

        try:
            # If there's already a commission for this date, delete it first
            if self._commission_record_id is not None:
                client.delete(f"/api/payment/entry/{self._commission_record_id}")

            resp = client.post("/api/payment/entry", data={
                "payment_date": date_str,
                "shift_number": None,
                "payment_method": "Commission",
                "amount": amount,
                "notes": "Commission added to expected cash"
            })
            self._commission_record_id = resp["id"]
            self._set_commission_saved(amount)

            if self._toast:
                self._toast.show_message(
                    f"Commission saved: {format_currency(amount)}", "success"
                )
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error saving commission: {e}", "error", 5000)

    def _set_commission_saved(self, amount: float):
        """Mark commission input as saved."""
        self.commission_input.set_value(amount)
        self.commission_input.setReadOnly(True)
        self.commission_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_SURFACE_LIGHT}40;
                border: 1px solid {ACCENT_SUCCESS}60;
                border-radius: 6px;
                padding: 4px 10px;
                color: {TEXT_SECONDARY};
                font-size: 15px;
                font-weight: 600;
                font-family: 'Consolas', monospace;
            }}
        """)
        self.commission_status.setText(f"✓ {format_currency(amount)}")
        self.commission_status.setStyleSheet(
            f"font-size: 12px; color: {ACCENT_SUCCESS}; font-weight: 600;"
        )
        self.commission_save_btn.setText("  Saved ✓  ")

    def _reset_commission(self):
        """Reset commission input to editable state."""
        self._commission_record_id = None
        self.commission_input.clear()
        self.commission_input.setReadOnly(False)
        self.commission_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_MAIN};
                border: 1.5px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 10px;
                color: {TEXT_PRIMARY};
                font-size: 15px;
                font-weight: 600;
                font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{
                border-color: {COMMISSION_COLOR};
                background-color: {BG_SURFACE};
            }}
        """)
        self.commission_status.setText("")
        self.commission_status.setStyleSheet(
            f"font-size: 12px; color: {TEXT_SECONDARY};"
        )
        self.commission_save_btn.setText("  Save  ")

    def _load_commission(self, payments: list):
        """Load existing commission entry for the selected date."""
        self._reset_commission()
        for p in payments:
            if p.get("payment_method") == "Commission":
                self._commission_record_id = p["id"]
                self._set_commission_saved(p["amount"])
                break

    # ── Data Loading ──

    def load_data(self):
        """Load existing payment entries for the selected date into shift sections."""
        date_str = self.date_picker.get_date_str()
        try:
            payments = client.get("/api/payment/list", params={
                "start_date": date_str,
                "end_date": date_str
            })
            # Filter out commission for shift loading
            regular_payments = [p for p in payments if p.get("payment_method") != "Commission"]
            self.shift1_section.load_existing_entries(regular_payments)
            self.shift2_section.load_existing_entries(regular_payments)
            # Load commission separately
            self._load_commission(payments)
        except Exception as e:
            print(f"Error loading payments: {e}")

    def _on_date_changed(self):
        self.load_data()
        if self.history_frame.isVisible():
            self._refresh_table()

    def _toggle_history(self):
        visible = not self.history_frame.isVisible()
        self.history_frame.setVisible(visible)
        self.history_toggle.setText(
            "  📋 Hide Collection Log ▲" if visible else "  📋 Show Collection Log ▼"
        )
        if visible:
            self._refresh_table()

    def _refresh_table(self):
        """Show collection log — excludes commission entries."""
        date_str = self.date_picker.get_date_str()
        try:
            payments = client.get("/api/payment/list", params={
                "start_date": date_str,
                "end_date": date_str
            })
            rows = []
            ids = []
            for p in payments:
                # Skip commission entries from collection log
                if p.get("payment_method") == "Commission":
                    continue
                shift_text = f"Shift {p['shift_number']}" if p.get('shift_number') else "-"
                rows.append((
                    p["payment_date"],
                    shift_text,
                    p["payment_method"],
                    format_currency(p["amount"]),
                ))
                ids.append(p["id"])
            self.table.populate(rows, row_ids=ids)
        except Exception as e:
            print(f"Error loading payments: {e}")

    def _delete_payment(self, payment_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete", "Delete this payment entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/payment/entry/{payment_id}")
            if self._toast:
                self._toast.show_message("Payment entry deleted", "success")
            self.load_data()  # Reload shift sections
            if self.history_frame.isVisible():
                self._refresh_table()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Delete failed: {e}", "error", 5000)
