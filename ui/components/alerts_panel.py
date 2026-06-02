"""
Petrol Pump Finance Manager ERP — Alerts Panel
Notification bell button with badge + slide-down alerts overlay panel.
"""
from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from ui.theme import (
    BG_MAIN, BG_SURFACE, BG_SURFACE_LIGHT, TEXT_PRIMARY, TEXT_SECONDARY,
    BORDER_COLOR, ACCENT_DANGER, ACCENT_WARNING, ACCENT_PRIMARY
)
from ui.api_client import client


# ─── Severity Styling ─────────────────────────────────────────────────────────

SEVERITY_STYLES = {
    "critical": {
        "color": "#ef4444",
        "bg": "#ef444418",
        "border": "#ef444460",
        "icon": "🔴",
        "label": "CRITICAL",
    },
    "warning": {
        "color": "#f59e0b",
        "bg": "#f59e0b18",
        "border": "#f59e0b60",
        "icon": "🟡",
        "label": "WARNING",
    },
    "caution": {
        "color": "#f97316",
        "bg": "#f9731618",
        "border": "#f9731660",
        "icon": "🟠",
        "label": "CAUTION",
    },
}


class AlertBellButton(QPushButton):
    """
    Notification bell button with a floating badge counter.
    Renders a styled bell icon and a red count badge when alerts are active.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0
        self._critical_count = 0
        self.setFixedSize(42, 42)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Alerts & Notifications")
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_SURFACE_LIGHT}50;
                border: 1px solid {BORDER_COLOR};
                border-radius: 21px;
                font-size: 18px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {BG_SURFACE_LIGHT};
                border-color: {ACCENT_PRIMARY}80;
            }}
            QPushButton:pressed {{
                background-color: {ACCENT_PRIMARY}30;
            }}
        """)

    def set_count(self, total: int, critical: int = 0):
        """Update the badge count."""
        self._count = total
        self._critical_count = critical
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw bell icon centered
        bell_font = QFont("Segoe UI Emoji", 16)
        painter.setFont(bell_font)
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(self.rect(), Qt.AlignCenter, "🔔")

        # Draw badge if count > 0
        if self._count > 0:
            badge_size = 18
            badge_x = self.width() - badge_size - 2
            badge_y = 2

            # Badge background — red for critical, amber for warnings only
            badge_color = QColor("#ef4444") if self._critical_count > 0 else QColor("#f59e0b")
            painter.setBrush(QBrush(badge_color))
            painter.setPen(QPen(QColor(BG_MAIN), 2))
            painter.drawEllipse(badge_x, badge_y, badge_size, badge_size)

            # Badge text
            painter.setPen(QColor("white"))
            badge_font = QFont("Segoe UI", 8, QFont.Bold)
            painter.setFont(badge_font)
            display_count = str(self._count) if self._count < 10 else "9+"
            from PySide6.QtCore import QRect
            painter.drawText(
                QRect(badge_x, badge_y, badge_size, badge_size),
                Qt.AlignCenter,
                display_count
            )

        painter.end()


