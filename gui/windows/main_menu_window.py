"""B41 - Main Menu Window Controller."""

import os
import logging

from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt

from ..ui.ui_main_menu import Ui_MainMenuWindow
from utils.resource_path import resource_path
from config import APP_DATA_DIR

logger = logging.getLogger(__name__)


class MainMenuWindow(QMainWindow):

    def __init__(self, config: dict):
        super().__init__()

        self.config = config
        self.ui = Ui_MainMenuWindow()
        self.ui.setupUi(self)

        self._apply_labels()
        self._load_application_icon()
        self._load_logos()
        self._load_watermark()

        # GIỮ TƯƠNG THÍCH VỚI APPLICATION CONTROLLER
        self.practice_button = self.ui.practice_button
        self.exit_button = self.ui.exit_button
        self.trung_lien_button = self.ui.trung_lien_button

    # ==============================================
    # APPLICATION LABELS
    # ==============================================

    def _apply_labels(self):
        self.ui.customer_title_label.setText("SÁNG KIẾN CẢI TIẾN KỸ THUẬT")

        self.ui.title_label.setText(
            "ỨNG DỤNG AI KIỂM TRA ĐƯỜNG NGẮM\n" "SÚNG HỎA LỰC BỘ BINH"
        )

        labels = self.config.get("labels", {})
        footer_text = labels.get(
            "app_footer",
            "Thông tin cá nhân\nThông tin đơn vị",
        )

        if not footer_text:
            footer_text = "Thông tin cá nhân\nThông tin đơn vị"

        self.ui.footer_label.setText(footer_text)

    # ==============================================
    # FILE PATH
    # ==============================================

    def _find_image_path(self, path_raw):
        """Tìm hình ảnh trong thư mục dữ liệu và thư mục ứng dụng."""

        if not path_raw:
            return None

        candidates = [
            path_raw,
            os.path.join(APP_DATA_DIR, "assets", os.path.basename(path_raw)),
            os.path.join(APP_DATA_DIR, path_raw),
            resource_path(path_raw),
            resource_path(os.path.join("assets", os.path.basename(path_raw))),
        ]

        checked_paths = set()

        for candidate in candidates:
            full_path = os.path.abspath(os.path.normpath(candidate))

            if full_path in checked_paths:
                continue

            checked_paths.add(full_path)

            if os.path.isfile(full_path):
                return full_path

        return None

    # ==============================================
    # APPLICATION ICON
    # ==============================================

    def _load_application_icon(self):
        """Nạp icon ứng dụng từ assets."""

        icon_candidates = [
            os.path.join(APP_DATA_DIR, "assets", "app_icon.ico"),
            resource_path(os.path.join("assets", "app_icon.ico")),
            os.path.join(APP_DATA_DIR, "assets", "app_icon.png"),
            resource_path(os.path.join("assets", "app_icon.png")),
        ]

        for icon_path in icon_candidates:
            if not os.path.isfile(icon_path):
                continue

            icon = QIcon(icon_path)

            if icon.isNull():
                logger.warning("Không thể đọc icon: %s", icon_path)
                continue

            self.setWindowIcon(icon)

            application = QApplication.instance()

            if application is not None:
                application.setWindowIcon(icon)

            logger.info("Đã nạp icon ứng dụng: %s", icon_path)
            return

        logger.warning("Không tìm thấy icon ứng dụng trong assets.")

    # ==============================================
    # LOGO LOADING
    # ==============================================

    def _load_single_logo(self, path_raw, label_widget, position_name):
        """Nạp logo và giữ nguyên tỷ lệ hình ảnh."""

        image_path = self._find_image_path(path_raw)

        if not image_path:
            logger.warning(
                "Không tìm thấy logo %s: %s",
                position_name,
                path_raw,
            )
            return

        pixmap = QPixmap(image_path)

        if pixmap.isNull():
            logger.error(
                "Không thể đọc logo %s: %s",
                position_name,
                image_path,
            )
            return

        scaled_pixmap = pixmap.scaled(
            label_widget.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        label_widget.setPixmap(scaled_pixmap)

        logger.info("Đã nạp logo %s: %s", position_name, image_path)

    def _load_logos(self):
        """Nạp logo trái và logo phải."""

        labels_config = self.config.get("labels", {})

        left_path = (
            self.config.get("logo_left")
            or labels_config.get("logo_left")
            or "logo_left.png"
        )

        right_path = (
            self.config.get("logo_right")
            or labels_config.get("logo_right")
            or "logo_right.png"
        )

        self._load_single_logo(
            left_path,
            self.ui.logo_left,
            "LEFT",
        )

        self._load_single_logo(
            right_path,
            self.ui.logo_right,
            "RIGHT",
        )

    # ==============================================
    # WATERMARK BACKGROUND
    # ==============================================

    def _load_watermark(self):
        """Nạp ảnh nền in chìm cho màn hình menu."""

        watermark_path = self.config.get("watermark_image") or "watermark.png"

        image_path = self._find_image_path(watermark_path)

        if not image_path:
            logger.warning(
                "Chưa có ảnh nền watermark. " "Đặt watermark.png trong thư mục assets."
            )
            return

        pixmap = QPixmap(image_path)

        if pixmap.isNull():
            logger.error(
                "Không thể đọc ảnh nền watermark: %s",
                image_path,
            )
            return

        self.ui.watermark_label.set_watermark(pixmap)

        logger.info("Đã nạp ảnh nền in chìm: %s", image_path)

    # ==============================================
    # WATERMARK SETTINGS
    # ==============================================

    def set_watermark_opacity(self, opacity: float):
        """Điều chỉnh độ mờ ảnh nền trong khoảng 0.0 đến 1.0."""

        self.ui.watermark_label.set_opacity(opacity)

    def set_watermark_image(self, image_path: str):
        """Cho phép thay ảnh nền mà không cần khởi động lại ứng dụng."""

        full_path = self._find_image_path(image_path)

        if not full_path:
            logger.warning(
                "Không tìm thấy ảnh nền mới: %s",
                image_path,
            )
            return False

        pixmap = QPixmap(full_path)

        if pixmap.isNull():
            logger.error(
                "Không thể đọc ảnh nền mới: %s",
                full_path,
            )
            return False

        self.ui.watermark_label.set_watermark(pixmap)

        logger.info("Đã thay ảnh nền: %s", full_path)
        return True
