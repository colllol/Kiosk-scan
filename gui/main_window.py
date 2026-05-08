"""
Kiosk Scan GUI - Main Window
Tích hợp Backend (FastAPI), Frontend (Webcam Scan), Chrome Extension
"""

import sys
import os
import json
import subprocess
import signal
import threading
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QTextEdit, QLabel, QGroupBox,
    QStatusBar, QMessageBox, QSplitter, QFrame, QCheckBox,
    QComboBox, QLineEdit, QFileDialog, QSpacerItem, QSizePolicy,
    QGridLayout, QScrollArea
)
from PyQt5.QtCore import (
    Qt, QUrl, QProcess, QTimer, pyqtSignal, QObject, QSize, QThread
)
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QColor, QPalette, QTextCharFormat
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtWebEngineCore import QWebEnginePage as QWebEngineCorePage


# ========== CUSTOM WEB ENGINE PAGE ==========
class CustomWebEnginePage(QWebEnginePage):
    """Custom QWebEnginePage để xử lý window.open() và mở tab mới"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_handler = None
        self.new_window_created = pyqtSignal(QWebEngineView)  # Tín hiệu khi tạo cửa sổ mới
    
    def set_log_handler(self, log_handler):
        """Gán log handler để ghi log"""
        self.log_handler = log_handler
    
    def createWindow(self, window_type):
        """Ghi đè phương thức createWindow để xử lý window.open()"""
        if self.log_handler:
            self.log_handler.log_message.emit(f"[WebEngine] window.open() requested - type: {window_type}")
        
        # Tạo một QWebEnginePage mới (đây là cách đúng để xử lý window.open())
        new_page = CustomWebEnginePage()
        new_page.set_log_handler(self.log_handler)
        
        # Tạo một QWebEngineView mới để chứa page này
        new_view = QWebEngineView()
        new_view.setPage(new_page)
        
        # Thiết lập các thuộc tính cho view mới
        new_view.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        new_view.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        new_view.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        
        # Kết nối tín hiệu để biết khi trang được load xong
        new_view.loadFinished.connect(lambda ok: self._on_new_window_loaded(new_view, ok))
        
        # Phát tín hiệu để thông báo có cửa sổ mới được tạo
        self.new_window_created.emit(new_view)
        
        return new_page
    
    def _on_new_window_loaded(self, view, ok):
        """Xử lý khi tab mới được load xong"""
        if self.log_handler:
            status = "success" if ok else "failed"
            url = view.url().toString()
            self.log_handler.log_message.emit(f"[WebEngine] New window loaded: {status} - URL: {url}")
        
        # Hiển thị cửa sổ mới
        view.setWindowTitle("Dịch vụ công - Cửa sổ mới")
        view.resize(1024, 768)
        view.show()


# ========== CONFIGURATION ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # e:\Kiosk-scan
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
CHROME_EXT_DIR = os.path.join(PROJECT_DIR, "chrome-extension")

BACKEND_SCRIPT = os.path.join(BACKEND_DIR, "main.py")
FRONTEND_INDEX = os.path.join(FRONTEND_DIR, "index.html")
EXTENSION_POPUP = os.path.join(CHROME_EXT_DIR, "popup.html")

BACKEND_PORT = 5000
FRONTEND_PORT = 3000

# Load config.json
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG_DATA = json.load(f)
    BACKEND_PORT = CONFIG_DATA.get("backendSettings", {}).get("port", 5000)
except Exception:
    CONFIG_DATA = {}


# ========== LOG HANDLER ==========
class LogHandler(QObject):
    """Handler để chuyển log từ thread khác sang main thread"""
    log_signal = pyqtSignal(str, str)  # message, level

    def emit_log(self, message, level="info"):
        self.log_signal.emit(message, level)


# ========== BACKEND PROCESS MANAGER ==========
class BackendManager(QObject):
    """Quản lý process backend FastAPI"""
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(bool)  # True=running, False=stopped

    def __init__(self):
        super().__init__()
        self.process = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return False

        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.setWorkingDirectory(BACKEND_DIR)

        # Set environment variables
        env = self.process.processEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        # Quan trong: set HOME va USERPROFILE de tranh loi "Could not determine home directory"
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            env.insert("USERPROFILE", user_profile)
            env.insert("HOME", user_profile)
            env.insert("HOMEDRIVE", os.environ.get("HOMEDRIVE", ""))
            env.insert("HOMEPATH", os.environ.get("HOMEPATH", ""))
            env.insert("USERNAME", os.environ.get("USERNAME", ""))
            env.insert("APPDATA", os.environ.get("APPDATA", ""))
            env.insert("LOCALAPPDATA", os.environ.get("LOCALAPPDATA", ""))
        self.process.setProcessEnvironment(env)

        # Connect signals
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._on_finished)

        # Start backend - DUNG VENV PYTHON (no fastapi, uvicorn, ...)
        venv_python = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            python_exe = venv_python
        else:
            python_exe = sys.executable
        self.process.start(python_exe, ["-u", BACKEND_SCRIPT])
        self.is_running = True
        self.status_signal.emit(True)
        return True

    def stop(self):
        if self.process and self.is_running:
            self.process.terminate()
            if not self.process.waitForFinished(5000):
                self.process.kill()
                self.process.waitForFinished(3000)
            self.is_running = False
            self.status_signal.emit(False)
            return True
        return False

    def _read_output(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self.output_signal.emit(data)

    def _on_finished(self, exit_code, exit_status):
        self.is_running = False
        self.status_signal.emit(False)
        self.error_signal.emit(f"Backend process exited with code {exit_code}")

    def is_alive(self):
        return self.is_running and self.process and self.process.state() == QProcess.Running


# ========== FRONTEND HTTP SERVER (Python built-in) ==========
class FrontendServerManager(QObject):
    """Quản lý HTTP server cho frontend (dùng Python http.server)"""
    output_signal = pyqtSignal(str)
    status_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.process = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return False

        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.setWorkingDirectory(FRONTEND_DIR)

        env = self.process.processEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(env)

        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._on_finished)

        python_exe = sys.executable
        self.process.start(python_exe, [
            "-u", "-m", "http.server",
            str(FRONTEND_PORT),
            "--bind", "127.0.0.1"
        ])
        self.is_running = True
        self.status_signal.emit(True)
        return True

    def stop(self):
        if self.process and self.is_running:
            self.process.terminate()
            if not self.process.waitForFinished(5000):
                self.process.kill()
                self.process.waitForFinished(3000)
            self.is_running = False
            self.status_signal.emit(False)
            return True
        return False

    def _read_output(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self.output_signal.emit(data)

    def _on_finished(self, exit_code, exit_status):
        self.is_running = False
        self.status_signal.emit(False)

    def is_alive(self):
        return self.is_running and self.process and self.process.state() == QProcess.Running


# ========== LOG WIDGET ==========
class LogWidget(QTextEdit):
    """Widget hiển thị log với màu sắc"""
    COLORS = {
        "info": QColor("#e0e0e0"),
        "success": QColor("#4caf50"),
        "warning": QColor("#ff9800"),
        "error": QColor("#f44336"),
        "debug": QColor("#9e9e9e"),
        "system": QColor("#2196f3"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.setMinimumHeight(150)

    def append_log(self, message, level="info"):
        color = self.COLORS.get(level, self.COLORS["info"])
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Format level tag
        level_tag = f"[{level.upper():7}]"

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Timestamp
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#666666"))
        cursor.insertText(f"{timestamp} ", fmt)

        # Level tag
        fmt.setForeground(color)
        cursor.insertText(f"{level_tag} ", fmt)

        # Message
        fmt.setForeground(self.COLORS["info"])
        cursor.insertText(f"{message}\n", fmt)

        # Auto scroll
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_log(self):
        self.clear()


# ========== STATUS INDICATOR ==========
class StatusIndicator(QFrame):
    """Đèn báo trạng thái (xanh/đỏ)"""

    def __init__(self, label_text="Status", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedSize(16, 16)
        self.set_off()

    def set_on(self):
        self.setStyleSheet("""
            background-color: #4caf50;
            border-radius: 8px;
            border: 2px solid #388e3c;
        """)

    def set_off(self):
        self.setStyleSheet("""
            background-color: #f44336;
            border-radius: 8px;
            border: 2px solid #c62828;
        """)

    def set_warning(self):
        self.setStyleSheet("""
            background-color: #ff9800;
            border-radius: 8px;
            border: 2px solid #e65100;
        """)


# ========== BACKEND TAB ==========
class BackendTab(QWidget):
    """Tab quản lý Backend FastAPI"""

    def __init__(self, log_handler, parent=None):
        super().__init__(parent)
        self.log_handler = log_handler
        self.backend_manager = BackendManager()
        self.frontend_server = FrontendServerManager()

        # Connect signals
        self.backend_manager.output_signal.connect(self._on_backend_output)
        self.backend_manager.status_signal.connect(self._on_backend_status)
        self.frontend_server.output_signal.connect(self._on_frontend_output)
        self.frontend_server.status_signal.connect(self._on_frontend_status)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === Control Panel ===
        control_group = QGroupBox("Điều khiển")
        control_layout = QGridLayout(control_group)

        # Row 0: Backend controls
        self.backend_status_led = StatusIndicator()
        backend_status_label = QLabel("Backend API:")
        self.btn_backend = QPushButton("▶ Start Backend")
        self.btn_backend.setMinimumHeight(36)
        self.btn_backend.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1976d2; }
            QPushButton:disabled { background-color: #666; }
        """)
        self.btn_backend.clicked.connect(self._toggle_backend)

        control_layout.addWidget(backend_status_label, 0, 0)
        control_layout.addWidget(self.backend_status_led, 0, 1)
        control_layout.addWidget(self.btn_backend, 0, 2)

        # Row 1: Frontend server controls
        self.frontend_status_led = StatusIndicator()
        frontend_status_label = QLabel("Frontend Server:")
        self.btn_frontend = QPushButton("▶ Start Frontend")
        self.btn_frontend.setMinimumHeight(36)
        self.btn_frontend.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:disabled { background-color: #666; }
        """)
        self.btn_frontend.clicked.connect(self._toggle_frontend)

        control_layout.addWidget(frontend_status_label, 1, 0)
        control_layout.addWidget(self.frontend_status_led, 1, 1)
        control_layout.addWidget(self.btn_frontend, 1, 2)

        # Row 2: Quick actions
        actions_layout = QHBoxLayout()
        self.btn_start_all = QPushButton("▶ Start All")
        self.btn_start_all.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #f57c00; }
        """)
        self.btn_start_all.clicked.connect(self._start_all)

        self.btn_stop_all = QPushButton("⏹ Stop All")
        self.btn_stop_all.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.btn_stop_all.clicked.connect(self._stop_all)

        self.btn_clear_log = QPushButton("🗑 Clear Log")
        self.btn_clear_log.setStyleSheet("""
            QPushButton {
                background-color: #607d8b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #546e7a; }
        """)
        self.btn_clear_log.clicked.connect(self._clear_log)

        actions_layout.addWidget(self.btn_start_all)
        actions_layout.addWidget(self.btn_stop_all)
        actions_layout.addWidget(self.btn_clear_log)
        actions_layout.addStretch()

        control_layout.addLayout(actions_layout, 2, 0, 1, 3)

        layout.addWidget(control_group)

        # === Log Console ===
        log_group = QGroupBox("Console Log")
        log_layout = QVBoxLayout(log_group)

        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)

        layout.addWidget(log_group, stretch=1)

        # Initial log
        self.log_handler.log_signal.connect(self.log_widget.append_log)
        self._log("system", "Kiosk Scan GUI - Khởi động thành công")
        self._log("system", f"Backend script: {BACKEND_SCRIPT}")
        self._log("system", f"Frontend directory: {FRONTEND_DIR}")
        self._log("system", f"Backend port: {BACKEND_PORT}, Frontend port: {FRONTEND_PORT}")

    def _log(self, level, message):
        self.log_handler.emit_log(message, level)

    def _toggle_backend(self):
        if self.backend_manager.is_alive():
            self.backend_manager.stop()
        else:
            self.backend_manager.start()

    def _toggle_frontend(self):
        if self.frontend_server.is_alive():
            self.frontend_server.stop()
        else:
            self.frontend_server.start()

    def _start_all(self):
        self._log("system", "=== Starting all services ===")
        if not self.backend_manager.is_alive():
            self.backend_manager.start()
        if not self.frontend_server.is_alive():
            self.frontend_server.start()

    def _stop_all(self):
        self._log("system", "=== Stopping all services ===")
        self.frontend_server.stop()
        self.backend_manager.stop()

    def _clear_log(self):
        self.log_widget.clear_log()
        self._log("system", "Log cleared")

    def _on_backend_output(self, text):
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Phân loại log level
            lower = line.lower()
            if any(w in lower for w in ["error", "exception", "traceback", "failed"]):
                self._log("error", line)
            elif any(w in lower for w in ["warning", "warn"]):
                self._log("warning", line)
            elif any(w in lower for w in ["success", "✅", "completed"]):
                self._log("success", line)
            elif any(w in lower for w in ["info", "startup", "loaded"]):
                self._log("info", line)
            else:
                self._log("debug", line)

    def _on_backend_status(self, running):
        if running:
            self.backend_status_led.set_on()
            self.btn_backend.setText("⏹ Stop Backend")
            self.btn_backend.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #d32f2f; }
            """)
            self._log("success", f"✅ Backend started on port {BACKEND_PORT}")
        else:
            self.backend_status_led.set_off()
            self.btn_backend.setText("▶ Start Backend")
            self.btn_backend.setStyleSheet("""
                QPushButton {
                    background-color: #2196f3;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #1976d2; }
            """)
            self._log("system", "⏹ Backend stopped")

    def _on_frontend_output(self, text):
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            self._log("debug", f"[Frontend] {line}")

    def _on_frontend_status(self, running):
        if running:
            self.frontend_status_led.set_on()
            self.btn_frontend.setText("⏹ Stop Frontend")
            self.btn_frontend.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #d32f2f; }
            """)
            self._log("success", f"✅ Frontend server started on port {FRONTEND_PORT}")
        else:
            self.frontend_status_led.set_off()
            self.btn_frontend.setText("▶ Start Frontend")
            self.btn_frontend.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #388e3c; }
            """)
            self._log("system", "⏹ Frontend server stopped")

    def closeEvent(self, event):
        """Dọn dẹp khi đóng tab"""
        self._stop_all()
        super().closeEvent(event)


# ========== FRONTEND TAB (Webcam Scan) ==========
class FrontendTab(QWidget):
    """Tab hiển thị Frontend Webcam Scan qua QWebEngineView"""

    def __init__(self, log_handler, parent=None):
        super().__init__(parent)
        self.log_handler = log_handler
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-bottom: 1px solid #444;
            }
        """)
        toolbar.setFixedHeight(44)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 4, 12, 4)

        title_label = QLabel("📷 Webcam Scan - Quét tài liệu")
        title_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 14px;")

        self.btn_reload = QPushButton("🔄 Reload")
        self.btn_reload.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #777; }
        """)
        self.btn_reload.clicked.connect(self._reload)

        self.btn_home = QPushButton("🏠 Home")
        self.btn_home.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #777; }
        """)
        self.btn_home.clicked.connect(self._go_home)

        self.url_label = QLabel("URL: http://localhost:3000")
        self.url_label.setStyleSheet("color: #999; font-size: 11px;")

        toolbar_layout.addWidget(title_label)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.url_label)
        toolbar_layout.addSpacing(10)
        toolbar_layout.addWidget(self.btn_home)
        toolbar_layout.addWidget(self.btn_reload)

        layout.addWidget(toolbar)

        # WebView với CustomWebEnginePage để hỗ trợ window.open()
        self.webview = QWebEngineView()
        
        # Tạo và thiết lập CustomWebEnginePage
        self.custom_page = CustomWebEnginePage()
        self.custom_page.set_log_handler(self.log_handler)
        self.webview.setPage(self.custom_page)
        
        # Kết nối tín hiệu khi có cửa sổ mới được tạo
        self.custom_page.new_window_created.connect(self._on_new_window_created)
        
        # Cấu hình settings
        self.webview.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.webview.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.webview.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.webview.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        self.webview.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        self.webview.settings().setAttribute(QWebEngineSettings.WebGLEnabled, True)
        self.webview.settings().setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        self.webview.settings().setAttribute(QWebEngineSettings.AutoLoadImages, True)
        self.webview.settings().setAttribute(QWebEngineSettings.ErrorPageEnabled, False)
        
        # Cho phép mở cửa sổ mới (popup)
        self.webview.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        self.webview.settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)

        # Cho phép camera qua getUserMedia
        self.webview.page().featurePermissionRequested.connect(self._on_permission_requested)

        layout.addWidget(self.webview, stretch=1)

        # Status bar
        status_bar = QFrame()
        status_bar.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-top: 1px solid #444;
            }
        """)
        status_bar.setFixedHeight(28)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(12, 2, 12, 2)

        self.status_label = QLabel("⏳ Vui lòng Start Frontend Server ở tab Backend trước")
        self.status_label.setStyleSheet("color: #ff9800; font-size: 11px;")

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(status_bar)

    def _on_permission_requested(self, url, feature):
        """Tự động cấp quyền camera cho frontend"""
        # PyQt5 5.15: feature constants are on QWebEnginePage, not QWebEngineSettings
        media_features = [
            QWebEnginePage.MediaAudioCapture,
            QWebEnginePage.MediaVideoCapture,
            QWebEnginePage.MediaAudioVideoCapture,
        ]
        if feature in media_features:
            self.webview.page().setFeaturePermission(
                url, feature, QWebEnginePage.PermissionGrantedByUser
            )
    
    def _on_new_window_created(self, new_view):
        """Xử lý khi có cửa sổ mới được tạo từ window.open()"""
        if self.log_handler:
            self.log_handler.log_message.emit("[FrontendTab] New window created via window.open()")
        
        # Thiết lập tiêu đề và kích thước cho cửa sổ mới
        new_view.setWindowTitle("Dịch vụ công - Cửa sổ mới")
        new_view.resize(1024, 768)
        
        # Hiển thị cửa sổ mới
        new_view.show()

    def load_frontend(self):
        """Load frontend từ local server"""
        url = f"http://127.0.0.1:{FRONTEND_PORT}/index.html"
        self.webview.load(QUrl(url))
        self.url_label.setText(f"URL: {url}")
        self.status_label.setText("✅ Frontend loaded")
        self.status_label.setStyleSheet("color: #4caf50; font-size: 11px;")

    def load_frontend_direct(self):
        """Load frontend trực tiếp từ file (fallback)"""
        url = QUrl.fromLocalFile(FRONTEND_INDEX)
        self.webview.load(url)
        self.url_label.setText(f"File: {FRONTEND_INDEX}")
        self.status_label.setText("⚠️ Direct file mode (API calls may fail)")
        self.status_label.setStyleSheet("color: #ff9800; font-size: 11px;")

    def _reload(self):
        self.webview.reload()

    def _go_home(self):
        self.load_frontend()


# ========== CHROME EXTENSION TAB ==========
class ExtensionTab(QWidget):
    """Tab hiển thị Chrome Extension popup + điều khiển"""

    def __init__(self, log_handler, parent=None):
        super().__init__(parent)
        self.log_handler = log_handler
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === Extension Info ===
        info_group = QGroupBox("📋 Chrome Extension - Auto Fill Form")
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel(
            "Extension: <b>Auto Fill Form - Dịch Vụ Công</b><br>"
            "Tự động điền thông tin vào form dịch vụ công từ dữ liệu API JSON<br><br>"
            "<b>Hướng dẫn:</b><br>"
            "1. Mở Chrome và truy cập <code>chrome://extensions</code><br>"
            "2. Bật <b>Developer mode</b><br>"
            "3. Chọn <b>Load unpacked</b> và chọn thư mục:<br>"
            f"&nbsp;&nbsp;<code>{CHROME_EXT_DIR}</code><br>"
            "4. Extension sẽ xuất hiện trên thanh công cụ<br>"
            "5. Truy cập <code>https://dichvucong.thainguyen.gov.vn</code> để sử dụng"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #ccc; font-size: 13px; padding: 8px; line-height: 1.6;")
        info_text.setTextFormat(Qt.RichText)
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # === Extension Popup Preview ===
        preview_group = QGroupBox("🔍 Extension Popup Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.ext_webview = QWebEngineView()
        self.ext_webview.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.ext_webview.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.ext_webview.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

        # Load popup.html
        popup_url = QUrl.fromLocalFile(EXTENSION_POPUP)
        self.ext_webview.load(popup_url)

        preview_layout.addWidget(self.ext_webview, stretch=1)

        layout.addWidget(preview_group, stretch=1)

        # === Actions ===
        actions_group = QGroupBox("⚙️ Thao tác nhanh")
        actions_layout = QHBoxLayout(actions_group)

        self.btn_reload_ext = QPushButton("🔄 Reload Extension Popup")
        self.btn_reload_ext.setStyleSheet("""
            QPushButton {
                background-color: #9c27b0;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #7b1fa2; }
        """)
        self.btn_reload_ext.clicked.connect(self._reload_extension)

        self.btn_open_ext_dir = QPushButton("📂 Open Extension Folder")
        self.btn_open_ext_dir.setStyleSheet("""
            QPushButton {
                background-color: #607d8b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #546e7a; }
        """)
        self.btn_open_ext_dir.clicked.connect(self._open_extension_folder)

        actions_layout.addWidget(self.btn_reload_ext)
        actions_layout.addWidget(self.btn_open_ext_dir)
        actions_layout.addStretch()

        layout.addWidget(actions_group)

    def _reload_extension(self):
        self.ext_webview.reload()
        self.log_handler.emit_log("Extension popup reloaded", "info")

    def _open_extension_folder(self):
        import subprocess
        subprocess.Popen(['explorer', CHROME_EXT_DIR])


# ========== MAIN WINDOW ==========
class MainWindow(QMainWindow):
    """Cửa sổ chính của Kiosk Scan GUI"""

    def __init__(self):
        super().__init__()
        self.log_handler = LogHandler()
        self._setup_ui()
        self._setup_menu()
        self._apply_theme()

    def _setup_ui(self):
        self.setWindowTitle("Kiosk Scan - Hệ thống quét tài liệu")
        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === Tabs ===
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #999;
                border: none;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #2196f3;
                border-bottom: 3px solid #2196f3;
            }
            QTabBar::tab:hover:!selected {
                background-color: #383838;
                color: #ccc;
            }
        """)

        # Tab 1: Backend
        self.backend_tab = BackendTab(self.log_handler)
        self.tabs.addTab(self.backend_tab, "⚙️ Backend")

        # Tab 2: Frontend
        self.frontend_tab = FrontendTab(self.log_handler)
        self.tabs.addTab(self.frontend_tab, "📷 Frontend")

        # Tab 3: Chrome Extension
        self.extension_tab = ExtensionTab(self.log_handler)
        self.tabs.addTab(self.extension_tab, "🔌 Extension")

        layout.addWidget(self.tabs)

        # === Status Bar ===
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #252525;
                color: #999;
                border-top: 1px solid #333;
                padding: 4px 12px;
                font-size: 12px;
            }
        """)
        self.setStatusBar(self.status_bar)

        # Status indicators in status bar
        self.backend_indicator = StatusIndicator()
        self.frontend_indicator = StatusIndicator()

        self.status_bar.addPermanentWidget(QLabel("Backend:"))
        self.status_bar.addPermanentWidget(self.backend_indicator)
        self.status_bar.addPermanentWidget(QLabel("  Frontend:"))
        self.status_bar.addPermanentWidget(self.frontend_indicator)
        self.status_bar.addPermanentWidget(QLabel("  "))

        self.status_label = QLabel("Sẵn sàng")
        self.status_bar.addWidget(self.status_label)

        # Connect backend status to main status bar
        self.backend_tab.backend_manager.status_signal.connect(self._on_backend_status)
        self.backend_tab.frontend_server.status_signal.connect(self._on_frontend_server_status)

    def _setup_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2d2d2d;
                color: #ccc;
                border-bottom: 1px solid #444;
                padding: 2px;
            }
            QMenuBar::item:selected {
                background-color: #444;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #ccc;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background-color: #2196f3;
            }
        """)

        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Start All Services", self.backend_tab._start_all)
        file_menu.addAction("Stop All Services", self.backend_tab._stop_all)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Backend Tab", lambda: self.tabs.setCurrentIndex(0))
        view_menu.addAction("Frontend Tab", lambda: self.tabs.setCurrentIndex(1))
        view_menu.addAction("Extension Tab", lambda: self.tabs.setCurrentIndex(2))

        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About", self._show_about)

    def _apply_theme(self):
        """Apply dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                background-color: #252525;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 16px;
                padding: 16px 12px 12px 12px;
                font-weight: bold;
                font-size: 13px;
                color: #ccc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                background-color: #333;
                border-radius: 4px;
                color: #2196f3;
            }
            QLabel {
                color: #ccc;
            }
            QPushButton {
                color: white;
            }
        """)

    def _on_backend_status(self, running):
        if running:
            self.backend_indicator.set_on()
        else:
            self.backend_indicator.set_off()

    def _on_frontend_server_status(self, running):
        if running:
            self.frontend_indicator.set_on()
            self.frontend_tab.load_frontend()
            self.status_label.setText("Frontend server đang chạy - Đã load giao diện")
        else:
            self.frontend_indicator.set_off()
            self.status_label.setText("Frontend server đã dừng")

    def _show_about(self):
        QMessageBox.about(self, "About Kiosk Scan GUI",
            "<h3>Kiosk Scan - Hệ thống quét tài liệu</h3>"
            "<p>Phiên bản 1.0.0</p>"
            "<p>Tích hợp:</p>"
            "<ul>"
            "<li>Backend FastAPI - Xử lý ảnh, tạo PDF</li>"
            "<li>Frontend Webcam Scan - Quét tài liệu</li>"
            "<li>Chrome Extension - Auto Fill Form</li>"
            "</ul>"
            "<p>© 2026 - Dịch vụ công tỉnh Thái Nguyên</p>"
        )

    def closeEvent(self, event):
        """Dọn dẹp khi đóng ứng dụng"""
        reply = QMessageBox.question(
            self, "Xác nhận thoát",
            "Bạn có chắc muốn thoát? Tất cả dịch vụ sẽ được dừng lại.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.backend_tab._stop_all()
            event.accept()
        else:
            event.ignore()


# ========== MAIN ==========
def main():
    """Entry point"""
    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Kiosk Scan GUI")
    app.setOrganizationName("ThaiNguyenDVC")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()