from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QWidget, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, 
    QComboBox, QPushButton, QFormLayout, QDialogButtonBox,
    QListWidget, QFileDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal
from pathlib import Path
import logging

from ereader.config import Config, save_config

class SettingsDialog(QDialog):
    """
    Comprehensive settings dialog for the E-Reader.
    Organized into tabs: Reading, Library, TTS, Sync, Advanced.
    """
    settings_changed = pyqtSignal(Config)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tabs creation
        self.tabs.addTab(self._create_reading_tab(), "Reading")
        self.tabs.addTab(self._create_library_tab(), "Library")
        self.tabs.addTab(self._create_cache_tab(), "Cache")
        self.tabs.addTab(self._create_tts_tab(), "TTS")
        self.tabs.addTab(self._create_sync_tab(), "Sync")
        self.tabs.addTab(self._create_advanced_tab(), "Advanced")

        # Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Apply
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)
        layout.addWidget(self.buttons)

    def _create_reading_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.font_family = QComboBox()
        self.font_family.addItems(["Arial", "Times New Roman", "Verdana", "Georgia", "Courier New"])
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        
        self.line_height = QDoubleSpinBox()
        self.line_height.setRange(1.0, 3.0)
        self.line_height.setSingleStep(0.1)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark", "sepia"])

        layout.addRow("Font Family:", self.font_family)
        layout.addRow("Font Size:", self.font_size)
        layout.addRow("Line Height:", self.line_height)
        layout.addRow("Theme:", self.theme_combo)

        return widget

    def _create_library_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Library Folders:"))
        self.folder_list = QListWidget()
        layout.addWidget(self.folder_list)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Folder")
        btn_add.clicked.connect(self._add_folder)
        btn_remove = QPushButton("Remove")
        btn_remove.clicked.connect(self._remove_folder)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        layout.addLayout(btn_layout)

        return widget

    def _create_cache_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()

        self.cache_enabled = QCheckBox("Enable Content Caching")
        self.cache_max_size = QSpinBox()
        self.cache_max_size.setRange(50, 5000)
        self.cache_max_size.setSuffix(" MB")
        
        self.cache_clear_startup = QCheckBox("Clear cache on startup")
        
        form.addRow(self.cache_enabled)
        form.addRow("Max Cache Size:", self.cache_max_size)
        form.addRow(self.cache_clear_startup)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Info & Actions
        self.cache_info_label = QLabel("Current Cache Size: Calculating...")
        layout.addWidget(self.cache_info_label)
        
        btn_clear = QPushButton("Clear All Cache Now")
        btn_clear.clicked.connect(self._clear_cache_now)
        layout.addWidget(btn_clear)
        
        btn_vacuum = QPushButton("Vacuum Database (Reclaim Space)")
        btn_vacuum.clicked.connect(self._vacuum_db)
        layout.addWidget(btn_vacuum)

        return widget

    def _clear_cache_now(self):
        reply = QMessageBox.question(self, "Confirm", "Delete all cached book content?")
        if reply == QMessageBox.StandardButton.Yes:
            # Note: We need a reference to DB. For now assuming it's available or we trigger signal.
            # In this app structure, MainWindow passes db but SettingsDialog doesn't have it yet.
            # Let's assume we'll pass it in __init__ if needed, or better, emit a signal.
            # For simplicity, we'll try to find parent with db.
            parent = self.parent()
            if hasattr(parent, 'db'):
                parent.db.clear_all_cache()
                self._update_cache_info()
                QMessageBox.information(self, "Success", "Cache cleared.")

    def _vacuum_db(self):
        parent = self.parent()
        if hasattr(parent, 'db'):
            parent.db.vacuum()
            QMessageBox.information(self, "Success", "Database vacuumed.")

    def _update_cache_info(self):
        parent = self.parent()
        if hasattr(parent, 'db'):
            size_bytes = parent.db.cache_size_bytes()
            size_mb = size_bytes / (1024 * 1024)
            self.cache_info_label.setText(f"Current Cache Size: {size_mb:.2f} MB")

    def _create_tts_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.tts_rate = QSpinBox()
        self.tts_rate.setRange(50, 400)
        
        self.tts_volume = QDoubleSpinBox()
        self.tts_volume.setRange(0.0, 1.0)
        self.tts_volume.setSingleStep(0.1)

        layout.addRow("Speech Rate:", self.tts_rate)
        layout.addRow("Volume:", self.tts_volume)

        return widget

    def _create_sync_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.sync_enabled = QComboBox()
        self.sync_enabled.addItems(["Disabled", "Enabled"])
        
        self.sync_url = QLineEdit()
        self.sync_url.setPlaceholderText("https://sync.koreader.rocks")
        
        self.sync_user = QLineEdit()
        self.sync_pass = QLineEdit()
        self.sync_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.sync_device = QLineEdit()
        
        layout.addRow("Sync State:", self.sync_enabled)
        layout.addRow("Server URL:", self.sync_url)
        layout.addRow("Username:", self.sync_user)
        layout.addRow("Password:", self.sync_pass)
        layout.addRow("Device ID:", self.sync_device)
        
        return widget

    def _create_advanced_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        
        btn_reset = QPushButton("Reset to Defaults")
        btn_reset.clicked.connect(self._reset_config)
        
        form = QFormLayout()
        form.addRow("Log Level:", self.log_level)
        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(btn_reset)

        return widget

    def _load_settings(self):
        """Populates UI with current config values."""
        cfg = self.config
        self.font_family.setCurrentText(cfg.reading.font_family)
        self.font_size.setValue(cfg.reading.font_size)
        self.line_height.setValue(cfg.reading.line_height)
        self.theme_combo.setCurrentText(cfg.reading.theme)
        
        self.cache_enabled.setChecked(cfg.cache.enabled)
        self.cache_max_size.setValue(cfg.cache.max_size_mb)
        self.cache_clear_startup.setChecked(cfg.cache.clear_on_startup)
        self._update_cache_info()
        
        # Library
        self.folder_list.clear()
        for folder in cfg.library.folders:
            self.folder_list.addItem(folder)
        if not cfg.library.folders and cfg.library.path:
            self.folder_list.addItem(cfg.library.path)
        
        self.tts_rate.setValue(cfg.tts.rate)
        self.tts_volume.setValue(cfg.tts.volume)
        
        # Sync
        self.sync_enabled.setCurrentText("Enabled" if cfg.sync.enabled else "Disabled")
        self.sync_url.setText(cfg.sync.url)
        self.sync_user.setText(cfg.sync.username)
        self.sync_pass.setText(cfg.sync.password)
        self.sync_device.setText(cfg.sync.device_id)
        
        self.log_level.setCurrentText(cfg.logging.level)

    def _apply_settings(self):
        """Saves UI values to config and emits signal."""
        cfg = self.config
        cfg.reading.font_family = self.font_family.currentText()
        cfg.reading.font_size = self.font_size.value()
        cfg.reading.line_height = self.line_height.value()
        cfg.reading.theme = self.theme_combo.currentText()
        
        cfg.cache.enabled = self.cache_enabled.isChecked()
        cfg.cache.max_size_mb = self.cache_max_size.value()
        cfg.cache.clear_on_startup = self.cache_clear_startup.isChecked()
        
        # Library
        folders = []
        for i in range(self.folder_list.count()):
            folders.append(self.folder_list.item(i).text())
        cfg.library.folders = folders
        if folders:
            cfg.library.path = folders[0] # Primary path
        
        cfg.tts.rate = self.tts_rate.value()
        cfg.tts.volume = self.tts_volume.value()
        
        # Sync
        cfg.sync.enabled = self.sync_enabled.currentText() == "Enabled"
        cfg.sync.url = self.sync_url.text()
        cfg.sync.username = self.sync_user.text()
        cfg.sync.password = self.sync_pass.text()
        cfg.sync.device_id = self.sync_device.text()
        
        cfg.logging.level = self.log_level.currentText()

        save_config(cfg)
        self.settings_changed.emit(cfg)
        logging.info("Settings applied and saved.")

    def accept(self):
        self._apply_settings()
        super().accept()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_list.addItem(folder)

    def _remove_folder(self):
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))

    def _reset_config(self):
        reply = QMessageBox.question(self, "Confirm", "Reset all settings to default?")
        if reply == QMessageBox.StandardButton.Yes:
            self.config = Config()
            self._load_settings()
            self._apply_settings()
