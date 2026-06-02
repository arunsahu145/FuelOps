"""
Petrol Pump Finance Manager ERP — Employee Management Page
Add, view, edit, and delete employees with name, age, phone, and salary.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit,
    QPushButton, QMessageBox, QScrollArea, QGridLayout, QSizePolicy,
    QSpinBox, QMenu, QDialog, QDialogButtonBox, QDateEdit, QFormLayout,
    QWidgetAction
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_SUCCESS,
    ACCENT_DANGER, ACCENT_WARNING, BG_SURFACE, BG_SURFACE_LIGHT, BORDER_COLOR
)
from ui.components.data_table import DataTable
from ui.components.currency_input import IndianCurrencyLineEdit
from ui.api_client import client
from utils.helpers import format_currency


class SalaryPaymentDialog(QDialog):
    def __init__(self, employee_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Pay Salary - {employee_name}")
        self.setModal(True)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.amount_input = IndianCurrencyLineEdit(self, placeholder="₹ Amount paid")
        self.amount_input.setMinimumWidth(220)
        form.addRow("Amount", self.amount_input)

        self.date_input = QDateEdit(self)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(QDate.currentDate())
        form.addRow("Date", self.date_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def amount(self) -> float:
        return self.amount_input.get_value()

    def paid_date(self) -> str:
        return self.date_input.date().toString("yyyy-MM-dd")


class EmployeePage(QWidget):
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
        title_lbl = QLabel("EMPLOYEE MANAGEMENT", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel(
            "Manage employee records and record salary payments from the employee list.",
            self
        )
        sub_lbl.setObjectName("SubHeaderLabel")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header.addLayout(title_vbox)
        header.addStretch()
        layout.addLayout(header)

        # ── Summary Cards ──
        summary_grid = QHBoxLayout()
        summary_grid.setSpacing(12)

        self.card_total_emp = self._make_stat_card("TOTAL EMPLOYEES", "0", ACCENT_PRIMARY)
        self.card_active = self._make_stat_card("ACTIVE EMPLOYEES", "0", ACCENT_SUCCESS)

        summary_grid.addWidget(self.card_total_emp)
        summary_grid.addWidget(self.card_active)

        layout.addLayout(summary_grid)

        # ── Add Employee Form ──
        form_frame = QFrame(self)
        form_frame.setObjectName("SmartCard")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        form_title = QLabel("ADD NEW EMPLOYEE", self)
        form_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; "
            f"letter-spacing: 0.5px;"
        )
        form_layout.addWidget(form_title)

        # Form fields row
        fields_row = QHBoxLayout()
        fields_row.setSpacing(12)

        # Name
        name_vbox = QVBoxLayout()
        name_lbl = QLabel("NAME *", self)
        name_lbl.setObjectName("FormLabel")
        name_vbox.addWidget(name_lbl)
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Employee full name")
        self.name_input.setMinimumWidth(180)
        name_vbox.addWidget(self.name_input)
        fields_row.addLayout(name_vbox)

        # Age
        age_vbox = QVBoxLayout()
        age_lbl = QLabel("AGE", self)
        age_lbl.setObjectName("FormLabel")
        age_vbox.addWidget(age_lbl)
        self.age_input = QSpinBox(self)
        self.age_input.setRange(16, 80)
        self.age_input.setValue(25)
        self.age_input.setMinimumWidth(80)
        age_vbox.addWidget(self.age_input)
        fields_row.addLayout(age_vbox)

        # Phone
        phone_vbox = QVBoxLayout()
        phone_lbl = QLabel("PHONE", self)
        phone_lbl.setObjectName("FormLabel")
        phone_vbox.addWidget(phone_lbl)
        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText("10-digit mobile")
        self.phone_input.setMinimumWidth(140)
        phone_vbox.addWidget(self.phone_input)
        fields_row.addLayout(phone_vbox)

        # Add Button
        btn_vbox = QVBoxLayout()
        btn_vbox.addSpacing(18)  # align with inputs
        self.add_btn = QPushButton("  + Add Employee  ", self)
        self.add_btn.setObjectName("SuccessButton")
        self.add_btn.setMinimumHeight(36)
        self.add_btn.clicked.connect(self._add_employee)
        btn_vbox.addWidget(self.add_btn)
        fields_row.addLayout(btn_vbox)

        fields_row.addStretch()
        form_layout.addLayout(fields_row)
        layout.addWidget(form_frame)

        # ── Employee Table ──
        table_frame = QFrame(self)
        table_frame.setObjectName("SmartCard")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 16, 16, 16)
        table_layout.setSpacing(10)

        table_title = QLabel("ALL EMPLOYEES", self)
        table_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; "
            f"letter-spacing: 0.5px;"
        )
        table_layout.addWidget(table_title)

        self.table = DataTable(
            ["Name", "Age", "Phone", "Status"],
            self
        )
        self.table.setMinimumHeight(450)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_employee_menu)
        self.table.viewport().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.viewport().customContextMenuRequested.connect(self._show_employee_menu)
        table_layout.addWidget(self.table)

        layout.addWidget(table_frame)
        layout.addStretch()

    def _make_stat_card(self, label: str, value: str, accent: str) -> QFrame:
        """Create a compact stat card."""
        card = QFrame(self)
        card.setObjectName("ReportMetric")
        card.setStyleSheet(f"""
            QFrame#ReportMetric {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-top: 3px solid {accent};
                border-radius: 8px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(85)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 10, 14, 10)
        cl.setSpacing(4)

        lbl = QLabel(label, card)
        lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {TEXT_SECONDARY}; "
            f"letter-spacing: 0.5px;"
        )
        cl.addWidget(lbl)

        val_lbl = QLabel(value, card)
        val_lbl.setObjectName("StatValue")
        val_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {TEXT_PRIMARY}; "
            f"font-family: 'Consolas', monospace;"
        )
        cl.addWidget(val_lbl)
        cl.addStretch()

        card._value_label = val_lbl
        return card

    def _update_card(self, card, value: str):
        card._value_label.setText(value)

    # ── Data Loading ──

    def load_data(self):
        """Called when page is navigated to."""
        self._refresh_table()

    def _refresh_table(self):
        try:
            employees = client.get("/api/employees", params={"active_only": False})
            rows = []
            ids = []
            active_count = 0

            for e in employees:
                status = "✅ Active" if e["is_active"] else "❌ Inactive"
                rows.append((
                    e["name"],
                    str(e.get("age") or "-"),
                    e.get("phone") or "-",
                    status,
                ))
                ids.append(e["id"])
                if e["is_active"]:
                    active_count += 1

            self.table.populate(rows, row_ids=ids)

            # Update summary cards
            self._update_card(self.card_total_emp, str(len(employees)))
            self._update_card(self.card_active, str(active_count))

        except Exception as e:
            print(f"Error loading employees: {e}")

    # ── CRUD Operations ──

    def _add_employee(self):
        name = self.name_input.text().strip()
        age = self.age_input.value()
        phone = self.phone_input.text().strip()

        if not name:
            if self._toast:
                self._toast.show_message("Employee name is required!", "error")
            return

        try:
            client.post("/api/employees", data={
                "name": name,
                "age": age,
                "phone": phone or None,
            })

            # Clear form
            self.name_input.clear()
            self.age_input.setValue(25)
            self.phone_input.clear()

            if self._toast:
                self._toast.show_message(f"Employee '{name}' added!", "success")
            self._refresh_table()

        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _show_employee_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self.table._row_ids):
            return

        employee_id = self.table._row_ids[row]
        name_item = self.table.item(row, 0)
        employee_name = name_item.text() if name_item else "Employee"

        menu = QMenu(self)
        pay_action = QAction("Pay Salary", menu)
        menu.addAction(pay_action)
        menu.addSeparator()
        remove_action = QWidgetAction(menu)
        remove_btn = QPushButton("Remove Employee", menu)
        remove_btn.setFlat(True)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                color: {ACCENT_DANGER};
                background: transparent;
                border: none;
                text-align: left;
                padding: 7px 26px 7px 12px;
            }}
            QPushButton:hover {{
                background-color: {BG_SURFACE_LIGHT};
            }}
        """)
        remove_action.setDefaultWidget(remove_btn)
        menu.addAction(remove_action)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 7px 26px 7px 12px;
            }}
            QMenu::item:selected {{
                background-color: {BG_SURFACE_LIGHT};
            }}
        """)

        selected = {"remove": False}
        remove_btn.clicked.connect(lambda: (selected.__setitem__("remove", True), menu.close()))

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == pay_action:
            self._pay_salary(employee_id, employee_name)
        elif selected["remove"]:
            self._delete_employee(employee_id)

    def _pay_salary(self, employee_id: int, employee_name: str):
        dialog = SalaryPaymentDialog(employee_name, self)
        if dialog.exec() != QDialog.Accepted:
            return

        amount = dialog.amount()
        if amount <= 0:
            if self._toast:
                self._toast.show_message("Enter a valid salary amount!", "error")
            return

        try:
            result = client.post(
                f"/api/employees/{employee_id}/salary-payments",
                data={
                    "amount": amount,
                    "paid_date": dialog.paid_date(),
                }
            )
            if self._toast:
                self._toast.show_message(
                    f"Salary paid to {result.get('employee_name', employee_name)}: "
                    f"{format_currency(result.get('amount', amount))}",
                    "success"
                )
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _delete_employee(self, employee_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this employee?\n"
            "This will NOT remove existing salary entries in reports.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/employees/{employee_id}")
            if self._toast:
                self._toast.show_message("Employee deleted", "success")
            self._refresh_table()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)
