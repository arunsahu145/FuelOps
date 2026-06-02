"""
Petrol Pump Finance Manager ERP — Shift Page (v2)
Nozzle grid layout with EDITABLE opening + closing readings per shift.
Enter/Tab to navigate. All 8 nozzles visible at once.
Delete support for log entries. Corrected shift timings.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit,
    QPushButton, QMessageBox, QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator
from ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_PRIMARY, ACCENT_SUCCESS,
    ACCENT_WARNING, BG_MAIN, BG_SURFACE, BG_SURFACE_LIGHT, BORDER_COLOR
)
from ui.components.date_picker import DatePicker
from ui.components.data_table import DataTable
from ui.api_client import client
from utils.helpers import format_currency, format_litres, get_fuel_color


class NozzleEntryCard(QFrame):
    """A single nozzle card with editable opening/closing reading inputs and live stats."""

    def __init__(self, nozzle_data: dict, shift_number: int, parent=None):
        super().__init__(parent)
        self.setObjectName("NozzleEntryCard")
        self.nozzle_data = nozzle_data
        self.shift_number = shift_number
        self.nozzle_id = nozzle_data["id"]
        self.fuel_type_id = nozzle_data.get("assigned_fuel_type_id")
        self.fuel_name = nozzle_data.get("assigned_fuel_type") or "UNASSIGNED"
        self.selling_price = 0.0
        self.is_submitted = False
        self._init_ui()

    def _init_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # ── Top row: Nozzle number + status ──
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        nozzle_lbl = QLabel(f"N{self.nozzle_data['nozzle_number']}", self)
        nozzle_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        top_row.addWidget(nozzle_lbl)
        top_row.addStretch()

        self.status_lbl = QLabel("", self)
        self.status_lbl.setObjectName("StatusBadge")
        top_row.addWidget(self.status_lbl)
        layout.addLayout(top_row)

        # Fuel badge
        fuel_color = get_fuel_color(self.fuel_name)
        self.fuel_badge = QLabel(self.fuel_name.upper(), self)
        self.fuel_badge.setAlignment(Qt.AlignCenter)
        if self.fuel_name == "UNASSIGNED":
            self.fuel_badge.setStyleSheet(
                "background-color: #475569; color: #cbd5e1; border-radius: 4px; "
                "padding: 4px 8px; font-weight: bold; font-size: 11px;"
            )
        else:
            self.fuel_badge.setStyleSheet(
                f"background-color: {fuel_color}18; color: {fuel_color}; border-radius: 4px; "
                f"padding: 4px 8px; font-weight: bold; font-size: 11px; "
                f"border: 1px solid {fuel_color}40;"
            )
        layout.addWidget(self.fuel_badge)

        # ── Opening reading (EDITABLE) ──
        op_lbl = QLabel("OPENING", self)
        op_lbl.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {TEXT_SECONDARY}; letter-spacing: 0.5px;")
        layout.addWidget(op_lbl)

        self.opening_input = QLineEdit("0.00000", self)
        self.opening_input.setObjectName("ReadingInput")
        self.opening_input.setPlaceholderText("Opening meter...")
        self.opening_input.setValidator(QDoubleValidator(0.0, 9999999999.99999, 5, self))
        self.opening_input.textChanged.connect(self._recalculate)
        layout.addWidget(self.opening_input)

        # ── Closing reading (editable) ──
        cl_lbl = QLabel("CLOSING", self)
        cl_lbl.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {TEXT_SECONDARY}; letter-spacing: 0.5px;")
        layout.addWidget(cl_lbl)

        self.closing_input = QLineEdit("", self)
        self.closing_input.setObjectName("ReadingInput")
        self.closing_input.setPlaceholderText("Closing meter...")
        self.closing_input.setValidator(QDoubleValidator(0.0, 9999999999.99999, 5, self))
        self.closing_input.textChanged.connect(self._recalculate)
        layout.addWidget(self.closing_input)

        # ── Live stats ──
        self.stats_lbl = QLabel("", self)
        self.stats_lbl.setStyleSheet(
            f"font-size: 11px; color: #38bdf8; background-color: {BG_MAIN}; "
            f"padding: 6px 8px; border-radius: 4px; font-weight: 600;"
        )
        self.stats_lbl.setWordWrap(True)
        layout.addWidget(self.stats_lbl)
        self._update_stats_display(0.0, 0.0)

    def set_opening(self, value: float):
        self.opening_input.setText(f"{value:.5f}")

    def set_closing(self, value: float):
        self.closing_input.setText(f"{value:.5f}")

    def get_opening(self) -> float:
        try:
            return float(self.opening_input.text())
        except (ValueError, TypeError):
            return 0.0

    def get_closing(self) -> float:
        try:
            return float(self.closing_input.text())
        except (ValueError, TypeError):
            return 0.0

    def set_selling_price(self, price: float):
        self.selling_price = price

    def mark_submitted(self, litres: float = 0, amount: float = 0):
        self.is_submitted = True
        self.opening_input.setReadOnly(True)
        self.closing_input.setReadOnly(True)
        read_only_style = (
            f"background-color: {BG_SURFACE_LIGHT}40; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {ACCENT_SUCCESS}60; border-radius: 6px; "
            f"padding: 8px 10px; font-size: 14px; font-weight: 600; "
            f"font-family: 'Consolas', monospace;"
        )
        self.opening_input.setStyleSheet(read_only_style)
        self.closing_input.setStyleSheet(read_only_style)
        self.status_lbl.setText("✓ SAVED")
        self.status_lbl.setStyleSheet(
            f"background-color: {ACCENT_SUCCESS}20; color: {ACCENT_SUCCESS}; "
            f"border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: bold;"
        )
        self.setStyleSheet(
            f"QFrame#NozzleEntryCard {{ background-color: {BG_SURFACE}; "
            f"border: 1.5px solid {ACCENT_SUCCESS}50; border-radius: 10px; }}"
        )

    def mark_pending(self):
        self.is_submitted = False
        self.opening_input.setReadOnly(False)
        self.closing_input.setReadOnly(False)
        self.opening_input.setStyleSheet("")
        self.closing_input.setStyleSheet("")
        self.status_lbl.setText("")
        self.status_lbl.setStyleSheet("")
        self.setStyleSheet("")

    def _recalculate(self):
        opening = self.get_opening()
        closing = self.get_closing()
        litres = max(0.0, closing - opening) if closing > 0 else 0.0
        amount = litres * self.selling_price
        self._update_stats_display(litres, amount)

    def _update_stats_display(self, litres: float, amount: float):
        self.stats_lbl.setText(
            f"{litres:,.5f} L  •  {format_currency(amount)}"
        )


class ShiftPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nozzle_cards = {}  # key: (shift_number, nozzle_id)
        self.nozzles_cache = []
        self._toast = None
        self._last_loaded_date = None
        self._init_ui()

    def set_toast(self, toast):
        self._toast = toast

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(scroll)

        content_widget = QWidget()
        content_widget.setObjectName("PageContainer")
        scroll.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # ── Header ──
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_lbl = QLabel("SHIFT METER READINGS", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel("Enter opening & closing readings for all nozzles. Press Enter to save & jump to next.", self)
        sub_lbl.setObjectName("SubHeaderLabel")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.date_picker = DatePicker(self)
        self.date_picker.date_changed.connect(self._on_date_changed)
        header_layout.addWidget(self.date_picker)

        layout.addLayout(header_layout)

        # ── Shift 1 Section ──
        self.shift1_container = self._create_shift_section(1)
        layout.addWidget(self.shift1_container)

        # ── Shift 2 Section ──
        self.shift2_container = self._create_shift_section(2)
        layout.addWidget(self.shift2_container)

        # ── Collapsible History Section ──
        history_row = QHBoxLayout()
        history_row.setSpacing(10)
        self.history_toggle_btn = QPushButton("  📋 Show Entry Log ▼", self)
        self.history_toggle_btn.setObjectName("ToggleHistoryBtn")
        self.history_toggle_btn.setFixedWidth(220)
        self.history_toggle_btn.clicked.connect(self._toggle_history)
        history_row.addWidget(self.history_toggle_btn)
        history_row.addStretch()
        layout.addLayout(history_row)

        # History table (hidden by default) — with delete support
        self.history_frame = QFrame(self)
        self.history_frame.setObjectName("SmartCard")
        self.history_frame.setVisible(False)
        history_layout = QVBoxLayout(self.history_frame)
        history_layout.setContentsMargins(16, 16, 16, 16)
        history_layout.setSpacing(10)

        hist_title = QLabel("ENTRIES ON SELECTED DATE", self)
        hist_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        history_layout.addWidget(hist_title)

        self.table = DataTable(
            ["Nozzle", "Shift", "Product", "Opening", "Closing", "Litres Sold", "Sales Value"],
            self,
            enable_delete=True
        )
        self.table.setMinimumHeight(450)
        self.table.row_delete_requested.connect(self._delete_shift_reading)
        history_layout.addWidget(self.table)
        layout.addWidget(self.history_frame)

        layout.addStretch()

    def _create_shift_section(self, shift_number: int) -> QFrame:
        """Create a shift section frame with a 3x2 nozzle grid."""
        container = QFrame(self)
        container.setObjectName("SmartCard")
        container.setStyleSheet(
            f"QFrame#SmartCard {{ background-color: {BG_SURFACE}; "
            f"border: 1px solid {BORDER_COLOR}; border-radius: 12px; }}"
        )

        outer_layout = QVBoxLayout(container)
        outer_layout.setContentsMargins(20, 16, 20, 16)
        outer_layout.setSpacing(14)

        # Section header
        header_row = QHBoxLayout()
        shift_color = ACCENT_PRIMARY if shift_number == 1 else ACCENT_WARNING

        indicator = QLabel("●", self)
        indicator.setStyleSheet(f"font-size: 14px; color: {shift_color};")
        header_row.addWidget(indicator)

        header_lbl = QLabel(f"SHIFT {shift_number}", self)
        header_lbl.setObjectName("ShiftSectionHeader")
        header_row.addWidget(header_lbl)

        # Corrected shift timings
        time_hint = QLabel("(8 AM – 7 PM)" if shift_number == 1 else "(7 PM – 8 AM)", self)
        time_hint.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; padding-top: 4px;")
        header_row.addWidget(time_hint)

        header_row.addStretch()

        save_all_btn = QPushButton(f"  Save All Shift {shift_number}  ", self)
        save_all_btn.setObjectName("SuccessButton")
        save_all_btn.clicked.connect(lambda: self._save_all_shift(shift_number))
        header_row.addWidget(save_all_btn)

        outer_layout.addLayout(header_row)

        grid_widget = QWidget(self)
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(12)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(grid_widget)

        if shift_number == 1:
            self._shift1_grid = grid_layout
            self._shift1_grid_widget = grid_widget
        else:
            self._shift2_grid = grid_layout
            self._shift2_grid_widget = grid_widget

        return container

    def load_data(self):
        current_date = self.date_picker.get_date_str()
        
        # Check if cache matches to prevent wiping out user inputs when switching tabs
        if hasattr(self, "_last_loaded_date") and self._last_loaded_date == current_date and self.nozzle_cards:
            # Re-fetch table if history panel is visible, but do not touch the input cards
            if self.history_frame.isVisible():
                self._refresh_table()
            return
            
        try:
            self.nozzles_cache = client.get("/api/nozzle/list")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load nozzles: {e}")
            return

        self._build_nozzle_grids()
        self._load_readings_into_cards()
        self._last_loaded_date = current_date

    def _build_nozzle_grids(self):
        self.nozzle_cards.clear()

        for shift_num in [1, 2]:
            grid = self._shift1_grid if shift_num == 1 else self._shift2_grid

            while grid.count():
                item = grid.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

            cols = 3
            tab_order_list = []

            for idx, nozzle in enumerate(self.nozzles_cache):
                row = idx // cols
                col = idx % cols

                card = NozzleEntryCard(nozzle, shift_num, self)

                if nozzle.get("assigned_fuel_type_id"):
                    try:
                        fuel_data = client.get(f"/api/fuel/types/{nozzle['assigned_fuel_type_id']}")
                        card.set_selling_price(fuel_data.get("current_selling_price") or 0.0)
                    except Exception:
                        pass

                # Connect Enter on closing to save + move
                card.closing_input.returnPressed.connect(
                    lambda c=card, s=shift_num, i=idx: self._on_enter_pressed(c, s, i)
                )

                # Live propagation: Shift 1 closing → Shift 2 opening
                if shift_num == 1:
                    nid = nozzle["id"]
                    card.closing_input.textChanged.connect(
                        lambda text, nozzle_id=nid: self._propagate_closing_to_shift2(nozzle_id, text)
                    )

                grid.addWidget(card, row, col)
                self.nozzle_cards[(shift_num, nozzle["id"])] = card
                tab_order_list.append(card.opening_input)
                tab_order_list.append(card.closing_input)

            # Tab order: opening1 -> closing1 -> opening2 -> closing2 -> ...
            for i in range(len(tab_order_list) - 1):
                QWidget.setTabOrder(tab_order_list[i], tab_order_list[i + 1])

    def _load_readings_into_cards(self):
        date_str = self.date_picker.get_date_str()

        for shift_num in [1, 2]:
            for nozzle in self.nozzles_cache:
                key = (shift_num, nozzle["id"])
                card = self.nozzle_cards.get(key)
                if not card:
                    continue
                card.mark_pending()
                card.opening_input.clear()
                card.closing_input.clear()

                # Try to get auto-populated opening from previous shift
                try:
                    res = client.get("/api/shift/opening-reading", params={
                        "nozzle_id": nozzle["id"],
                        "shift_number": shift_num,
                        "reading_date": date_str
                    })
                    opening = res.get("opening_reading")
                    if opening is not None:
                        card.set_opening(opening)
                except Exception:
                    pass

        # Mark already-submitted entries
        try:
            readings = client.get("/api/shift/readings", params={"reading_date": date_str})
            for r in readings:
                key = (r["shift_number"], r["nozzle_id"])
                card = self.nozzle_cards.get(key)
                if card:
                    card.set_opening(r["opening_reading"])
                    card.set_closing(r["closing_reading"])
                    card.mark_submitted(r["fuel_sold_litres"], r["sales_amount"])
        except Exception:
            pass

        # After loading shift 1 data, propagate closings to shift 2 openings
        for nozzle in self.nozzles_cache:
            s1_card = self.nozzle_cards.get((1, nozzle["id"]))
            s2_card = self.nozzle_cards.get((2, nozzle["id"]))
            if s1_card and s2_card and not s2_card.is_submitted:
                closing_text = s1_card.closing_input.text().strip()
                if closing_text:
                    try:
                        val = float(closing_text)
                        if val > 0:
                            s2_card.set_opening(val)
                    except ValueError:
                        pass

        self._focus_first_empty(1)

        if self.history_frame.isVisible():
            self._refresh_table()

    def _focus_first_empty(self, shift_num: int):
        for nozzle in self.nozzles_cache:
            key = (shift_num, nozzle["id"])
            card = self.nozzle_cards.get(key)
            if card and not card.is_submitted:
                card.opening_input.setFocus()
                return

    def _on_enter_pressed(self, card: NozzleEntryCard, shift_num: int, idx: int):
        if card.is_submitted:
            self._focus_next_card(shift_num, idx)
            return
        closing_text = card.closing_input.text().strip()
        if not closing_text:
            self._focus_next_card(shift_num, idx)
            return
        self._save_single_entry(card, shift_num, idx)

    def _focus_next_card(self, shift_num: int, current_idx: int):
        nozzle_count = len(self.nozzles_cache)
        for offset in range(1, nozzle_count):
            next_idx = (current_idx + offset) % nozzle_count
            next_nozzle = self.nozzles_cache[next_idx]
            key = (shift_num, next_nozzle["id"])
            card = self.nozzle_cards.get(key)
            if card and not card.is_submitted:
                card.opening_input.setFocus()
                return
        next_shift = 2 if shift_num == 1 else 1
        self._focus_first_empty(next_shift)

    def _save_single_entry(self, card: NozzleEntryCard, shift_num: int, idx: int):
        if card.fuel_type_id is None:
            if self._toast:
                self._toast.show_message(f"Nozzle {card.nozzle_data['nozzle_number']}: No fuel assigned!", "error")
            return
        if card.selling_price <= 0:
            if self._toast:
                self._toast.show_message(f"Nozzle {card.nozzle_data['nozzle_number']}: No selling price set!", "error")
            return

        opening = card.get_opening()
        closing = card.get_closing()
        if closing < opening:
            if self._toast:
                self._toast.show_message("Closing reading cannot be less than opening!", "error")
            return

        date_str = self.date_picker.get_date_str()
        try:
            client.post("/api/shift/reading", data={
                "nozzle_id": card.nozzle_id,
                "shift_number": shift_num,
                "reading_date": date_str,
                "opening_reading": opening,
                "closing_reading": closing
            })
            litres = closing - opening
            amount = litres * card.selling_price
            card.mark_submitted(litres, amount)

            # If shift 1 saved, push closing to shift 2 opening
            if shift_num == 1:
                s2_card = self.nozzle_cards.get((2, card.nozzle_id))
                if s2_card and not s2_card.is_submitted:
                    s2_card.set_opening(closing)

            if self._toast:
                self._toast.show_message(
                    f"N{card.nozzle_data['nozzle_number']} Shift {shift_num} saved — {format_litres(litres)}",
                    "success"
                )
            self._focus_next_card(shift_num, idx)
            if self.history_frame.isVisible():
                self._refresh_table()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)

    def _save_all_shift(self, shift_num: int):
        saved_count = 0
        error_count = 0

        for idx, nozzle in enumerate(self.nozzles_cache):
            key = (shift_num, nozzle["id"])
            card = self.nozzle_cards.get(key)
            if not card or card.is_submitted:
                continue
            closing_text = card.closing_input.text().strip()
            if not closing_text:
                continue
            if card.fuel_type_id is None or card.selling_price <= 0:
                error_count += 1
                continue
            opening = card.get_opening()
            closing = card.get_closing()
            if closing < opening:
                error_count += 1
                continue

            date_str = self.date_picker.get_date_str()
            try:
                client.post("/api/shift/reading", data={
                    "nozzle_id": card.nozzle_id,
                    "shift_number": shift_num,
                    "reading_date": date_str,
                    "opening_reading": opening,
                    "closing_reading": closing
                })
                litres = closing - opening
                amount = litres * card.selling_price
                card.mark_submitted(litres, amount)
                saved_count += 1
            except Exception:
                error_count += 1

        if self._toast:
            if saved_count > 0 and error_count == 0:
                self._toast.show_message(f"Shift {shift_num}: {saved_count} entries saved ✓", "success")
            elif saved_count > 0:
                self._toast.show_message(f"Shift {shift_num}: {saved_count} saved, {error_count} errors", "warning")
            elif error_count > 0:
                self._toast.show_message(f"Shift {shift_num}: {error_count} errors", "error")
            else:
                self._toast.show_message(f"Shift {shift_num}: No new entries to save", "info")

        # After batch save of shift 1, propagate closings to shift 2 openings
        if shift_num == 1:
            for nozzle in self.nozzles_cache:
                s1_card = self.nozzle_cards.get((1, nozzle["id"]))
                s2_card = self.nozzle_cards.get((2, nozzle["id"]))
                if s1_card and s1_card.is_submitted and s2_card and not s2_card.is_submitted:
                    s2_card.set_opening(s1_card.get_closing())

        if self.history_frame.isVisible():
            self._refresh_table()

    def _propagate_closing_to_shift2(self, nozzle_id: int, text: str):
        """Live propagation: when user types in Shift 1 closing, mirror it to Shift 2 opening."""
        s2_card = self.nozzle_cards.get((2, nozzle_id))
        if s2_card and not s2_card.is_submitted:
            try:
                val = float(text) if text.strip() else 0.0
                if val > 0:
                    s2_card.set_opening(val)
            except ValueError:
                pass

    def _on_date_changed(self):
        self._load_readings_into_cards()
        self._last_loaded_date = self.date_picker.get_date_str()

    def _toggle_history(self):
        visible = not self.history_frame.isVisible()
        self.history_frame.setVisible(visible)
        self.history_toggle_btn.setText(
            "  📋 Hide Entry Log ▲" if visible else "  📋 Show Entry Log ▼"
        )
        if visible:
            self._refresh_table()

    def _refresh_table(self):
        date_str = self.date_picker.get_date_str()
        try:
            readings = client.get("/api/shift/readings", params={"reading_date": date_str})
            rows = []
            ids = []
            for r in readings:
                rows.append((
                    f"Nozzle {r['nozzle_number']}",
                    f"Shift {r['shift_number']}",
                    r["fuel_type_name"],
                    f"{r['opening_reading']:.2f}",
                    f"{r['closing_reading']:.2f}",
                    format_litres(r["fuel_sold_litres"]),
                    format_currency(r["sales_amount"])
                ))
                ids.append(r["id"])
            self.table.populate(rows, row_ids=ids)
        except Exception as e:
            print(f"Error refreshing shift entries table: {e}")

    def _delete_shift_reading(self, reading_id: int):
        """Delete a shift reading entry and reload."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this shift entry?\nThis will also remove the associated sale record.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            client.delete(f"/api/shift/reading/{reading_id}")
            if self._toast:
                self._toast.show_message("Shift entry deleted", "success")
            self._load_readings_into_cards()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Delete failed: {e}", "error", 5000)
