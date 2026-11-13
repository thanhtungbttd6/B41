"""B41 - Trung Lien Window Controller."""

import logging

from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QPixmap

from ..ui.ui_trung_lien import TrungLienGui

logger = logging.getLogger(__name__)


class TrungLienWindow(QMainWindow):
    """Cửa sổ giao diện Trung liên độc lập."""

    def __init__(self, config=None):
        super().__init__()

        self.config = config or {}
        self.gui = TrungLienGui()

        self.setWindowTitle("LUYỆN TẬP TRUNG LIÊN")
        self.setMinimumSize(1100, 720)
        self.setCentralWidget(self.gui)

        self.back_button = self.gui.back_button

        logger.info("Đã khởi tạo giao diện Trung liên.")

    def reset_ui_state(self):
        """Đưa giao diện về trạng thái ban đầu."""

        self.gui.camera_view_label.setPixmap(QPixmap())
        self.gui.camera_view_label.setText("Camera Trung liên chưa được kết nối")

        self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Kết quả: --")

        self.gui.result_image_label.setPixmap(QPixmap())
        self.gui.result_image_label.setText("Chưa có ảnh kết quả")
