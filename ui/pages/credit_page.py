"""Customer credit, repayment, ledger, and aging page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit,
    QPushButton, QScrollArea, QTabWidget, QComboBox, QMessageBox, QMenu,
    QCompleter, QWidgetAction, QSizePolicy
)
from PySide6.QtCore import Qt

from ui.api_client import client
from ui.components.currency_input import IndianCurrencyLineEdit
from ui.components.data_table import DataTable
from ui.components.date_picker import DatePicker
from ui.theme import (
    ACCENT_DANGER, ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_WARNING,
    BG_SURFACE, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY
)
from utils.helpers import format_currency


class CreditPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
        self.customers = []
        self.customer_rows = []
        self.outstanding_rows = []
        self.current_ledger = []
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

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("CUSTOMER CREDIT & REPAYMENT", self)
        title.setObjectName("HeaderLabel")
        subtitle = QLabel(
            "Manage customer master records, daily credit entries, repayments, ledger, history, and aging.",
            self,
        )
        subtitle.setObjectName("SubHeaderLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        summary = QHBoxLayout()
        self.today_credit_lbl = self._summary_label("Credit Today", ACCENT_PRIMARY)
        self.outstanding_lbl = self._summary_label("Outstanding", ACCENT_DANGER)
        self.today_repay_lbl = self._summary_label("Repayment Today", ACCENT_SUCCESS)
        self.overdue_lbl = self._summary_label("Overdue Customers", ACCENT_WARNING)
        for widget in [self.today_credit_lbl, self.outstanding_lbl, self.today_repay_lbl, self.overdue_lbl]:
            summary.addWidget(widget)
        layout.addLayout(summary)

        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                background: {BG_SURFACE};
            }}
            QTabBar::tab {{
                padding: 9px 14px;
                font-weight: 600;
                color: {TEXT_SECONDARY};
            }}
            QTabBar::tab:selected {{
                color: {TEXT_PRIMARY};
                border-bottom: 2px solid {ACCENT_PRIMARY};
            }}
        """)
        layout.addWidget(self.tabs)

        self._build_customer_tab()
        self._build_credit_tab()
        self._build_repayment_tab()
        self._build_ledger_tab()
        self._build_aging_tab()

    def _summary_label(self, title: str, accent: str) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("SmartCard")
        frame.setStyleSheet(f"""
            QFrame#SmartCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-top: 3px solid {accent};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        name = QLabel(title, self)
        name.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; font-weight: 700;")
        value = QLabel("0", self)
        value.setObjectName("value")
        value.setStyleSheet(f"font-size: 18px; color: {TEXT_PRIMARY}; font-weight: 700;")
        layout.addWidget(name)
        layout.addWidget(value)
        return frame

    def _set_summary_value(self, frame: QFrame, value: str):
        frame.findChild(QLabel, "value").setText(value)

    def _build_customer_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form = QHBoxLayout()
        self.cust_name = QLineEdit(self)
        self.cust_name.setPlaceholderText("Customer Name")
        self.cust_phone = QLineEdit(self)
        self.cust_phone.setPlaceholderText("Phone Number")
        self.cust_address = QLineEdit(self)
        self.cust_address.setPlaceholderText("Address")
        add_btn = QPushButton("  + Add Customer  ", self)
        add_btn.setObjectName("SuccessButton")
        add_btn.clicked.connect(self._add_customer)
        for widget in [self.cust_name, self.cust_phone, self.cust_address, add_btn]:
            form.addWidget(widget)
        layout.addLayout(form)

        search_row = QHBoxLayout()
        search_lbl = QLabel("Search:", self)
        self.customer_search = QLineEdit(self)
        self.customer_search.setPlaceholderText("Type customer name or phone number")
        self.customer_search.textChanged.connect(self._load_customers)
        search_row.addWidget(search_lbl)
        search_row.addWidget(self.customer_search)
        layout.addLayout(search_row)

        self.customer_table = DataTable(
            ["Customer ID", "Name", "Phone", "Address", "Created", "Outstanding"], self
        )
        self.customer_table.setMinimumHeight(360)
        self.customer_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customer_table.customContextMenuRequested.connect(self._show_customer_menu)
        layout.addWidget(self.customer_table)
        self.tabs.addTab(tab, "Customer Master")

    def _build_credit_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form = QHBoxLayout()
        self.credit_customer = QComboBox(self)
        self._setup_customer_combo(self.credit_customer, "Search customer by name or phone")
        self.credit_amount = IndianCurrencyLineEdit(self, placeholder="Credit Amount")
        self.credit_date = DatePicker(self)
        self.credit_remarks = QLineEdit(self)
        self.credit_remarks.setPlaceholderText("Remarks")
        add_btn = QPushButton("  Save Credit  ", self)
        add_btn.setObjectName("SuccessButton")
        add_btn.clicked.connect(self._add_credit)
        for widget in [self.credit_customer, self.credit_amount, self.credit_date, self.credit_remarks, add_btn]:
            form.addWidget(widget)
        layout.addLayout(form)

        self.credit_table = DataTable(["Date", "Customer", "Phone", "Amount", "Remarks"], self)
        self.credit_table.setMinimumHeight(360)
        layout.addWidget(self.credit_table)
        self.tabs.addTab(tab, "Credit Entry")

    def _build_repayment_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        cust_row = QHBoxLayout()
        cust_lbl = QLabel("Outstanding Customer:", self)
        cust_lbl.setStyleSheet(f"font-weight: bold; color: {TEXT_SECONDARY}; font-size: 13px;")
        self.repay_customer = QComboBox(self)
        self._setup_customer_combo(self.repay_customer, "Search outstanding customer by name or phone")
        self.repay_customer.setMinimumWidth(400)
        self.repay_customer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cust_row.addWidget(cust_lbl)
        cust_row.addWidget(self.repay_customer)
        cust_row.addStretch()
        layout.addLayout(cust_row)

        form = QHBoxLayout()
        self.repay_amount = IndianCurrencyLineEdit(self, placeholder="Repayment Amount")
        self.repay_amount.setMinimumWidth(180)
        
        self.repay_date = DatePicker(self)
        
        self.repay_mode = QComboBox(self)
        self.repay_mode.addItems(["Cash", "Paytm", "PhonePe", "UPI", "Bank Transfer", "Cheque", "Other"])
        self.repay_mode.setMinimumWidth(150)
        
        self.repay_ref = QLineEdit(self)
        self.repay_ref.setPlaceholderText("Reference No.")
        self.repay_ref.setMinimumWidth(180)
        
        repay_btn = QPushButton("  Record Repayment  ", self)
        repay_btn.setObjectName("SuccessButton")
        repay_btn.setMinimumHeight(34)
        repay_btn.setMinimumWidth(180)
        repay_btn.clicked.connect(self._add_repayment)
        
        for widget in [self.repay_amount, self.repay_date, self.repay_mode, self.repay_ref, repay_btn]:
            form.addWidget(widget)
        layout.addLayout(form)

        self.outstanding_table = DataTable(
            ["Customer", "Phone", "Total Credit", "Paid", "Outstanding", "Status"], self
        )
        self.outstanding_table.setMinimumHeight(240)
        layout.addWidget(self.outstanding_table)

        self.payment_history_table = DataTable(
            ["Date", "Customer", "Amount", "Mode", "Reference", "Remarks"], self
        )
        self.payment_history_table.setMinimumHeight(220)
        layout.addWidget(self.payment_history_table)
        self.tabs.addTab(tab, "Repayment")

    def _build_ledger_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        row = QHBoxLayout()
        self.ledger_customer = QComboBox(self)
        self._setup_customer_combo(self.ledger_customer, "Search customer by name or phone")
        load_btn = QPushButton("  Load Ledger  ", self)
        load_btn.setObjectName("ActionButton")
        load_btn.clicked.connect(self._load_ledger)
        row.addWidget(self.ledger_customer)
        row.addWidget(load_btn)
        row.addStretch()
        layout.addLayout(row)

        filter_row = QHBoxLayout()
        self.ledger_from_date = QLineEdit(self)
        self.ledger_from_date.setPlaceholderText("From date YYYY-MM-DD")
        self.ledger_to_date = QLineEdit(self)
        self.ledger_to_date.setPlaceholderText("To date YYYY-MM-DD")
        self.ledger_min_amount = IndianCurrencyLineEdit(self, placeholder="Min Amount")
        self.ledger_type_filter = QComboBox(self)
        self.ledger_type_filter.addItems(["All Types", "Credit", "Repayment"])
        self.ledger_mode_filter = QComboBox(self)
        self.ledger_mode_filter.addItems(["All Modes", "Cash", "Paytm", "PhonePe", "UPI", "Bank Transfer", "Cheque", "Other"])
        apply_btn = QPushButton("  Apply Filters  ", self)
        apply_btn.setObjectName("ActionButton")
        apply_btn.clicked.connect(self._apply_ledger_filters)
        clear_btn = QPushButton("  Clear  ", self)
        clear_btn.clicked.connect(self._clear_ledger_filters)
        for widget in [
            self.ledger_from_date, self.ledger_to_date, self.ledger_min_amount,
            self.ledger_type_filter, self.ledger_mode_filter, apply_btn, clear_btn,
        ]:
            filter_row.addWidget(widget)
        layout.addLayout(filter_row)

        self.ledger_table = DataTable(
            ["Date", "Type", "Debit", "Credit", "Balance", "Mode", "Reference", "Remarks"], self
        )
        self.ledger_table.setMinimumHeight(430)
        layout.addWidget(self.ledger_table)
        self.tabs.addTab(tab, "Customer Ledger")

    def _setup_customer_combo(self, combo: QComboBox, placeholder: str):
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.setMinimumWidth(280)
        combo.lineEdit().setPlaceholderText(placeholder)
        completer = QCompleter(combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        combo.setCompleter(completer)

    def _build_aging_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        reload_btn = QPushButton("  Refresh Aging Report  ", self)
        reload_btn.setObjectName("ActionButton")
        reload_btn.clicked.connect(self._load_aging)
        layout.addWidget(reload_btn)
        self.aging_bucket_table = DataTable(["Bucket", "Customers", "Outstanding"], self)
        self.aging_bucket_table.setMinimumHeight(160)
        layout.addWidget(self.aging_bucket_table)
        self.aging_customer_table = DataTable(
            ["Customer", "Phone", "Oldest Unpaid", "Overdue Days", "Outstanding", "Status"], self
        )
        self.aging_customer_table.setMinimumHeight(300)
        layout.addWidget(self.aging_customer_table)
        self.tabs.addTab(tab, "Aging Report")

    def load_data(self):
        self._load_customers()
        self._load_credits()
        self._load_outstanding()
        self._load_repayments()
        self._load_summary()
        self._load_aging()

    def _load_summary(self):
        try:
            data = client.get("/api/credit/summary")
            self._set_summary_value(self.today_credit_lbl, format_currency(data.get("total_credits_given_today", 0)))
            self._set_summary_value(self.outstanding_lbl, format_currency(data.get("total_credits_outstanding", 0)))
            self._set_summary_value(self.today_repay_lbl, format_currency(data.get("total_repayment_amount_done", 0)))
            self._set_summary_value(self.overdue_lbl, str(data.get("overdue_customers", 0)))
        except Exception as e:
            print(f"Error loading credit summary: {e}")

    def _load_customers(self, *args):
        try:
            search = self.customer_search.text().strip() if hasattr(self, "customer_search") else ""
            params = {"search": search} if search else None
            self.customer_rows = client.get("/api/credit/customers", params=params)
            self.customers = client.get("/api/credit/customers")
            for combo in [self.credit_customer, self.ledger_customer]:
                self._populate_customer_combo(combo, self.customers)
            rows = [
                (
                    c["customer_code"], c["name"], c["phone"], c.get("address") or "-",
                    c["created_at"][:10], format_currency(c.get("outstanding", 0)),
                )
                for c in self.customer_rows
            ]
            self.customer_table.populate(rows, row_ids=[c["id"] for c in self.customer_rows])
        except Exception as e:
            print(f"Error loading customers: {e}")

    def _populate_customer_combo(self, combo: QComboBox, rows: list, selected_id=None):
        current_id = selected_id if selected_id is not None else combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for customer in rows:
            label = (
                f"{customer['customer_code']} - {customer['name']} | "
                f"{customer['phone']} | Due {format_currency(customer.get('outstanding', 0))}"
            )
            combo.addItem(label, customer["id"])
        if current_id:
            index = combo.findData(current_id)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)
        if combo.completer():
            combo.completer().setModel(combo.model())

    def _customer_by_id(self, customer_id: int):
        for customer in self.customers:
            if customer["id"] == customer_id:
                return customer
        for customer in self.customer_rows:
            if customer["id"] == customer_id:
                return customer
        return None

    def _set_combo_customer(self, combo: QComboBox, customer_id: int) -> bool:
        index = combo.findData(customer_id)
        if index < 0:
            return False
        combo.setCurrentIndex(index)
        return True

    def _show_customer_menu(self, pos):
        row = self.customer_table.rowAt(pos.y())
        if row < 0 or row >= len(self.customer_table._row_ids):
            return
        customer_id = self.customer_table._row_ids[row]
        customer = self._customer_by_id(customer_id)
        if not customer:
            return

        self.customer_table.selectRow(row)
        menu = QMenu(self)
        credit_action = menu.addAction("Credit Entry")
        repayment_action = menu.addAction("Repayment")
        ledger_action = menu.addAction("View Ledger")
        menu.addSeparator()
        delete_btn = QPushButton("Delete Customer", self)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                color: {ACCENT_DANGER};
                background: transparent;
                border: none;
                padding: 7px 24px;
                text-align: left;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_DANGER}20;
            }}
        """)
        delete_action = QWidgetAction(menu)
        delete_action.setDefaultWidget(delete_btn)
        menu.addAction(delete_action)
        delete_btn.clicked.connect(lambda: (menu.close(), self._delete_customer(customer_id, customer["name"])))

        action = menu.exec(self.customer_table.viewport().mapToGlobal(pos))
        if action == credit_action:
            self._open_credit_for_customer(customer_id)
        elif action == repayment_action:
            self._open_repayment_for_customer(customer)
        elif action == ledger_action:
            self._open_ledger_for_customer(customer_id)

    def _open_credit_for_customer(self, customer_id: int):
        self.tabs.setCurrentIndex(1)
        self._set_combo_customer(self.credit_customer, customer_id)
        self.credit_amount.setFocus()

    def _open_repayment_for_customer(self, customer: dict):
        self.tabs.setCurrentIndex(2)
        if not self._set_combo_customer(self.repay_customer, customer["id"]):
            if self._toast:
                self._toast.show_message("This customer has no outstanding credit", "info")
        self.repay_amount.setFocus()

    def _open_ledger_for_customer(self, customer_id: int):
        self.tabs.setCurrentIndex(3)
        self._set_combo_customer(self.ledger_customer, customer_id)
        self._load_ledger()

    def _delete_customer(self, customer_id: int, customer_name: str):
        reply = QMessageBox.question(
            self,
            "Delete Customer",
            f"Delete customer '{customer_name}'?\n\nCustomers with outstanding credit cannot be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/credit/customers/{customer_id}")
            if self._toast:
                self._toast.show_message("Customer deleted", "success")
            self.load_data()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Delete failed: {e}", "error", 5000)

    def _load_credits(self):
        try:
            credits = client.get("/api/credit/credits")
            self.credit_table.populate([
                (
                    c["credit_date"], c["customer_name"], c["phone"],
                    format_currency(c["amount"]), c.get("remarks") or "-",
                )
                for c in credits
            ])
        except Exception as e:
            print(f"Error loading credits: {e}")

    def _load_outstanding(self, *args):
        try:
            self.outstanding_rows = client.get("/api/credit/outstanding")
            self.repay_customer.blockSignals(True)
            self.repay_customer.clear()
            for row in self.outstanding_rows:
                self.repay_customer.addItem(
                    (
                        f"{row['customer_code']} - {row['customer_name']} | "
                        f"{row['phone']} | Due {format_currency(row['outstanding'])}"
                    ),
                    row["customer_id"],
                )
            self.repay_customer.blockSignals(False)
            if self.repay_customer.completer():
                self.repay_customer.completer().setModel(self.repay_customer.model())
            self.outstanding_table.populate([
                (
                    r["customer_name"], r["phone"], format_currency(r["total_credit"]),
                    format_currency(r["total_repaid"]), format_currency(r["outstanding"]), r["status"],
                )
                for r in self.outstanding_rows
            ])
        except Exception as e:
            print(f"Error loading outstanding customers: {e}")

    def _load_repayments(self):
        try:
            repayments = client.get("/api/credit/repayments")
            self.payment_history_table.populate([
                (
                    r["repayment_date"], r["customer_name"], format_currency(r["amount"]),
                    r["mode"], r.get("reference_number") or "-", r.get("remarks") or "-",
                )
                for r in repayments
            ])
        except Exception as e:
            print(f"Error loading repayments: {e}")

    def _load_ledger(self):
        customer_id = self.ledger_customer.currentData()
        if not customer_id:
            return
        try:
            ledger = client.get(f"/api/credit/ledger/{customer_id}")
            self.current_ledger = ledger
            self._populate_ledger_table(ledger)
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Ledger error: {e}", "error", 5000)

    def _populate_ledger_table(self, ledger: list):
        self.ledger_table.populate([
                (
                    e["entry_date"], e["entry_type"], format_currency(e["debit"]),
                    format_currency(e["credit"]), format_currency(e["balance"]),
                    e.get("mode") or "-", e.get("reference_number") or "-", e.get("remarks") or "-",
                )
                for e in ledger
        ])

    def _apply_ledger_filters(self):
        from_date = self.ledger_from_date.text().strip()
        to_date = self.ledger_to_date.text().strip()
        min_amount = self.ledger_min_amount.get_value()
        selected_type = self.ledger_type_filter.currentText()
        selected_mode = self.ledger_mode_filter.currentText()

        filtered = []
        for entry in self.current_ledger:
            entry_date = entry["entry_date"]
            if from_date and entry_date < from_date:
                continue
            if to_date and entry_date > to_date:
                continue
            if selected_type != "All Types" and entry["entry_type"] != selected_type:
                continue
            if selected_mode != "All Modes" and entry.get("mode") != selected_mode:
                continue
            amount = entry.get("debit", 0) if entry["entry_type"] == "Credit" else entry.get("credit", 0)
            if min_amount > 0 and amount < min_amount:
                continue
            filtered.append(entry)
        self._populate_ledger_table(filtered)

    def _clear_ledger_filters(self):
        self.ledger_from_date.clear()
        self.ledger_to_date.clear()
        self.ledger_min_amount.clear_value()
        self.ledger_type_filter.setCurrentIndex(0)
        self.ledger_mode_filter.setCurrentIndex(0)
        self._populate_ledger_table(self.current_ledger)

    def _load_aging(self):
        try:
            data = client.get("/api/credit/aging")
            self.aging_bucket_table.populate([
                (b["bucket"], b["customer_count"], format_currency(b["outstanding"]))
                for b in data.get("buckets", [])
            ])
            self.aging_customer_table.populate([
                (
                    c["customer_name"], c["phone"], c.get("oldest_unpaid_date") or "-",
                    c["overdue_days"], format_currency(c["outstanding"]), c["status"],
                )
                for c in data.get("customers", [])
            ])
        except Exception as e:
            print(f"Error loading aging: {e}")

    def _add_customer(self):
        name = self.cust_name.text().strip()
        phone = self.cust_phone.text().strip()
        address = self.cust_address.text().strip()
        if not name or not phone:
            if self._toast:
                self._toast.show_message("Customer name and phone are required", "error")
            return
        try:
            client.post("/api/credit/customers", data={"name": name, "phone": phone, "address": address or None})
            self.cust_name.clear()
            self.cust_phone.clear()
            self.cust_address.clear()
            if self._toast:
                self._toast.show_message("Customer added", "success")
            self.load_data()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Customer error: {e}", "error", 5000)

    def _add_credit(self):
        customer_id = self.credit_customer.currentData()
        amount = self.credit_amount.get_value()
        if not customer_id or amount <= 0:
            if self._toast:
                self._toast.show_message("Select customer and enter credit amount", "error")
            return
        try:
            client.post("/api/credit/credits", data={
                "customer_id": customer_id,
                "credit_date": self.credit_date.get_date_str(),
                "amount": amount,
                "remarks": self.credit_remarks.text().strip() or None,
            })
            self.credit_amount.clear_value()
            self.credit_remarks.clear()
            if self._toast:
                self._toast.show_message("Credit entry saved", "success")
            self.load_data()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Credit error: {e}", "error", 5000)

    def _add_repayment(self):
        customer_id = self.repay_customer.currentData()
        amount = self.repay_amount.get_value()
        if not customer_id or amount <= 0:
            if self._toast:
                self._toast.show_message("Select customer and enter repayment amount", "error")
            return
        try:
            client.post("/api/credit/repayments", data={
                "customer_id": customer_id,
                "repayment_date": self.repay_date.get_date_str(),
                "amount": amount,
                "mode": self.repay_mode.currentText(),
                "reference_number": self.repay_ref.text().strip() or None,
                "remarks": None,
            })
            self.repay_amount.clear_value()
            self.repay_ref.clear()
            if self._toast:
                self._toast.show_message("Repayment recorded", "success")
            self.load_data()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Repayment error: {e}", "error", 5000)
