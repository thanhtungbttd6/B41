# file: gui/ui/ui_practice.py

import cv2
import base64
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QGroupBox, QComboBox, QApplication
)
import logging
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor, QIcon
from PySide6.QtCore import Qt, QSize, QPoint, QByteArray, Signal

logger = logging.getLogger(__name__)

class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 4.0 / 3.0
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignCenter)
        self._is_calibrating = False

    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        self.setToolTip("Click để chọn tâm ngắm mới" if active else "")

    def mousePressEvent(self, event):
        if self._is_calibrating and event.button() == Qt.LeftButton:
            self.clicked.emit(event.pos())
        super().mousePressEvent(event)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return int(width / self.aspect_ratio)

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        painter = QPainter(self)
        painter.drawPixmap(QPoint(int(x), int(y)), scaled_pixmap)


class MainGui(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setupUi()

    def setupUi(self):
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        self.scale_factor = screen_height / 1080.0

        def scale_size(base_size): return max(1, int(base_size * self.scale_factor))
        def scale_font(base_size): return max(9, int(base_size * self.scale_factor))

        self.setStyleSheet(f"""
            QWidget {{ background-color: #f8fafc; color: #1e293b; font-family: 'Segoe UI'; }}
            QFrame#panel {{ background-color: #ffffff; border-radius: {scale_size(12)}px; border: 1px solid #e2e8f0; }}
            QLabel#title {{ color: #1e293b; padding: {scale_size(10)}px; }}
            QLabel.panel-title {{ font-size: {scale_font(16)}px; font-weight: bold; color: #ffffff; padding: {scale_size(8)}px {scale_size(15)}px; background-color: #0ea5e9; border-radius: {scale_size(6)}px; }}
            QPushButton {{ background-color: #0ea5e9; color: white; font-size: {scale_font(14)}px; font-weight: bold; border: none; padding: {scale_size(10)}px {scale_size(20)}px; border-radius: {scale_size(8)}px; }}
            QPushButton:hover {{ background-color: #0284c7; }}
            QPushButton#danger {{ background-color: #ef4444; }}
            QPushButton#danger:hover {{ background-color: #dc2626; }}
            QPushButton:disabled {{ background-color: #cbd5e1; }}
            QSlider::groove:horizontal {{ border: 1px solid #e2e8f0; height: {scale_size(4)}px; background: #e2e8f0; margin: {scale_size(2)}px 0; border-radius: {scale_size(2)}px; }}
            QSlider::handle:horizontal {{ background: #0ea5e9; border: 1px solid #0ea5e9; width: {scale_size(18)}px; margin: -{scale_size(7)}px 0; border-radius: {scale_size(9)}px; }}
            VideoLabel {{ background-color: #e2e8f0; border: 1px solid #cbd5e1; border-radius: {scale_size(8)}px; color: #64748b; font-size: {scale_font(24)}px; }}
            #controlsPanel {{ padding: {scale_size(10)}px; }}
            #zoomValueLabel {{ font-size: {scale_font(13)}px; font-weight: bold; color: #0ea5e9; min-width: {scale_size(45)}px; }}
            QComboBox {{ border: 1px solid #cbd5e1; border-radius: {scale_size(4)}px; padding: {scale_size(5)}px; background-color: #ffffff; color: #1e293b; min-width: {scale_size(120)}px; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{ background-color: #ffffff; color: #1e293b; selection-background-color: #0ea5e9; }}
            #refreshButton {{ background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: {scale_size(5)}px {scale_size(10)}px; border-radius: {scale_size(4)}px; min-width: {scale_size(30)}px; color: #1e293b; }}
            #refreshButton:hover {{ background-color: #e2e8f0; }}
            QGroupBox {{ font-size: {scale_font(14)}px; font-weight: bold; border: 1px solid #cbd5e1; border-radius: {scale_size(8)}px; margin-top: {scale_size(10)}px; color: #1e293b; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: {scale_size(2)}px {scale_size(8)}px; background-color: #f1f5f9; color: #0ea5e9; border-radius: {scale_size(4)}px; border: 1px solid #cbd5e1; }}
        """)

        margin = scale_size(20)
        spacing = scale_size(15)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(margin, scale_size(10), margin, margin)
        root_layout.setSpacing(spacing)

        title_label = QLabel("MÀN HÌNH TẬP LUYỆN")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont('Segoe UI', scale_font(18), QFont.Bold)
        title_label.setFont(title_font)
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(scale_size(20))
        
        columns_layout.addWidget(self._create_camera_column(), 6)
        columns_layout.addWidget(self._create_right_column(), 4)
        root_layout.addLayout(columns_layout)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow_effect = QGraphicsDropShadowEffect(panel)
        shadow_effect.setBlurRadius(int(20 * self.scale_factor))
        shadow_effect.setColor(QColor(0, 0, 0, 30)) # Shadow nhạt đi cho Light Theme
        shadow_effect.setOffset(0, int(5 * self.scale_factor))
        panel.setGraphicsEffect(shadow_effect)
        return panel

    def _create_camera_column(self) -> QWidget:
        panel = self._create_styled_panel()
        margin = int(15 * self.scale_factor)
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(margin)

        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        title = QLabel("Đường ngắm trực tiếp")
        title.setProperty("class", "panel-title")
        title.setAlignment(Qt.AlignCenter)
        title_layout.addStretch(1)
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        main_layout.addWidget(title_widget)

        self.camera_view_label = VideoLabel()
        self.camera_view_label.setText("Vui lòng kết nối camera")
        main_layout.addWidget(self.camera_view_label, 1)

        controls_panel = QWidget()
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(int(5*self.scale_factor), int(5*self.scale_factor), int(5*self.scale_factor), 0)
        controls_layout.setSpacing(int(10 * self.scale_factor))
        
        self.camera_selector = QComboBox()
        self.camera_selector.setPlaceholderText("Chọn Camera...")
        self.camera_selector.setMinimumWidth(int(150 * self.scale_factor))
        controls_layout.addWidget(self.camera_selector)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.setObjectName("refreshButton")
        controls_layout.addWidget(self.refresh_button)

        controls_layout.addStretch(1)
        zoom_text_label = QLabel("Khoảng cách:")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(50)
        self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("zoomValueLabel")
        
        controls_layout.addWidget(zoom_text_label)
        controls_layout.addWidget(self.zoom_slider, 2)
        controls_layout.addWidget(self.zoom_value_label)
        controls_layout.addStretch(1)

        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        controls_layout.addWidget(self.calibrate_button)
        
        main_layout.addWidget(controls_panel)
        self.zoom_slider.valueChanged.connect(self._update_zoom_value_label)
        
        return panel
    
    def _update_zoom_value_label(self, value):
        zoom_factor = value / 10.0
        self.zoom_value_label.setText(f"{zoom_factor:.1f}x")

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        margin = int(20 * self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(margin)

        result_box = QGroupBox("Kết quả bắn")
        result_layout = QVBoxLayout(result_box)
        font_info = QFont('Segoe UI', max(9, int(12 * self.scale_factor)))
        
        self.time_label = QLabel("Thời gian: --:--:--")
        self.target_name_label = QLabel("Tên mục tiêu: --")
        self.score_label = QLabel("Kết quả: --")
        
        for label in [self.time_label, self.target_name_label, self.score_label]:
            label.setFont(font_info)
            result_layout.addWidget(label)
        
        result_image_title = QLabel("Ảnh kết quả:")
        result_image_title.setFont(font_info)
        result_layout.addWidget(result_image_title)
        
        self.result_image_label = VideoLabel()
        result_layout.addWidget(self.result_image_label, 1)

        layout.addWidget(result_box, 1)

        self.back_button = QPushButton("Về Menu Chính")
        self.back_button.setObjectName("danger")
        layout.addWidget(self.back_button)
        
        return panel

    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None: return QPixmap()
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)

    def display_frame(self, frame_bgr):
        if frame_bgr is None: return
        pixmap = self._convert_cv_to_pixmap(frame_bgr)
        self.camera_view_label.setPixmap(pixmap)

    def clear_video_feed(self, message: str):
        self.camera_view_label.setPixmap(QPixmap())
        self.camera_view_label.setText(message)

    def update_results(self, time_str, target_name, score, result_frame):
        self.time_label.setText(f"Thời gian: {time_str}")
        self.target_name_label.setText(f"Tên mục tiêu: {target_name}")
        self.score_label.setText(f"Kết quả: {score}")
        pixmap = self._convert_cv_to_pixmap(result_frame)
        if pixmap.isNull():
            self.result_image_label.setText("Không có ảnh kết quả")
            self.result_image_label.setPixmap(QPixmap())
        else:
            self.result_image_label.setText("") 
            self.result_image_label.setPixmap(pixmap)