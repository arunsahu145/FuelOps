"""
Petrol Pump Finance Manager ERP — Indian Currency LineEdit
Custom QLineEdit that auto-formats numbers with Indian comma grouping
(e.g., 1,23,456.78) as the user types. Preserves cursor position.
"""
from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent


def indian_format(number_str: str) -> str:
    """
    Apply Indian comma grouping to a numeric string (integer part only).
    Rules: last 3 digits grouped, then groups of 2 from the left.
    Example: '1234567' → '12,34,567'
    """
    if not number_str:
        return ""

    # Handle negative
    negative = number_str.startswith("-")
    if negative:
        number_str = number_str[1:]

    # Split integer and decimal
    if "." in number_str:
        int_part, dec_part = number_str.split(".", 1)
    else:
        int_part = number_str
        dec_part = None

    # Remove leading zeros (but keep at least one digit)
    int_part = int_part.lstrip("0") or "0"

    # Apply Indian grouping
    if len(int_part) <= 3:
        formatted = int_part
    else:
        last3 = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        formatted = ",".join(groups) + "," + last3

    if dec_part is not None:
        formatted += "." + dec_part

    if negative:
        formatted = "-" + formatted

    return formatted


def strip_commas(text: str) -> str:
    """Remove all commas from a string."""
    return text.replace(",", "")


class IndianCurrencyLineEdit(QLineEdit):
    """
    QLineEdit that auto-formats input with Indian comma grouping.

    Features:
    - Formats as the user types (e.g., 123456 → 1,23,456)
    - Preserves cursor position intelligently across reformats
    - Allows only digits, one decimal point, and navigation keys
    - Exposes get_value() → float and set_value(float) for clean API integration
    """

    def __init__(self, parent=None, placeholder: str = "₹ 0.00", allow_decimal: bool = True):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._allow_decimal = allow_decimal
        self._formatting = False  # Guard against recursive formatting
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str):
        """Reformat the text with Indian commas whenever it changes."""
        if self._formatting:
            return

        self._formatting = True
        try:
            # Remember cursor position relative to digits (ignore commas)
            cursor_pos = self.cursorPosition()
            # Count how many non-comma characters are before the cursor
            digits_before_cursor = len(strip_commas(text[:cursor_pos]))

            # Strip commas to get raw number
            raw = strip_commas(text)

            # Validate: allow only digits, at most one decimal, optional leading minus
            cleaned = ""
            has_decimal = False
            for i, ch in enumerate(raw):
                if ch == "-" and i == 0:
                    cleaned += ch
                elif ch.isdigit():
                    cleaned += ch
                elif ch == "." and not has_decimal and self._allow_decimal:
                    has_decimal = True
                    cleaned += ch
                # else: skip invalid chars

            # Apply Indian formatting
            formatted = indian_format(cleaned)

            # Set the formatted text
            self.blockSignals(True)
            self.setText(formatted)
            self.blockSignals(False)

            # Restore cursor position: find the position in formatted text
            # where digits_before_cursor non-comma characters have passed
            new_cursor = 0
            digit_count = 0
            for i, ch in enumerate(formatted):
                if digit_count >= digits_before_cursor:
                    new_cursor = i
                    break
                if ch != ",":
                    digit_count += 1
            else:
                new_cursor = len(formatted)

            self.setCursorPosition(new_cursor)

        finally:
            self._formatting = False

    def get_value(self) -> float:
        """Return the clean float value, stripping commas."""
        raw = strip_commas(self.text().strip())
        if not raw or raw == "-" or raw == ".":
            return 0.0
        try:
            return float(raw)
        except (ValueError, TypeError):
            return 0.0

    def set_value(self, value: float, decimals: int = 2):
        """Set the value programmatically with proper formatting."""
        self._formatting = True
        try:
            text = f"{value:.{decimals}f}"
            formatted = indian_format(text)
            self.blockSignals(True)
            self.setText(formatted)
            self.blockSignals(False)
        finally:
            self._formatting = False

    def clear_value(self):
        """Clear the input field."""
        self._formatting = True
        try:
            self.blockSignals(True)
            self.clear()
            self.blockSignals(False)
        finally:
            self._formatting = False
