"""
Petrol Pump Finance Manager ERP — Login Page
Sleek, centered premium login interface with rich animations and validation.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from ui.api_client import client
from ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_DANGER, BG_MAIN


class LoginPage(QWidget):
    login_success = Signal(dict)  # Emits data dictionary containing access_token, username, and full_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        # Outer main layout (fills screen)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(f"background-color: {BG_MAIN};")

        # Center card container
        center_frame = QFrame(self)
        center_frame.setFixedSize(380, 480)
        center_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 16px;
            }
        """)

        card_layout = QVBoxLayout(center_frame)
        card_layout.setContentsMargins(30, 40, 30, 40)
        card_layout.setSpacing(15)

        # App Logo / Icon representation
        logo_label = QLabel("⛽", center_frame)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("font-size: 48px; border: none; background: transparent;")
        card_layout.addWidget(logo_label)

        # Title
        title_label = QLabel("PETROL PUMP ERP", center_frame)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {TEXT_PRIMARY}; border: none; background: transparent;")
        card_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Finance & Operations Manager", center_frame)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; border: none; background: transparent;")
        card_layout.addWidget(subtitle_label)

        card_layout.addSpacing(15)

        # Username Label + Input
        user_lbl = QLabel("USERNAME", center_frame)
        user_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {TEXT_SECONDARY}; border: none; background: transparent;")
        card_layout.addWidget(user_lbl)

        self.username_input = QLineEdit(center_frame)
        self.username_input.setPlaceholderText("Enter admin username...")
        self.username_input.setText("admin")  # Seed default
        card_layout.addWidget(self.username_input)

        # Password Label + Input
        pass_lbl = QLabel("PASSWORD", center_frame)
        pass_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {TEXT_SECONDARY}; border: none; background: transparent;")
        card_layout.addWidget(pass_lbl)

        self.password_input = QLineEdit(center_frame)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter password...")
        self.password_input.setText("admin123")  # Seed default
        self.password_input.returnPressed.connect(self._handle_login)
        card_layout.addWidget(self.password_input)

        # Error message field
        self.error_label = QLabel("", center_frame)
        self.error_label.setStyleSheet(f"color: {ACCENT_DANGER}; font-size: 11px; border: none; background: transparent;")
        self.error_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.error_label)

        card_layout.addSpacing(10)

        # Login Button
        self.login_btn = QPushButton("Sign In", center_frame)
        self.login_btn.setObjectName("ActionButton")
        self.login_btn.clicked.connect(self._handle_login)
        card_layout.addWidget(self.login_btn)

        # Add centered container to screen layout
        main_layout.addStretch()
        main_layout.addWidget(center_frame)
        main_layout.addStretch()

    def _handle_login(self):
        self.error_label.setText("")
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.error_label.setText("Please enter both username and password")
            return

        self.login_btn.setText("Authenticating...")
        self.login_btn.setEnabled(False)

        res = client.login(username, password)
        if res["success"]:
            self.login_success.emit(res["data"])
        else:
            self.error_label.setText(res["error"])
            self.login_btn.setText("Sign In")
            self.login_btn.setEnabled(True)

    def clear_inputs(self):
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.clear()
        self.login_btn.setText("Sign In")
        self.login_btn.setEnabled(True)
