# file: main.py
import json
import logging
import multiprocessing
import os
import shutil
import sys

from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QProxyStyle,
    QStackedWidget,
    QStyleFactory,
)

# Bắt buộc thêm đoạn này để ép Python in toàn bộ log INFO ra terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

from PySide6.QtCore import QThread
from PySide6.QtGui import QColor, QFont, QIcon, QPalette

from config import APP_DATA_DIR
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.trung_lien_window import TrungLienWindow
from utils.license_manager import verify_key
from utils.resource_path import resource_path

log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] (%(name)s) - %(message)s")
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

logging.info("--- Application Started ---")

# --- GIAO DIỆN SÁNG (LIGHT THEME) ---
GLOBAL_STYLESHEET = """
    QWidget {
        color: #1e293b;
        font-family: 'Segoe UI', sans-serif;
    }
    QMessageBox {
        background-color: #ffffff;
    }
    QMessageBox QLabel {
        color: #1e293b;
    }
    QMessageBox QPushButton {
        background-color: #f1f5f9;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 5px 15px;
        min-width: 60px;
    }
    QMessageBox QPushButton:hover {
        background-color: #e2e8f0;
    }
    QLineEdit {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 5px;
        selection-background-color: #0ea5e9;
        selection-color: white;
    }
    QComboBox {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 5px;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #1e293b;
        selection-background-color: #0ea5e9;
        selection-color: white;
        border: 1px solid #cbd5e1;
    }
    QScrollBar:vertical {
        border: none;
        background: #f8fafc;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #cbd5e1;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
"""


def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, "license.key")
    if os.path.exists(license_file_path):
        try:
            with open(license_file_path, "r", encoding="utf-8") as f:
                key = f.read().strip()
            if verify_key(key):
                logging.info("License hợp lệ.")
                return True
            else:
                logging.warning("License không hợp lệ hoặc đã hết hạn.")
                os.remove(license_file_path)
        except Exception as e:
            logging.error(f"Lỗi đọc file license: {e}")

    while True:
        key, ok = QInputDialog.getText(
            None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key để tiếp tục:"
        )
        if not ok:
            return False
        if verify_key(key):
            try:
                with open(license_file_path, "w", encoding="utf-8") as f:
                    f.write(key)
                QMessageBox.information(
                    None, "Thành công", "Kích hoạt phần mềm thành công!"
                )
                return True
            except Exception as e:
                QMessageBox.critical(None, "Lỗi", f"Không thể lưu license: {e}")
                return False
        else:
            QMessageBox.warning(
                None, "Lỗi", "License Key không hợp lệ. Vui lòng kiểm tra lại."
            )


class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self._ensure_assets_are_in_appdata()

        app_title = self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng")
        self.setWindowTitle(app_title)
        self.setStyleSheet(
            "background-color: #f8fafc;"
        )  # Màu nền sáng cho container chính

        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()

        self.processing_thread.setObjectName("ProcessingThread")
        self.processing_worker.moveToThread(self.processing_thread)

        self.main_menu = MainMenuWindow(self.config)
        self.practice_screen = PracticeWindow(
            worker=self.processing_worker, trigger=self.bt_trigger, config=self.config
        )

        self.trung_lien_screen = TrungLienWindow(config=self.config)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)
        self.stacked_widget.addWidget(self.trung_lien_screen)
        self.connect_signals()

        self.processing_thread.start()
        self.bt_trigger.start_global_listener()

    def _load_config(self) -> dict:
        config_filename = "config.json"
        dest_path = os.path.join(APP_DATA_DIR, config_filename)
        if not os.path.exists(dest_path):
            source_path = resource_path(config_filename)
            if os.path.exists(source_path):
                try:
                    shutil.copyfile(source_path, dest_path)
                    logging.info(f"Đã khởi tạo config mặc định tại: {dest_path}")
                except Exception as e:
                    logging.error(f"Lỗi khởi tạo config: {e}")
        if os.path.exists(dest_path):
            try:
                with open(dest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Lỗi đọc config.json: {e}")
        return {}

    def _ensure_assets_are_in_appdata(self):
        dest_assets_dir = os.path.join(APP_DATA_DIR, "assets")
        os.makedirs(dest_assets_dir, exist_ok=True)

        model_filename = self.config.get("yolo_model_name")
        if model_filename:
            dest_model_path = os.path.join(APP_DATA_DIR, model_filename)
            if not os.path.exists(dest_model_path):
                source_model_path = resource_path(
                    os.path.join("assets", "models", model_filename)
                )
                if os.path.exists(source_model_path):
                    try:
                        shutil.copyfile(source_model_path, dest_model_path)
                    except Exception as e:
                        logging.error(f"Lỗi sao chép model: {e}")

        target_logos = ["logo_left.png", "logo_right.png"]
        for filename in target_logos:
            dest_path = os.path.join(dest_assets_dir, filename)
            if not os.path.exists(dest_path):
                source_path = resource_path(os.path.join("assets", filename))
                if os.path.exists(source_path):
                    try:
                        shutil.copyfile(source_path, dest_path)
                    except Exception as e:
                        logging.error(f"Lỗi khi copy {filename}: {e}")

    def connect_signals(self):
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)
        self.main_menu.trung_lien_button.clicked.connect(self.show_trung_lien_screen)
        self.practice_screen.gui.back_button.clicked.connect(self.show_main_menu)
        self.trung_lien_screen.back_button.clicked.connect(self.show_main_menu)
        self.main_menu.exit_button.clicked.connect(self.close)

        self.practice_screen.request_processing.connect(
            self.processing_worker.process_image
        )
        self.processing_worker.finished.connect(
            self.practice_screen.on_processing_finished
        )
        self.bt_trigger.triggered.connect(self.practice_screen.capture_photo)

    def cleanup_before_exit(self):
        # Giải phóng camera của cả hai màn hình trước khi thoát
        self.practice_screen.disconnect_camera()
        self.trung_lien_screen.disconnect_camera()

        if self.bt_trigger:
            self.bt_trigger.stop_global_listener()
        if self.processing_thread.isRunning():
            self.processing_thread.quit()
            if not self.processing_thread.wait(3000):
                self.processing_thread.terminate()

    def show_trung_lien_screen(self):
        self.trung_lien_screen.start_camera()
        self.stacked_widget.setCurrentWidget(self.trung_lien_screen)

    def show_main_menu(self):
        current_widget = self.stacked_widget.currentWidget()

        if current_widget == self.practice_screen:
            self.practice_screen.shutdown_components()

        elif current_widget == self.trung_lien_screen:
            self.trung_lien_screen.shutdown_components()

        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_practice_screen(self):
        self.practice_screen.start_camera()
        self.stacked_widget.setCurrentWidget(self.practice_screen)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)

    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_STYLESHEET)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    icon_path = resource_path("assets/app_icon.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()
