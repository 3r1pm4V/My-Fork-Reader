from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QLabel, QDialogButtonBox, QMessageBox,
    QCheckBox, QGroupBox, QHBoxLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
import requests
import logging

class SyncDialog(QDialog):
    """
    Dialog for managing user credentials and monitoring KOReader synchronization status.
    """
    sync_requested = pyqtSignal()
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Synchronization Settings")
        self.resize(450, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Status Group ---
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; color: #555;")
        status_layout.addWidget(self.status_label)
        
        self.last_sync_label = QLabel("Last Sync: Never")
        status_layout.addWidget(self.last_sync_label)
        
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("Test Connection")
        self.btn_test.clicked.connect(self._test_connection)
        btn_layout.addWidget(self.btn_test)
        
        self.btn_sync_now = QPushButton("Sync Now")
        self.btn_sync_now.clicked.connect(self._on_sync_now)
        self.btn_sync_now.setEnabled(self.config.sync.enabled)
        btn_layout.addWidget(self.btn_sync_now)
        
        status_layout.addLayout(btn_layout)
        layout.addWidget(status_group)

        # --- Credentials Group ---
        cred_group = QGroupBox("KOReader Sync Credentials")
        form = QFormLayout(cred_group)
        
        self.enabled_cb = QCheckBox("Enable Background Sync")
        self.enabled_cb.setChecked(self.config.sync.enabled)
        self.enabled_cb.toggled.connect(self._on_enabled_toggled)
        form.addRow(self.enabled_cb)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        form.addRow(line)

        self.url_edit = QLineEdit(self.config.sync.url)
        self.url_edit.setPlaceholderText("https://sync.koreader.rocks")
        form.addRow("Server URL:", self.url_edit)
        
        self.user_edit = QLineEdit(self.config.sync.username)
        self.user_edit.setPlaceholderText("Username")
        form.addRow("Username:", self.user_edit)
        
        self.pass_edit = QLineEdit(self.config.sync.password)
        self.pass_edit.setPlaceholderText("Password or API Key")
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password/Key:", self.pass_edit)
        
        self.device_edit = QLineEdit(self.config.sync.device_id)
        form.addRow("Device ID:", self.device_edit)
        
        layout.addWidget(cred_group)
        
        # --- Actions ---
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _on_enabled_toggled(self, checked):
        self.btn_sync_now.setEnabled(checked)

    def _test_connection(self):
        self.status_label.setText("Testing connection...")
        self.status_label.setStyleSheet("color: blue;")
        
        url = self.url_edit.text().rstrip('/') + "/koreader/sync/v1/auth"
        headers = {
            "x-auth-user": self.user_edit.text(),
            "x-auth-key": self.pass_edit.text(),
            "User-Agent": "ereader-py/0.1.0"
        }
        
        try:
            # KOReader sync protocol check
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                self.status_label.setText("Connection Successful!")
                self.status_label.setStyleSheet("font-weight: bold; color: green;")
                QMessageBox.information(self, "Success", "Connected to KOReader sync server successfully!")
            else:
                self.status_label.setText(f"Failed (HTTP {resp.status_code})")
                self.status_label.setStyleSheet("font-weight: bold; color: red;")
                QMessageBox.warning(self, "Failed", f"Server returned error: {resp.status_code}\nCheck your credentials.")
        except Exception as e:
            self.status_label.setText("Connection Error")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            QMessageBox.critical(self, "Error", f"Could not connect to server:\n{str(e)}")

    def _on_sync_now(self):
        self.status_label.setText("Manual sync requested...")
        self.sync_requested.emit()
        # If parent has a manual sync method, we could trigger it directly if needed
        if hasattr(self.parent(), "_manual_sync_pull"):
            self.parent()._manual_sync_pull()
            self.status_label.setText("Sync operation complete.")
            self.status_label.setStyleSheet("color: green;")

    def _on_accept(self):
        self.config.sync.enabled = self.enabled_cb.isChecked()
        self.config.sync.url = self.url_edit.text()
        self.config.sync.username = self.user_edit.text()
        self.config.sync.password = self.pass_edit.text()
        self.config.sync.device_id = self.device_edit.text()
        
        logging.info("Sync configuration updated.")
        self.accept()

__all__ = ["SyncDialog"]
