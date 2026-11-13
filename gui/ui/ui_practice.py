"""B41 - Practice Screen UI."""

import cv2

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QFrame,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import COLORS, scaled, add_soft_shadow


class VideoLabel(QLabel):
    """Widget hiển thị hình ảnh camera và hỗ trợ chọn tâm."""

    clicked = Signal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 4.0 / 3.0
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignCenter)
        self._is_calibrating = False
        self.setMinimumSize(180, 140)

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

        scaled_pixmap = self._pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(QPoint(x, y), scaled_pixmap)


class MainGui(QWidget):
    """Giao diện màn hình luyện tập B41."""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setupUi()

    def setupUi(self):
        screen = QApplication.primaryScreen()
        screen_height = screen.availableGeometry().height() if screen else 1080
        self.scale_factor = max(0.82, min(1.18, screen_height / 1080.0))

        def s(value):
            return scaled(value, self.scale_factor)

        def f(value):
            return max(9, scaled(value, self.scale_factor))

        self.setObjectName("PracticeScreen")
        self.setStyleSheet(f"""
            QWidget#PracticeScreen {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                font-family: 'Segoe UI', 'Aptos', 'Arial', sans-serif;
            }}
            QFrame#panel {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(18)}px;
            }}
            QLabel#screenTitle {{
                color: {COLORS['text']};
                font-size: {f(22)}px;
                font-weight: 800;
                padding: {s(4)}px;
                background: transparent;
            }}
            QLabel.panel-title {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border: 1px solid #D9E5FF;
                border-radius: {s(10)}px;
                padding: {s(9)}px {s(16)}px;
                font-size: {f(14)}px;
                font-weight: 700;
            }}
            QLabel#timeLabel, QLabel#targetNameLabel, QLabel#scoreLabel {{
                color: {COLORS['text']};
                background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(10)}px;
                padding: {s(11)}px {s(13)}px;
                font-size: {f(12)}px;
                font-weight: 600;
            }}
            QLabel#scoreLabel {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border-color: #D9E5FF;
                font-size: {f(14)}px;
                font-weight: 800;
            }}
            QLabel#resultImageTitle {{
                color: {COLORS['text_secondary']};
                font-size: {f(11)}px;
                font-weight: 700;
                background: transparent;
                padding-top: {s(4)}px;
            }}
            QPushButton {{
                min-height: {s(40)}px;
                padding: {s(8)}px {s(15)}px;
                color: #FFFFFF;
                background-color: {COLORS['primary']};
                border: 0;
                border-radius: {s(10)}px;
                font-size: {f(11)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary_pressed']};
            }}
            QPushButton:disabled {{
                color: #FFFFFF;
                background-color: #B8C4D6;
            }}
            QPushButton:focus {{
                border: 2px solid #A9C2FF;
            }}
            QPushButton#danger {{
                color: {COLORS['danger']};
                background-color: {COLORS['danger_soft']};
                border: 1px solid #F3D2D2;
            }}
            QPushButton#danger:hover {{
                color: #FFFFFF;
                background-color: {COLORS['danger']};
                border-color: {COLORS['danger']};
            }}
            QPushButton#refreshButton {{
                min-width: {s(78)}px;
                min-height: {s(36)}px;
                padding: {s(6)}px {s(11)}px;
                color: {COLORS['text']};
                background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {s(9)}px;
            }}
            QPushButton#refreshButton:hover {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border-color: #B9CCFF;
            }}
            QPushButton#calibrateButton[calibrating="true"] {{
                color: #8A5A00;
                background-color: {COLORS['warning_soft']};
                border: 1px solid #F1D9A8;
            }}
            QComboBox {{
                min-height: {s(36)}px;
                min-width: {s(125)}px;
                padding: {s(4)}px {s(10)}px;
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {s(9)}px;
                selection-background-color: {COLORS['primary']};
            }}
            QComboBox:hover {{
                border-color: #9CB7F5;
            }}
            QComboBox:focus {{
                border: 1px solid {COLORS['primary']};
            }}
            QComboBox::drop-down {{
                width: {s(27)}px;
                border: 0;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}
            QComboBox QAbstractItemView {{
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['primary_soft']};
                selection-color: {COLORS['primary']};
                outline: 0;
                padding: {s(4)}px;
            }}
            QSlider::groove:horizontal {{
                height: {s(6)}px;
                background: #E7ECF4;
                border: 0;
                border-radius: {s(3)}px;
                margin: {s(5)}px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['primary']};
                border-radius: {s(3)}px;
            }}
            QSlider::add-page:horizontal {{
                background: #E7ECF4;
                border-radius: {s(3)}px;
            }}
            QSlider::handle:horizontal {{
                width: {s(17)}px;
                height: {s(17)}px;
                margin: -{s(6)}px 0;
                background: #FFFFFF;
                border: 3px solid {COLORS['primary']};
                border-radius: {s(10)}px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLORS['primary_soft']};
                border-color: {COLORS['primary_hover']};
            }}
            QLabel#zoomValueLabel {{
                min-width: {s(48)}px;
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border-radius: {s(8)}px;
                padding: {s(5)}px;
                font-size: {f(11)}px;
                font-weight: 800;
            }}
            VideoLabel {{
                color: #D0D5DD;
                background-color: {COLORS['video_background']};
                border: 1px solid #344054;
                border-radius: {s(13)}px;
                font-size: {f(13)}px;
                font-weight: 600;
                padding: {s(4)}px;
            }}
            QGroupBox {{
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(13)}px;
                margin-top: {s(14)}px;
                padding: {s(16)}px {s(12)}px {s(12)}px;
                font-size: {f(13)}px;
                font-weight: 800;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {s(14)}px;
                padding: {s(3)}px {s(9)}px;
                color: {COLORS['primary']};
                background-color: {COLORS['surface']};
            }}
        """)

        # MAIN LAYOUT
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(s(22), s(18), s(22), s(22))
        root_layout.setSpacing(s(16))

        title_label = QLabel("MÀN HÌNH TẬP LUYỆN")
        title_label.setObjectName("screenTitle")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", f(22), QFont.Bold))
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(s(18))
        columns_layout.addWidget(self._create_camera_column(), 6)
        columns_layout.addWidget(self._create_right_column(), 4)
        root_layout.addLayout(columns_layout, 1)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        add_soft_shadow(
            panel,
            blur=scaled(28, self.scale_factor),
            y_offset=scaled(7, self.scale_factor),
            alpha=17,
        )
        return panel

    def _create_camera_column(self) -> QWidget:
        panel = self._create_styled_panel()
        margin = scaled(17, self.scale_factor)
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(margin)

        # CAMERA TITLE
        title_widget = QWidget()
        title_widget.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        title = QLabel("ĐƯỜNG NGẮM TRỰC TIẾP")
        title.setProperty("class", "panel-title")
        title.setAlignment(Qt.AlignCenter)
        title_layout.addStretch(1)
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        main_layout.addWidget(title_widget)

        # CAMERA DISPLAY
        self.camera_view_label = VideoLabel()
        self.camera_view_label.setText("Vui lòng kết nối camera")
        self.camera_view_label.setMinimumHeight(scaled(300, self.scale_factor))
        main_layout.addWidget(self.camera_view_label, 1)

        # CAMERA CONTROL BAR
        controls_panel = QWidget()
        controls_panel.setStyleSheet("background: transparent;")
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(
            scaled(4, self.scale_factor),
            scaled(5, self.scale_factor),
            scaled(4, self.scale_factor),
            0,
        )
        controls_layout.setSpacing(scaled(9, self.scale_factor))

        self.camera_selector = QComboBox()
        self.camera_selector.setPlaceholderText("Chọn Camera...")
        self.camera_selector.setMinimumWidth(scaled(135, self.scale_factor))
        controls_layout.addWidget(self.camera_selector)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        controls_layout.addWidget(self.refresh_button)

        controls_layout.addSpacing(scaled(5, self.scale_factor))

        zoom_text_label = QLabel("Thu phóng")
        zoom_text_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-weight: 600; background: transparent;"
        )

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(50)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setMinimumWidth(scaled(90, self.scale_factor))

        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("zoomValueLabel")
        self.zoom_value_label.setAlignment(Qt.AlignCenter)

        controls_layout.addWidget(zoom_text_label)
        controls_layout.addWidget(self.zoom_slider, 2)
        controls_layout.addWidget(self.zoom_value_label)

        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        self.calibrate_button.setObjectName("calibrateButton")
        self.calibrate_button.setCursor(Qt.PointingHandCursor)
        controls_layout.addWidget(self.calibrate_button)

        main_layout.addWidget(controls_panel)
        self.zoom_slider.valueChanged.connect(self._update_zoom_value_label)
        return panel

    def _update_zoom_value_label(self, value):
        self.zoom_value_label.setText(f"{value / 10.0:.1f}x")

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        margin = scaled(18, self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(scaled(13, self.scale_factor))

        # RESULT GROUP
        result_box = QGroupBox("KẾT QUẢ GHI NHẬN")
        result_layout = QVBoxLayout(result_box)
        result_layout.setContentsMargins(
            scaled(12, self.scale_factor),
            scaled(18, self.scale_factor),
            scaled(12, self.scale_factor),
            scaled(12, self.scale_factor),
        )
        result_layout.setSpacing(scaled(10, self.scale_factor))

        font_info = QFont(
            "Segoe UI",
            max(9, scaled(11, self.scale_factor)),
        )

        self.time_label = QLabel("Thời gian: --:--:--")
        self.time_label.setObjectName("timeLabel")

        self.target_name_label = QLabel("Tên mục tiêu: --")
        self.target_name_label.setObjectName("targetNameLabel")

        self.score_label = QLabel("Kết quả: --")
        self.score_label.setObjectName("scoreLabel")

        for label in (self.time_label, self.target_name_label, self.score_label):
            label.setFont(font_info)
            label.setWordWrap(True)
            result_layout.addWidget(label)

        result_image_title = QLabel("HÌNH ẢNH KẾT QUẢ")
        result_image_title.setObjectName("resultImageTitle")
        result_layout.addWidget(result_image_title)

        self.result_image_label = VideoLabel()
        self.result_image_label.setText("Chưa có ảnh kết quả")
        self.result_image_label.setMinimumHeight(scaled(230, self.scale_factor))
        result_layout.addWidget(self.result_image_label, 1)

        layout.addWidget(result_box, 1)

        # BACK BUTTON
        self.back_button = QPushButton("Về Menu Chính")
        self.back_button.setObjectName("danger")
        self.back_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.back_button)
        return panel

    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None:
            return QPixmap()

        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_image.shape
        bytes_per_line = channels * width

        qt_image = QImage(
            rgb_image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        )
        return QPixmap.fromImage(qt_image.copy())

    def display_frame(self, frame_bgr):
        if frame_bgr is None:
            return
        self.camera_view_label.setPixmap(self._convert_cv_to_pixmap(frame_bgr))

    def clear_video_feed(self, message: str):
        self.camera_view_label.setPixmap(QPixmap())
        self.camera_view_label.setText(message)

    def update_results(self, time_str, target_name, score, result_frame):
        self.time_label.setText(f"Thời gian: {time_str}")
        self.target_name_label.setText(f"Tên mục tiêu: {target_name}")
        self.score_label.setText(f"Kết quả: {score}")

        if score == "TRÚNG":
            self.score_label.setStyleSheet(f"""
                color: {COLORS['success']};
                background-color: {COLORS['success_soft']};
                border: 1px solid #BFE9D8;
                border-radius: 10px;
                padding: 11px 13px;
                font-weight: 800;
            """)
        elif score == "TRƯỢT":
            self.score_label.setStyleSheet(f"""
                color: {COLORS['danger']};
                background-color: {COLORS['danger_soft']};
                border: 1px solid #F3D2D2;
                border-radius: 10px;
                padding: 11px 13px;
                font-weight: 800;
            """)
        else:
            self.score_label.setStyleSheet("")

        pixmap = self._convert_cv_to_pixmap(result_frame)
        if pixmap.isNull():
            self.result_image_label.setText("Không có ảnh kết quả")
            self.result_image_label.setPixmap(QPixmap())
        else:
            self.result_image_label.setText("")
            self.result_image_label.setPixmap(pixmap)
