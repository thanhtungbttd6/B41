"""Main Menu Window Controller."""

import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow

from config import APP_DATA_DIR
from utils.branding import find_branding_image, footer_text, get_branding
from utils.resource_path import resource_path

from ..ui.ui_main_menu import Ui_MainMenuWindow

logger = logging.getLogger(__name__)


class MainMenuWindow(QMainWindow):

    def __init__(self, config: dict):
        super().__init__()

        self.config = config
        self.ui = Ui_MainMenuWindow()
        self.ui.setupUi(self)

        self._load_application_icon()
        self.apply_branding()

        # GIỮ TƯƠNG THÍCH VỚI APPLICATION CONTROLLER
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.settings_button = self.ui.settings_button
        self.exit_button = self.ui.exit_button

    # ==============================================
    # GIAO DIỆN DO NGƯỜI DÙNG CÀI ĐẶT
    # ==============================================

    def apply_branding(self):
        """Áp dụng tiêu đề, chân trang, logo và ảnh nền chìm theo cài đặt hiện tại.

        Mục để trống thì không hiển thị. Gọi lại sau khi người dùng lưu cài đặt.
        """
        branding = get_branding(self.config)

        self._set_text_or_hide(self.ui.customer_title_label, branding["title_1"])
        self._set_text_or_hide(self.ui.title_label, branding["title_2"])
        self._set_text_or_hide(self.ui.footer_label, footer_text(branding))

        self._load_single_logo(branding["logo_left"], self.ui.logo_left, "LEFT")
        self._load_single_logo(branding["logo_right"], self.ui.logo_right, "RIGHT")
        self._load_watermark(branding["watermark_image"])
        self.set_watermark_opacity(branding["watermark_opacity"] / 100.0)

    @staticmethod
    def _set_text_or_hide(label, text: str):
        # Gõ \n trong ô cài đặt để xuống dòng
        text = (text or "").replace("\\n", "\n").strip()
        label.setText(text)
        label.setVisible(bool(text))

    def _find_image_path(self, path_raw):
        """Tìm hình ảnh trong thư mục dữ liệu và thư mục ứng dụng."""
        return find_branding_image(path_raw)

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
        """Nạp logo và giữ nguyên tỷ lệ hình ảnh. Để trống hoặc không có ảnh thì xóa logo."""

        label_widget.clear()

        if not path_raw:
            return

        image_path = self._find_image_path(path_raw)

        if not image_path:
            logger.warning("Không tìm thấy logo %s: %s", position_name, path_raw)
            return

        pixmap = QPixmap(image_path)

        if pixmap.isNull():
            logger.error("Không thể đọc logo %s: %s", position_name, image_path)
            return

        label_widget.setPixmap(
            pixmap.scaled(
                label_widget.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        logger.info("Đã nạp logo %s: %s", position_name, image_path)

    # ==============================================
    # WATERMARK BACKGROUND
    # ==============================================

    def _load_watermark(self, watermark_path):
        """Nạp ảnh nền in chìm cho màn hình menu. Để trống thì xóa ảnh nền."""

        self.ui.watermark_label.set_watermark(QPixmap())

        if not watermark_path:
            return

        image_path = self._find_image_path(watermark_path)

        if not image_path:
            logger.warning("Không tìm thấy ảnh nền in chìm: %s", watermark_path)
            return

        pixmap = QPixmap(image_path)

        if pixmap.isNull():
            logger.error("Không thể đọc ảnh nền in chìm: %s", image_path)
            return

        self.ui.watermark_label.set_watermark(pixmap)

        logger.info("Đã nạp ảnh nền in chìm: %s", image_path)

    def set_watermark_opacity(self, opacity: float):
        """Điều chỉnh độ mờ ảnh nền trong khoảng 0.0 đến 1.0."""

        self.ui.watermark_label.set_opacity(opacity)
