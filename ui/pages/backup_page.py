"""
Petrol Pump Finance Manager ERP — Backup & Restore Page
Full backup management interface with status card, action buttons, and history table.
"""
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QFileDialog, QMessageBox, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from ui.theme import (
    BG_MAIN, BG_SURFACE, BG_SURFACE_LIGHT, TEXT_PRIMARY, TEXT_SECONDARY,
    BORDER_COLOR, ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_DANGER
)
from ui.components.data_table import DataTable
from ui.api_client import client
from datetime import datetime, timedelta


class BackupPage(QWidget):
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
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)

        # ── Header ──
        header_vbox = QVBoxLayout()
        title_lbl = QLabel("BACKUP & RESTORE", self)
        title_lbl.setObjectName("HeaderLabel")
        sub_lbl = QLabel("Secure your business data with local backups. Export, restore, and manage database snapshots.", self)
        sub_lbl.setObjectName("SubHeaderLabel")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(sub_lbl)
        layout.addLayout(header_vbox)

        # ── Status Card ──
        self.status_card = QFrame(self)
        self.status_card.setObjectName("SmartCard")
        self._init_status_card()
        layout.addWidget(self.status_card)

        # ── Action Buttons Row ──
        actions_frame = QFrame(self)
        actions_frame.setObjectName("SmartCard")
        actions_layout_outer = QVBoxLayout(actions_frame)
        actions_layout_outer.setContentsMargins(20, 18, 20, 18)
        actions_layout_outer.setSpacing(14)

        actions_title = QLabel("QUICK ACTIONS", self)
        actions_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_SECONDARY}; letter-spacing: 0.5px;")
        actions_layout_outer.addWidget(actions_title)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(14)

        # Create Backup button
        self.create_btn = self._make_action_button(
            "💾  Create Backup",
            "Take an instant snapshot of your database",
            ACCENT_PRIMARY, "#2563eb"
        )
        self.create_btn.clicked.connect(self._create_backup)
        actions_row.addWidget(self.create_btn)

        # Export button
        self.export_btn = self._make_action_button(
            "📂  Export Backup",
            "Save latest backup to USB / external drive",
            "#8b5cf6", "#7c3aed"
        )
        self.export_btn.clicked.connect(self._export_latest_backup)
        actions_row.addWidget(self.export_btn)

        # Restore button
        self.restore_btn = self._make_action_button(
            "📥  Restore from Backup",
            "Import a backup file to replace current data",
            ACCENT_DANGER, "#dc2626"
        )
        self.restore_btn.clicked.connect(self._restore_backup)
        actions_row.addWidget(self.restore_btn)

        actions_layout_outer.addLayout(actions_row)
        layout.addWidget(actions_frame)

        # ── Backup History Table ──
        history_frame = QFrame(self)
        history_frame.setObjectName("SmartCard")
        hist_layout = QVBoxLayout(history_frame)
        hist_layout.setContentsMargins(20, 18, 20, 18)
        hist_layout.setSpacing(12)

        hist_header = QHBoxLayout()
        hist_title = QLabel("📋  BACKUP HISTORY", self)
        hist_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY};")
        hist_header.addWidget(hist_title)
        hist_header.addStretch()

        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setObjectName("SecondaryActionButton")
        self.refresh_btn.setFixedWidth(110)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_data)
        hist_header.addWidget(self.refresh_btn)
        hist_layout.addLayout(hist_header)

        self.table = DataTable(
            ["Filename", "Date Created", "Size", "Actions"],
            self, enable_delete=False
        )
        hist_layout.addWidget(self.table)
        layout.addWidget(history_frame)

        layout.addStretch()

    def _init_status_card(self):
        """Build the dynamic backup health status card."""
        card_layout = QHBoxLayout(self.status_card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(20)

        # Status indicator dot + text
        left_section = QVBoxLayout()
        left_section.setSpacing(6)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(20)
        self.status_dot.setStyleSheet(f"font-size: 20px; color: {TEXT_SECONDARY};")
        status_row.addWidget(self.status_dot)

        self.status_title = QLabel("Checking backup status...")
        self.status_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY};")
        status_row.addWidget(self.status_title)
        status_row.addStretch()

        left_section.addLayout(status_row)

        self.status_subtitle = QLabel("Loading...")
        self.status_subtitle.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; padding-left: 30px;")
        left_section.addWidget(self.status_subtitle)

        card_layout.addLayout(left_section, 1)

        # Right side: backup count
        right_section = QVBoxLayout()
        right_section.setAlignment(Qt.AlignCenter)

        self.backup_count_lbl = QLabel("—")
        self.backup_count_lbl.setAlignment(Qt.AlignCenter)
        self.backup_count_lbl.setStyleSheet(f"""
            font-size: 28px; font-weight: bold; color: {ACCENT_PRIMARY};
        """)
        right_section.addWidget(self.backup_count_lbl)

        count_label = QLabel("Total Backups")
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        right_section.addWidget(count_label)

        card_layout.addLayout(right_section)

    def _make_action_button(self, text: str, subtitle: str, color: str, hover_color: str) -> QPushButton:
        """Create a styled action button with a subtitle."""
        btn = QPushButton(self)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setFixedHeight(80)

        # Use a widget inside the button for multi-line content
        btn_layout = QVBoxLayout(btn)
        btn_layout.setContentsMargins(16, 12, 16, 12)
        btn_layout.setSpacing(4)

        main_label = QLabel(text)
        main_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: white; background: transparent; border: none;")
        main_label.setAlignment(Qt.AlignCenter)
        main_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        btn_layout.addWidget(main_label)

        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet(f"font-size: 10px; color: rgba(255,255,255,0.7); background: transparent; border: none;")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        btn_layout.addWidget(sub_label)

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 10px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
                padding-top: 2px;
            }}
        """)

        return btn

    def _update_status_card(self, last_backup_time: str, total_count: int):
        """Update the status card indicator based on backup freshness."""
        self.backup_count_lbl.setText(str(total_count))

        if not last_backup_time or total_count == 0:
            # No backups — RED/Critical
            self.status_dot.setStyleSheet(f"font-size: 20px; color: {ACCENT_DANGER};")
            self.status_title.setText("No Backups Found")
            self.status_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {ACCENT_DANGER};")
            self.status_subtitle.setText("Your database is not backed up. Create a backup immediately!")
            self.status_card.setStyleSheet(f"""
                QFrame#SmartCard {{
                    background-color: {BG_SURFACE};
                    border: 1px solid {ACCENT_DANGER}40;
                    border-left: 4px solid {ACCENT_DANGER};
                    border-radius: 12px;
                }}
            """)
            return

        try:
            last_dt = datetime.strptime(last_backup_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            last_dt = datetime.now() - timedelta(days=30)

        age = datetime.now() - last_dt
        hours_ago = age.total_seconds() / 3600

        if hours_ago < 24:
            # GREEN — recent backup
            time_str = f"{int(hours_ago)} hour{'s' if int(hours_ago) != 1 else ''} ago" if hours_ago >= 1 else "Just now"
            self.status_dot.setStyleSheet(f"font-size: 20px; color: {ACCENT_SUCCESS};")
            self.status_title.setText("Database Secured")
            self.status_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {ACCENT_SUCCESS};")
            self.status_subtitle.setText(f"Last backup: {last_backup_time} ({time_str})")
            self.status_card.setStyleSheet(f"""
                QFrame#SmartCard {{
                    background-color: {BG_SURFACE};
                    border: 1px solid {ACCENT_SUCCESS}40;
                    border-left: 4px solid {ACCENT_SUCCESS};
                    border-radius: 12px;
                }}
            """)
        elif hours_ago < 168:  # 7 days
            days_ago = int(hours_ago / 24)
            self.status_dot.setStyleSheet(f"font-size: 20px; color: {ACCENT_WARNING};")
            self.status_title.setText("Backup Getting Old")
            self.status_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {ACCENT_WARNING};")
            self.status_subtitle.setText(f"Last backup: {last_backup_time} ({days_ago} day{'s' if days_ago != 1 else ''} ago). Consider taking a new backup.")
            self.status_card.setStyleSheet(f"""
                QFrame#SmartCard {{
                    background-color: {BG_SURFACE};
                    border: 1px solid {ACCENT_WARNING}40;
                    border-left: 4px solid {ACCENT_WARNING};
                    border-radius: 12px;
                }}
            """)
        else:
            days_ago = int(hours_ago / 24)
            self.status_dot.setStyleSheet(f"font-size: 20px; color: {ACCENT_DANGER};")
            self.status_title.setText("Backup Overdue!")
            self.status_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {ACCENT_DANGER};")
            self.status_subtitle.setText(f"Last backup: {last_backup_time} ({days_ago} days ago). Your data may be at risk!")
            self.status_card.setStyleSheet(f"""
                QFrame#SmartCard {{
                    background-color: {BG_SURFACE};
                    border: 1px solid {ACCENT_DANGER}40;
                    border-left: 4px solid {ACCENT_DANGER};
                    border-radius: 12px;
                }}
            """)

    def load_data(self):
        """Refresh backup list and status card."""
        try:
            data = client.get("/api/backup/list")
            backups = data.get("backups", [])
            total = data.get("total_count", 0)
            last_time = data.get("last_backup_time")

            self._update_status_card(last_time, total)
            self._populate_table(backups)
        except Exception as e:
            print(f"[Backup] Error loading data: {e}")
            self._update_status_card(None, 0)

    def _populate_table(self, backups: list):
        """Populate the history table with backup entries and action buttons."""
        self.table.clearContents()
        self.table.setRowCount(len(backups))

        # Reconfigure columns for custom action buttons
        header = self.table.horizontalHeader()
        from PySide6.QtWidgets import QHeaderView
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 160)

        from PySide6.QtWidgets import QTableWidgetItem

        for row_idx, backup in enumerate(backups):
            self.table.setItem(row_idx, 0, QTableWidgetItem(backup["filename"]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(backup["created_at"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(backup["size_display"]))

            # Action buttons widget
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            # Export button
            export_btn = QPushButton("📂")
            export_btn.setFixedSize(32, 28)
            export_btn.setToolTip("Export this backup")
            export_btn.setCursor(Qt.PointingHandCursor)
            export_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {BORDER_COLOR};
                    border-radius: 4px;
                    font-size: 13px; padding: 0;
                }}
                QPushButton:hover {{
                    background-color: {ACCENT_PRIMARY}30;
                    border-color: {ACCENT_PRIMARY};
                }}
            """)
            fname = backup["filename"]
            export_btn.clicked.connect(lambda checked, f=fname: self._export_specific_backup(f))
            actions_layout.addWidget(export_btn)

            # Delete button
            del_btn = QPushButton("🗑")
            del_btn.setFixedSize(32, 28)
            del_btn.setToolTip("Delete this backup")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {BORDER_COLOR};
                    border-radius: 4px;
                    font-size: 13px; padding: 0;
                }}
                QPushButton:hover {{
                    background-color: {ACCENT_DANGER}30;
                    border-color: {ACCENT_DANGER};
                }}
            """)
            del_btn.clicked.connect(lambda checked, f=fname: self._delete_backup(f))
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row_idx, 3, actions_widget)

    # ── Action Handlers ──────────────────────────────────────────────────────

    def _create_backup(self):
        """Create a new backup via the API."""
        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating...")
        try:
            result = client.post("/api/backup/create")
            if result.get("success"):
                if self._toast:
                    self._toast.show_message(
                        f"Backup created successfully!", "success"
                    )
                self.load_data()
            else:
                if self._toast:
                    self._toast.show_message("Backup creation failed", "error")
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error", 5000)
        finally:
            self.create_btn.setEnabled(True)
            # Restore button text by rebuilding inner labels
            self.create_btn.findChildren(QLabel)[0].setText("💾  Create Backup")

    def _export_latest_backup(self):
        """Export the latest backup (or show info if none exists)."""
        try:
            data = client.get("/api/backup/list")
            backups = data.get("backups", [])
            if not backups:
                if self._toast:
                    self._toast.show_message("No backups to export. Create one first!", "warning")
                return
            self._export_specific_backup(backups[0]["filename"])
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Error: {e}", "error")

    def _export_specific_backup(self, filename: str):
        """Export a specific backup file to user-chosen location."""
        try:
            result = client.get(f"/api/backup/export/{filename}")
            source_path = result.get("filepath")
            if not source_path:
                return

            # Open native Save As dialog
            dest_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Backup",
                filename,
                "ZIP Archives (*.zip)"
            )

            if dest_path:
                shutil.copy2(source_path, dest_path)
                if self._toast:
                    self._toast.show_message(f"Backup exported to {dest_path}", "success")

        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Export failed: {e}", "error", 5000)

    def _restore_backup(self):
        """Restore database from a backup ZIP file."""
        # Open file picker
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File to Restore",
            "",
            "ZIP Archives (*.zip)"
        )
        if not file_path:
            return

        # Critical confirmation dialog
        reply = QMessageBox.warning(
            self,
            "⚠️  Restore Database — CRITICAL",
            "This will OVERWRITE all current data including:\n\n"
            "  • All sales & shift records\n"
            "  • All purchases & expenses\n"
            "  • All employee data & reports\n"
            "  • All fuel prices & nozzle mappings\n\n"
            "This action CANNOT be undone.\n\n"
            "Are you absolutely sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Second confirmation
        reply2 = QMessageBox.question(
            self,
            "Final Confirmation",
            f"Restore from:\n{file_path}\n\nProceed with database restore?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply2 != QMessageBox.Yes:
            return

        try:
            # If the file is from an external location, copy it to backups dir first
            from pathlib import Path
            source = Path(file_path)
            filename = source.name

            # Check if it's already in backups directory
            from config import BASE_DIR
            backup_dir = BASE_DIR / "backups"
            target = backup_dir / filename

            if not target.exists():
                shutil.copy2(str(source), str(target))

            result = client.post("/api/backup/restore", data={"filename": filename})

            if result.get("success"):
                QMessageBox.information(
                    self,
                    "✅ Restore Complete",
                    "Database has been successfully restored.\n\n"
                    "The application will now reload data from the restored database."
                )
                if self._toast:
                    self._toast.show_message("Database restored successfully!", "success")
                self.load_data()
            else:
                if self._toast:
                    self._toast.show_message("Restore failed", "error")

        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Restore error: {e}", "error", 5000)

    def _delete_backup(self, filename: str):
        """Delete a backup file after confirmation."""
        reply = QMessageBox.question(
            self,
            "Delete Backup",
            f"Are you sure you want to delete:\n{filename}?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            client.delete(f"/api/backup/{filename}")
            if self._toast:
                self._toast.show_message(f"Backup deleted: {filename}", "success")
            self.load_data()
        except Exception as e:
            if self._toast:
                self._toast.show_message(f"Delete failed: {e}", "error", 5000)
