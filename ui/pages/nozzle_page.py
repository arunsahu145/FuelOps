"""
Petrol Pump Finance Manager ERP — Nozzle Mapping Page
Interactive grid map of nozzles where clicking any card opens a premium fuel assignment modal.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QMessageBox, QScrollArea, QSizePolicy, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR, BG_SURFACE, BG_MAIN,
    BG_SURFACE_LIGHT, ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_DANGER
)
from ui.api_client import client
from utils.helpers import get_fuel_color


class FuelSelectionDialog(QDialog):
    """Premium dialog for selecting and assigning a fuel type to a nozzle."""
    def __init__(self, nozzle_number, nozzle_label, current_fuel, fuels, parent=None):
        super().__init__(parent)
        self.selected_fuel_id = None
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setWindowTitle(f"Assign Nozzle N{nozzle_number}")

        # Premium Dark Theme style
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_MAIN};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        title_lbl = QLabel(f"Assign Fuel Product to Nozzle N{nozzle_number}", self)
        title_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            f"Location: {nozzle_label}\nCurrent Assignment: <b>{current_fuel or 'UNASSIGNED'}</b>",
            self
        )
        desc_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        layout.addSpacing(4)

        # Large beautiful product cards
        for f in fuels:
            fid = f["id"]
            fname = f["name"]
            color = get_fuel_color(fname)

            btn = QPushButton(f"  {fname}  ", self)
            btn.setCursor(Qt.PointingHandCursor)

            is_active = (fname == current_fuel)
            if is_active:
                btn_style = f"""
                    QPushButton {{
                        background-color: {color};
                        color: #ffffff;
                        font-weight: bold;
                        border-radius: 8px;
                        padding: 12px;
                        font-size: 13px;
                        border: 2px solid #ffffff;
                    }}
                    QPushButton:hover {{
                        background-color: {color}ee;
                    }}
                """
            else:
                btn_style = f"""
                    QPushButton {{
                        background-color: {BG_SURFACE};
                        color: {TEXT_PRIMARY};
                        font-weight: 600;
                        border-radius: 8px;
                        padding: 12px;
                        font-size: 13px;
                        border: 1px solid {BORDER_COLOR};
                    }}
                    QPushButton:hover {{
                        background-color: {color}15;
                        color: {color};
                        border: 1px solid {color}a0;
                    }}
                """
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked=False, id_=fid: self._on_select(id_))
            layout.addWidget(btn)

        layout.addSpacing(10)

        # Cancel button
        close_btn = QPushButton("  Cancel  ", self)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                font-weight: bold;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                border: 1px solid {BORDER_COLOR};
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
                background-color: {BG_SURFACE};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _on_select(self, fuel_id):
        self.selected_fuel_id = fuel_id
        self.accept()


class NozzleCard(QFrame):
    """Interactive visual representation of a nozzle. Responds to clicks with animations."""
    clicked = Signal(object)

    def __init__(self, nozzle_data, parent=None):
        super().__init__(parent)
        self.nozzle_data = nozzle_data
        self.setObjectName("NozzleEntryCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        accent_color = get_fuel_color(self.nozzle_data.get("assigned_fuel_type", ""))
        fuel_name = self.nozzle_data.get("assigned_fuel_type") or "UNASSIGNED"

        if fuel_name == "UNASSIGNED":
            card_border = BORDER_COLOR
            hover_border = ACCENT_PRIMARY
        else:
            card_border = f"{accent_color}50"
            hover_border = accent_color

        self.setStyleSheet(f"""
            QFrame#NozzleEntryCard {{
                background-color: {BG_SURFACE};
                border: 1.5px solid {card_border};
                border-radius: 12px;
            }}
            QFrame#NozzleEntryCard:hover {{
                border: 1.5px solid {hover_border};
                background-color: {BG_SURFACE_LIGHT}40;
            }}
        """)

        card_layout = QVBoxLayout(self)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(18, 16, 18, 16)

        # Header Row: Nozzle No. & Edit Icon
        top_row = QHBoxLayout()
        number_lbl = QLabel(f"N{self.nozzle_data['nozzle_number']}", self)
        number_lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {TEXT_PRIMARY};")
        top_row.addWidget(number_lbl)

        top_row.addStretch()

        edit_icon = QLabel("✏️", self)
        edit_icon.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        top_row.addWidget(edit_icon)
        card_layout.addLayout(top_row)

        # Label (Location details)
        label_lbl = QLabel(self.nozzle_data['label'], self)
        label_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; font-weight: 500;")
        card_layout.addWidget(label_lbl)

        # Product Badge
        product_badge = QLabel(fuel_name, self)
        product_badge.setAlignment(Qt.AlignCenter)
        if fuel_name == "UNASSIGNED":
            badge_style = (
                "background-color: #475569; color: #cbd5e1; border-radius: 6px; "
                "padding: 6px 10px; font-weight: bold; font-size: 11px;"
            )
        else:
            badge_style = (
                f"background-color: {accent_color}18; color: {accent_color}; border-radius: 6px; "
                f"padding: 6px 10px; font-weight: bold; font-size: 11px; "
                f"border: 1px solid {accent_color}40;"
            )
        product_badge.setStyleSheet(badge_style)
        card_layout.addWidget(product_badge)

        # Interactive Cue
        cue_lbl = QLabel("Click card to reassign product", self)
        cue_lbl.setAlignment(Qt.AlignCenter)
        cue_lbl.setStyleSheet(f"font-size: 10px; color: {TEXT_SECONDARY}; font-style: italic;")
        card_layout.addWidget(cue_lbl)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.nozzle_data)


class NozzlePage(QWidget):
    """Desktop view hosting the interactive nozzle map grid."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toast = None
        self.nozzles_data = []
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
        title_lbl = QLabel("NOZZLE ASSIGNMENTS", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel("Interactive Nozzle Map. Click directly on any card below to map a fuel product.", self)
        sub_lbl.setObjectName("SubHeaderLabel")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(sub_lbl)
        layout.addLayout(header_vbox)

        # ── Interactive Nozzle Grid Map ──
        grid_frame = QFrame(self)
        grid_frame.setObjectName("SmartCard")
        grid_frame_layout = QVBoxLayout(grid_frame)
        grid_frame_layout.setContentsMargins(20, 20, 20, 20)
        grid_frame_layout.setSpacing(12)

        grid_title = QLabel("INTERACTIVE PUMP NOZZLE MAP", self)
        grid_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY}; letter-spacing: 0.5px;")
        grid_frame_layout.addWidget(grid_title)

        self.grid_widget = QWidget(self)
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 10, 0, 0)
        grid_frame_layout.addWidget(self.grid_widget)

        layout.addWidget(grid_frame)
        layout.addStretch()

    def load_data(self):
        try:
            self.nozzles_data = client.get("/api/nozzle/list")
            self._rebuild_grid()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load nozzle data: {e}")

    def _rebuild_grid(self):
        # Clear previous grid elements
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        cols = 3
        for idx, nozzle in enumerate(self.nozzles_data):
            row = idx // cols
            col = idx % cols

            nozzle_card = NozzleCard(nozzle, self)
            nozzle_card.clicked.connect(self._on_nozzle_clicked)
            self.grid_layout.addWidget(nozzle_card, row, col)

    def _on_nozzle_clicked(self, nozzle):
        try:
            fuels = client.get("/api/fuel/types")
            dialog = FuelSelectionDialog(
                nozzle["nozzle_number"],
                nozzle["label"],
                nozzle["assigned_fuel_type"],
                fuels,
                self
            )
            if dialog.exec() == QDialog.Accepted:
                selected_fuel_id = dialog.selected_fuel_id
                if selected_fuel_id:
                    client.post("/api/nozzle/assign", data={
                        "nozzle_id": nozzle["id"],
                        "fuel_type_id": selected_fuel_id
                    })

                    if self._toast:
                        fuel_name = next(
                            (f["name"] for f in fuels if f["id"] == selected_fuel_id),
                            "Product"
                        )
                        self._toast.show_message(
                            f"Nozzle N{nozzle['nozzle_number']} mapped to {fuel_name} successfully!",
                            "success"
                        )

                    self.load_data()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)
