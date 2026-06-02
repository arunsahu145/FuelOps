"""
Petrol Pump Finance Manager ERP — Toast Notification Widget
Sleek, animated slide-in notification with auto-dismiss and variant support.
"""
from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont


class Toast(QLabel):
    """Animated toast notification that appears at the top-right of the parent widget."""

    VARIANTS = {
        "success": {"bg": "#059669", "border": "#10b981", "icon": "✓"},
        "error":   {"bg": "#dc2626", "border": "#ef4444", "icon": "✕"},
        "info":    {"bg": "#2563eb", "border": "#3b82f6", "icon": "ℹ"},
        "warning": {"bg": "#d97706", "border": "#f59e0b", "icon": "⚠"},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedHeight(48)
        self.setMinimumWidth(280)
        self.setMaximumWidth(420)
        self.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        self.hide()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)

    def show_message(self, message: str, variant: str = "success", duration_ms: int = 3000):
        """Show a toast message with the given variant (success/error/info/warning)."""
        v = self.VARIANTS.get(variant, self.VARIANTS["info"])

        self.setText(f"  {v['icon']}  {message}")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {v['bg']};
                color: #ffffff;
                border: 1px solid {v['border']};
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }}
        """)

        self.adjustSize()
        self.setFixedHeight(48)

        # Position at top-right of parent
        if self.parent():
            pw = self.parent().width()
            x = pw - self.width() - 20
            y = 20
            self.move(x, y)

        # Reset opacity
        self._opacity_effect.setOpacity(1.0)

        # Slide-in animation
        self.show()
        self.raise_()

        start_pos = QPoint(self.x(), -self.height())
        end_pos = QPoint(self.x(), 20)

        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(280)
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._slide_anim.start()

        # Start dismiss timer
        self._dismiss_timer.start(duration_ms)

    def _fade_out(self):
        """Animate opacity to 0 then hide."""
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(400)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InQuad)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()
