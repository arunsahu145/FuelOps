"""
Petrol Pump Finance Manager ERP — Expense Page (v2)
Full-width form, collapsible history with delete, toast notifications.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox,
    QLineEdit, QPushButton, QMessageBox, QDateEdit, QScrollArea
)
from PySide6.QtCore import Qt, QDate
from ui.components.currency_input import IndianCurrencyLineEdit
from ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY
from ui.components.data_table import DataTable
from ui.api_client import client
from utils.helpers import format_currency
from config import EXPENSE_CATEGORIES


class ExpensePage(QWidget):
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

        header_vbox = QVBoxLayout()
        title_lbl = QLabel("OPERATIONAL EXPENSES", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel("Record station outlays, utility bills, maintenance, and salaries.", self)
        sub_lbl.setObjectName("SubHeaderLabel")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(sub_lbl)
        layout.addLayout(header_vbox)

        form_frame = QFrame(self)
        form_frame.setObjectName("SmartCard")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(14)

        form_title = QLabel("RECORD EXPENSE", self)
        form_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        form_layout.addWidget(form_title)

        row = QHBoxLayout()
        row.setSpacing(16)

        d_vbox = QVBoxLayout()
        d_lbl = QLabel("DATE", self)
        d_lbl.setObjectName("FormLabel")
        d_vbox.addWidget(d_lbl)
        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        d_vbox.addWidget(self.date_edit)
        row.addLayout(d_vbox)

        c_vbox = QVBoxLayout()
        c_lbl = QLabel("CATEGORY", self)
        c_lbl.setObjectName("FormLabel")
        c_vbox.addWidget(c_lbl)
        self.category_combo = QComboBox(self)
        self.category_combo.addItems(EXPENSE_CATEGORIES)
        c_vbox.addWidget(self.category_combo)
        row.addLayout(c_vbox)

        a_vbox = QVBoxLayout()
        a_lbl = QLabel("AMOUNT (₹)", self)
        a_lbl.setObjectName("FormLabel")
        a_vbox.addWidget(a_lbl)
        self.amount_input = IndianCurrencyLineEdit(self, placeholder="₹ 0.00")
        a_vbox.addWidget(self.amount_input)
        row.addLayout(a_vbox)

        desc_vbox = QVBoxLayout()
        desc_lbl = QLabel("DESCRIPTION", self)
        desc_lbl.setObjectName("FormLabel")
        desc_vbox.addWidget(desc_lbl)
        self.desc_input = QLineEdit(self)
        self.desc_input.setPlaceholderText("e.g., Electricity bill, cleaning...")
        self.desc_input.returnPressed.connect(self._save_expense)
        desc_vbox.addWidget(self.desc_input)
        row.addLayout(desc_vbox)

        form_layout.addLayout(row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.submit_btn = QPushButton("  Save Expense Entry  ", self)
        self.submit_btn.setObjectName("ActionButton")
        self.submit_btn.clicked.connect(self._save_expense)
        btn_row.addWidget(self.submit_btn)
        form_layout.addLayout(btn_row)

        layout.addWidget(form_frame)

        QWidget.setTabOrder(self.date_edit, self.category_combo)
        QWidget.setTabOrder(self.category_combo, self.amount_input)
        QWidget.setTabOrder(self.amount_input, self.desc_input)

        # Collapsible History with delete
        hist_row = QHBoxLayout()
        self.history_toggle = QPushButton("  📋 Show Recent Expenses ▼", self)
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
            ["Date", "Category", "Amount", "Description"],
            self, enable_delete=True
        )
        self.table.row_delete_requested.connect(self._delete_expense)
        hl.addWidget(self.table)
        layout.addWidget(self.history_frame)

        layout.addStretch()

    def load_data(self):
        self.amount_input.clear_value()
        self.desc_input.clear()
        self.amount_input.setFocus()

    def _toggle_history(self):
        visible = not self.history_frame.isVisible()
        self.history_frame.setVisible(visible)
        self.history_toggle.setText(
            "  📋 Hide Recent Expenses ▲" if visible else "  📋 Show Recent Expenses ▼"
        )
        if visible:
            self._refresh_table()

    def _refresh_table(self):
        try:
            expenses = client.get("/api/expense/list")
            rows = []
            ids = []
            for e in expenses:
                rows.append((
                    e["expense_date"],
                    e["category"],
                    format_currency(e["amount"]),
                    e["description"] or "-"
                ))
                ids.append(e["id"])
            self.table.populate(rows, row_ids=ids)
        except Exception as e:
            print(f"Error loading expenses: {e}")

    def _delete_expense(self, expense_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete", "Delete this expense entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            client.delete(f"/api/expense/entry/{expense_id}")
            if self._toast:
                self._toast.show_message("Expense entry deleted", "success")
            self._refresh_table()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Delete failed: {e}", "error", 5000)

    def _save_expense(self):
        amount_val = self.amount_input.get_value()
        if amount_val <= 0:
            if self._toast:
                self._toast.show_message("Enter a positive expense amount!", "error")
            return

        amount = amount_val

        edate = self.date_edit.date().toString("yyyy-MM-dd")
        category = self.category_combo.currentText()
        desc = self.desc_input.text().strip()

        try:
            client.post("/api/expense/entry", data={
                "expense_date": edate,
                "category": category,
                "amount": amount,
                "description": desc or None
            })

            if self._toast:
                self._toast.show_message(
                    f"{category} expense saved: {format_currency(amount)}", "success"
                )

            self.amount_input.clear_value()
            self.desc_input.clear()
            self.amount_input.setFocus()

            if self.history_frame.isVisible():
                self._refresh_table()

        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)
