"""
Petrol Pump Finance Manager ERP — UI Theme and Stylesheets
Implements a stunning, modern dark slate theme with harmony colors.
"""

# ── Color Palette ──────────────────────────────────────────────────────────
BG_MAIN = "#0f172a"          # Very dark slate (slate-900)
BG_SURFACE = "#1e293b"       # Dark slate (slate-800)
BG_SURFACE_LIGHT = "#334155" # Medium slate (slate-700)
ACCENT_PRIMARY = "#3b82f6"   # Electric blue
ACCENT_SUCCESS = "#10b981"   # Emerald green
ACCENT_WARNING = "#f59e0b"   # Amber
ACCENT_DANGER = "#ef4444"    # Rose red
TEXT_PRIMARY = "#f8fafc"     # Near white (slate-50)
TEXT_SECONDARY = "#94a3b8"   # Cool gray (slate-400)
BORDER_COLOR = "#334155"     # Subtle border (slate-700)

# ── Fuel Colors ─────────────────────────────────────────────────────────────
FUEL_COLORS = {
    "Petrol": "#10b981",        # Emerald green
    "Power Petrol": "#0ea5e9",  # Sky blue
    "Diesel": "#f59e0b",        # Amber
}

# ── Stylesheet Definitions ──────────────────────────────────────────────────
MAIN_STYLE = f"""
QMainWindow {{
    background-color: {BG_MAIN};
}}

QWidget {{
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    font-size: 13px;
}}

/* Sidebar styling */
#SidebarFrame {{
    background-color: {BG_SURFACE};
    border-right: 1px solid {BORDER_COLOR};
}}

#SidebarTitle {{
    font-size: 15px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    padding: 12px 8px;
}}

/* Sidebar buttons */
QPushButton {{
    border: none;
    border-radius: 6px;
    padding: 10px 15px;
    background-color: transparent;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {BG_SURFACE_LIGHT}80;
}}

QPushButton:checked {{
    background-color: {ACCENT_PRIMARY};
    color: white;
    font-weight: bold;
}}

/* Styled Page Containers */
#PageContainer {{
    background-color: {BG_MAIN};
    padding: 20px;
}}

#HeaderLabel {{
    font-size: 22px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    letter-spacing: 0.5px;
}}

#SubHeaderLabel {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

/* Cards styling */
QFrame#SmartCard {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
}}

/* Forms and Inputs */
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    min-height: 20px;
}}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1.5px solid {ACCENT_PRIMARY};
}}

QComboBox::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid {BORDER_COLOR};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: {BG_SURFACE_LIGHT}40;
}}

QComboBox::drop-down:hover, QDateEdit::drop-down:hover {{
    background-color: {BG_SURFACE_LIGHT}80;
}}

QComboBox::down-arrow, QDateEdit::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {TEXT_PRIMARY};
    width: 0;
    height: 0;
    margin-right: 2px;
}}

/* Beautiful Premium QCalendarWidget Styling */
QCalendarWidget {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {BORDER_COLOR};
    border-radius: 10px;
}}

QCalendarWidget QWidget {{
    alternate-background-color: {BG_MAIN};
}}

QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {BG_MAIN};
    border-bottom: 1.5px solid {BORDER_COLOR};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

QCalendarWidget QToolButton {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    margin: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 12px;
}}

QCalendarWidget QToolButton:hover {{
    background-color: {BG_SURFACE_LIGHT};
    border-color: {BORDER_COLOR};
}}

QCalendarWidget QToolButton:pressed {{
    background-color: {ACCENT_PRIMARY};
    color: white;
}}

QCalendarWidget QWidget#qt_calendar_yearedit,
QCalendarWidget QWidget#qt_calendar_monthedit {{
    color: {TEXT_PRIMARY};
    font-weight: bold;
    font-size: 12px;
}}

QCalendarWidget QAbstractItemView:enabled {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT_PRIMARY};
    selection-color: white;
    border: none;
    outline: none;
}}

QCalendarWidget QAbstractItemView:disabled {{
    color: {TEXT_SECONDARY};
}}

QCalendarWidget QToolButton#qt_calendar_prevmonth,
QCalendarWidget QToolButton#qt_calendar_nextmonth {{
    qproperty-icon: none;
    border: none;
    background-color: transparent;
    font-size: 14px;
    font-weight: bold;
    color: {TEXT_SECONDARY};
}}

QCalendarWidget QToolButton#qt_calendar_prevmonth:hover,
QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {{
    background-color: {BG_SURFACE_LIGHT};
    color: {TEXT_PRIMARY};
}}

QLabel#FormLabel {{
    font-weight: 600;
    color: {TEXT_SECONDARY};
    margin-bottom: 4px;
    font-size: 11px;
    letter-spacing: 0.3px;
}}

/* Tables styling — base defaults only; DataTable has its own inline styles */
QTableWidget {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    font-size: 13px;
}}

QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BG_SURFACE_LIGHT}50;
}}

QTableWidget::item:selected {{
    background-color: {ACCENT_PRIMARY}20;
    color: {TEXT_PRIMARY};
}}

QHeaderView::section {{
    background-color: {BG_SURFACE_LIGHT};
    color: {TEXT_PRIMARY};
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid {BORDER_COLOR};
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 0.3px;
}}

/* Beautiful Primary Action Button */
QPushButton#ActionButton {{
    background-color: {ACCENT_PRIMARY};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    text-align: center;
    font-size: 13px;
}}

QPushButton#ActionButton:hover {{
    background-color: #2563eb;
}}

QPushButton#ActionButton:pressed {{
    background-color: #1d4ed8;
}}

QPushButton#ActionButton:disabled {{
    background-color: {BG_SURFACE_LIGHT};
    color: {TEXT_SECONDARY};
}}

QPushButton#SecondaryActionButton {{
    background-color: {BG_SURFACE_LIGHT};
    color: {TEXT_PRIMARY};
    font-weight: 500;
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 10px 20px;
    text-align: center;
}}

QPushButton#SecondaryActionButton:hover {{
    background-color: {BG_SURFACE_LIGHT}D0;
}}

QPushButton#SuccessButton {{
    background-color: {ACCENT_SUCCESS};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    text-align: center;
    font-size: 13px;
}}

QPushButton#SuccessButton:hover {{
    background-color: #059669;
}}

QPushButton#SuccessButton:pressed {{
    background-color: #047857;
}}

/* Toggle / collapsible history button */
QPushButton#ToggleHistoryBtn {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    font-weight: 500;
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 16px;
    text-align: center;
    font-size: 12px;
}}

QPushButton#ToggleHistoryBtn:hover {{
    background-color: {BG_SURFACE_LIGHT}40;
    color: {TEXT_PRIMARY};
}}

/* Nozzle entry cards in shift page */
QFrame#NozzleEntryCard {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
}}

QFrame#NozzleEntryCard[submitted="true"] {{
    border-color: {ACCENT_SUCCESS};
}}

/* Fuel rate cards */
QFrame#FuelRateCard {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
}}

/* Inline reading input — clean, no arrows */
QLineEdit#ReadingInput {{
    background-color: #0f172a;
    border: 1.5px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 10px 12px;
    color: {TEXT_PRIMARY};
    font-size: 15px;
    font-weight: 600;
    font-family: 'Consolas', 'Courier New', monospace;
}}

QLineEdit#ReadingInput:focus {{
    border-color: {ACCENT_PRIMARY};
    background-color: #1e293b;
}}

/* Section headers inside shift page */
QLabel#ShiftSectionHeader {{
    font-size: 16px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    padding: 8px 0px;
    letter-spacing: 0.5px;
}}

/* Status badges */
QLabel#StatusBadge {{
    font-size: 11px;
    font-weight: bold;
    padding: 3px 10px;
    border-radius: 10px;
}}

/* Scrollbar customization */
QScrollBar:vertical {{
    border: none;
    background: {BG_MAIN};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {BG_SURFACE_LIGHT};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: {BG_MAIN};
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {BG_SURFACE_LIGHT};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
}}

QScrollArea {{
    border: none;
}}
"""