class AlertCard(QFrame):
    """A single alert card in the panel, styled by severity."""

    def __init__(self, alert_data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("AlertCard")
        sev = alert_data.get("severity", "warning")
        style = SEVERITY_STYLES.get(sev, SEVERITY_STYLES["warning"])

        self.setStyleSheet(f"""
            QFrame#AlertCard {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-left: 4px solid {style['color']};
                border-radius: 8px;
                padding: 0;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        # Severity icon
        icon_lbl = QLabel(style["icon"])
        icon_lbl.setFixedWidth(28)
        icon_lbl.setAlignment(Qt.AlignTop)
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        # Header row: title + severity badge
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title_lbl = QLabel(alert_data.get("title", "Alert"))
        title_lbl.setStyleSheet(f"""
            font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY};
            background: transparent; border: none;
        """)
        title_lbl.setWordWrap(True)
        header_row.addWidget(title_lbl, 1)

        badge_lbl = QLabel(style["label"])
        badge_lbl.setFixedHeight(20)
        badge_lbl.setStyleSheet(f"""
            font-size: 9px; font-weight: bold; color: {style['color']};
            background-color: {style['color']}25;
            border: 1px solid {style['color']}40;
            border-radius: 4px;
            padding: 2px 8px;
        """)
        header_row.addWidget(badge_lbl)
        text_layout.addLayout(header_row)

        # Message
        msg_lbl = QLabel(alert_data.get("message", ""))
        msg_lbl.setStyleSheet(f"""
            font-size: 13px; color: {TEXT_SECONDARY};
            background: transparent; border: none;
        """)
        msg_lbl.setWordWrap(True)
        text_layout.addWidget(msg_lbl)

        layout.addLayout(text_layout, 1)


class AlertsPanel(QFrame):
    """
    Slide-down overlay panel displaying all active alerts.
    Positioned below the header bar.
    """

    panel_closed = Signal()
    alerts_changed = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AlertsOverlay")
        self.setFixedWidth(560)
        self.setMinimumHeight(180)
        self.setMaximumHeight(820)
        self.hide()

        # Drop shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(f"""
            QFrame#AlertsOverlay {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 16)
        main_layout.setSpacing(14)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title = QLabel("🔔  Alerts & Notifications")
        title.setStyleSheet(f"""
            font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY};
        """)
        header_row.addWidget(title)
        header_row.addStretch()

        self.count_badge = QLabel("0 alerts")
        self.count_badge.setStyleSheet(f"""
            font-size: 11px; color: {TEXT_SECONDARY};
            background-color: {BG_SURFACE_LIGHT}60;
            border-radius: 10px;
            padding: 3px 10px;
        """)
        header_row.addWidget(self.count_badge)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_SURFACE_LIGHT}55;
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 700;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_DANGER}20;
                border-color: {ACCENT_DANGER};
                color: {ACCENT_DANGER};
            }}
            QPushButton:disabled {{
                color: {TEXT_SECONDARY}70;
                background-color: transparent;
            }}
        """)
        self.clear_btn.clicked.connect(self._clear_alerts)
        header_row.addWidget(self.clear_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {BORDER_COLOR};
                border-radius: 16px;
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_DANGER}20;
                border-color: {ACCENT_DANGER};
                color: {ACCENT_DANGER};
            }}
        """)
        close_btn.clicked.connect(self._close_panel)
        header_row.addWidget(close_btn)
        main_layout.addLayout(header_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {BORDER_COLOR}; max-height: 1px;")
        main_layout.addWidget(sep)

        # Scrollable alert cards area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll, 1)

        # Empty state label (hidden when alerts exist)
        self.empty_label = QLabel("✅  All clear! No active alerts.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            font-size: 14px; color: {TEXT_SECONDARY};
            padding: 36px;
        """)
        self.empty_label.hide()
        main_layout.addWidget(self.empty_label)

    def load_alerts(self):
        """Fetch alerts from API and populate cards."""
        try:
            data = client.get("/api/alerts")
            alerts = data.get("alerts", [])
            total = data.get("total_count", 0)

            # Clear existing cards
            while self.cards_layout.count() > 1:  # Keep the stretch
                item = self.cards_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if total == 0:
                self.empty_label.show()
                self.scroll.hide()
                self.clear_btn.setEnabled(False)
                self.count_badge.setText("All clear")
                self.count_badge.setStyleSheet(f"""
                    font-size: 11px; color: #10b981;
                    background-color: #10b98120;
                    border-radius: 10px;
                    padding: 3px 10px;
                """)
            else:
                self.empty_label.hide()
                self.scroll.show()
                self.clear_btn.setEnabled(True)
                self.count_badge.setText(f"{total} alert{'s' if total != 1 else ''}")
                self.count_badge.setStyleSheet(f"""
                    font-size: 11px; color: {ACCENT_DANGER};
                    background-color: {ACCENT_DANGER}20;
                    border-radius: 10px;
                    padding: 3px 10px;
                """)

                for alert in alerts:
                    card = AlertCard(alert, self.cards_container)
                    # Insert before the stretch
                    self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

            # Adjust height based on content
            parent_height = self.parent().height() if self.parent() else 820
            available_height = max(360, parent_height - 76)
            card_height = max(360, min(112 * total + 130, available_height, 800))
            self.setFixedHeight(card_height)
            critical_count = data.get("critical_count", 0)
            self.alerts_changed.emit(total, critical_count)

        except Exception as e:
            print(f"[Alerts] Error fetching alerts: {e}")

    def _clear_alerts(self):
        """Dismiss the currently visible generated alerts."""
        try:
            result = client.post("/api/alerts/clear", data={})
            self.alerts_changed.emit(0, 0)
            self.load_alerts()
        except Exception as e:
            print(f"[Alerts] Error clearing alerts: {e}")

    def toggle(self):
        """Toggle the panel visibility."""
        if self.isVisible():
            self._close_panel()
        else:
            self.load_alerts()
            self.show()
            self.raise_()

    def _close_panel(self):
        self.hide()
        self.panel_closed.emit()
