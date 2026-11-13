"""B41 - Trung Lien Practice UI.
Giao diện độc lập, hiển thị camera và hỗ trợ chọn tâm giống màn hình B41.
"""

import cv2

from PySide6.QtCore import Qt, QSize, QPoint, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QFrame,
    QGroupBox,
    QComboBox,
    QSizePolicy,
)

from .theme import COLORS, scaled, add_soft_shadow


class ToggleSwitch(QAbstractButton):
    """Công tắc bật/tắt dạng trượt (iOS style)."""

    def __init__(self, width=44, height=24, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(width, height)

    def sizeHint(self):
        return QSize(self.width(), self.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)

        track_color = QColor(COLORS["primary"] if self.isChecked() else "#CBD5E1")
        painter.setBrush(track_color)
        radius = self.height() / 2
        painter.drawRoundedRect(self.rect(), radius, radius)

        margin = 3
        knob_d = self.height() - 2 * margin
        knob_x = self.width() - knob_d - margin if self.isChecked() else margin
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob_x, margin, knob_d, knob_d)


class TrungLienVideoLabel(QLabel):
    """Khu vực hiển thị camera riêng của Trung liên, hỗ trợ chọn tâm."""

    clicked = Signal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._is_calibrating = False
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(240, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            background-color: {COLORS['video_background']};
            color: #D0D5DD;
            border: 1px solid #344054;
            border-radius: 13px;
            font-size: 13px;
            font-weight: 600;
        """)

    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        self.setToolTip("Click để chọn tâm ngắm mới" if active else "")

    def mousePressEvent(self, event):
        if self._is_calibrating and event.button() == Qt.LeftButton:
            self.clicked.emit(event.pos())
        super().mousePressEvent(event)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        scaled_pixmap = self._pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)


class TrungLienGui(QWidget):
    """Giao diện thiết lập và luyện tập Trung liên."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

    def setupUi(self):
        screen = QApplication.primaryScreen()
        screen_height = screen.availableGeometry().height() if screen else 1080
        self.scale_factor = max(0.82, min(1.18, screen_height / 1080))

        def s(value):
            return scaled(value, self.scale_factor)

        def f(value):
            return max(9, scaled(value, self.scale_factor))

        self.setObjectName("TrungLienScreen")

        self.setStyleSheet(f"""
            QWidget#TrungLienScreen {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                font-family: 'Segoe UI', 'Aptos', 'Arial';
            }}
            QFrame#panel {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(14)}px;
            }}
            QLabel#screenTitle {{
                color: {COLORS['text']};
                font-size: {f(18)}px;
                font-weight: 800;
                background: transparent;
            }}
            QLabel#panelTitle {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border-radius: {s(8)}px;
                padding: {s(5)}px {s(12)}px;
                font-size: {f(11)}px;
                font-weight: 800;
            }}
            QLabel#fieldLabel {{
                color: {COLORS['text_secondary']};
                background: transparent;
                font-size: {f(10)}px;
                font-weight: 700;
            }}
            QLabel#valueLabel {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border: 1px solid #D9E5FF;
                border-radius: {s(7)}px;
                padding: {s(3)}px {s(6)}px;
                font-size: {f(11)}px;
                font-weight: 800;
            }}
            QLabel#resultLabel {{
                color: {COLORS['text']};
                background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(8)}px;
                padding: {s(6)}px {s(8)}px;
                font-size: {f(10)}px;
                font-weight: 600;
            }}
            QGroupBox {{
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(10)}px;
                margin-top: {s(10)}px;
                padding: {s(10)}px {s(8)}px {s(8)}px;
                font-size: {f(10)}px;
                font-weight: 800;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {s(10)}px;
                padding: {s(1)}px {s(6)}px;
                color: {COLORS['primary']};
                background-color: {COLORS['surface']};
            }}
            QPushButton {{
                min-height: {s(30)}px;
                padding: {s(4)}px {s(12)}px;
                color: white;
                background-color: {COLORS['primary']};
                border: none;
                border-radius: {s(8)}px;
                font-size: {f(10)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
            QPushButton#refreshButton {{
                color: {COLORS['text']};
                background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border_strong']};
            }}
            QPushButton#backButton {{
                color: {COLORS['danger']};
                background-color: {COLORS['danger_soft']};
                border: 1px solid #F3D2D2;
            }}
            QPushButton#backButton:hover {{
                color: white;
                background-color: {COLORS['danger']};
            }}
            QComboBox {{
                min-height: {s(28)}px;
                padding: {s(2)}px {s(8)}px;
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {s(8)}px;
                font-size: {f(10)}px;
            }}
            QSlider::groove:horizontal {{
                height: {s(5)}px;
                background: #E7ECF4;
                border-radius: {s(2)}px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['primary']};
                border-radius: {s(2)}px;
            }}
            QSlider::handle:horizontal {{
                width: {s(13)}px;
                height: {s(13)}px;
                margin: -{s(5)}px 0;
                background: white;
                border: 2px solid {COLORS['primary']};
                border-radius: {s(8)}px;
            }}
        """)

        # ROOT LAYOUT
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(s(14), s(10), s(14), s(12))
        root_layout.setSpacing(s(8))

        # SCREEN TITLE
        title = QLabel("MÀN HÌNH LUYỆN TẬP TRUNG LIÊN")
        title.setObjectName("screenTitle")
        title.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(title)

        # MAIN COLUMNS (tỷ lệ 6.5 : 3.5)
        columns = QHBoxLayout()
        columns.setSpacing(s(12))
        columns.addWidget(self._create_camera_panel(), 13)
        columns.addWidget(self._create_right_panel(), 7)
        root_layout.addLayout(columns, 1)

    def _create_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        add_soft_shadow(panel, blur=20, y_offset=4, alpha=15)
        return panel

    def _create_camera_panel(self):
        panel = self._create_panel()
        margin = scaled(10, self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(scaled(8, self.scale_factor))

        title = QLabel("HÌNH ẢNH CAMERA")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, 0, Qt.AlignHCenter)

        self.camera_view_label = TrungLienVideoLabel()
        self.camera_view_label.setText("Camera Trung liên chưa được kết nối")
        layout.addWidget(self.camera_view_label, 1)

        controls = QHBoxLayout()
        controls.setSpacing(scaled(7, self.scale_factor))

        self.camera_selector = QComboBox()
        self.camera_selector.setMinimumWidth(scaled(115, self.scale_factor))
        self.camera_selector.setPlaceholderText("Chọn Camera...")
        controls.addWidget(self.camera_selector)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        controls.addWidget(self.refresh_button)

        controls.addStretch(1)

        zoom_text_label = QLabel("Thu phóng")
        zoom_text_label.setObjectName("fieldLabel")

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 50)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setMaximumWidth(scaled(110, self.scale_factor))
        controls.addWidget(zoom_text_label)
        controls.addWidget(self.zoom_slider)

        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("valueLabel")
        self.zoom_value_label.setAlignment(Qt.AlignCenter)
        self.zoom_value_label.setMinimumWidth(scaled(42, self.scale_factor))
        controls.addWidget(self.zoom_value_label)

        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        self.calibrate_button.setCursor(Qt.PointingHandCursor)
        controls.addWidget(self.calibrate_button)

        layout.addLayout(controls)
        self.zoom_slider.valueChanged.connect(
            lambda value: self.zoom_value_label.setText(f"{value / 10:.1f}x")
        )
        return panel

    def _create_right_panel(self):
        panel = self._create_panel()
        margin = scaled(10, self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(scaled(8, self.scale_factor))

        # TRAINING SETTINGS (một dòng: công tắc Liên thanh + thanh tốc độ)
        settings_box = QGroupBox("THIẾT LẬP LUYỆN TẬP")
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.setContentsMargins(
            scaled(6, self.scale_factor),
            scaled(4, self.scale_factor),
            scaled(6, self.scale_factor),
            scaled(2, self.scale_factor),
        )

        self.settings_row = QHBoxLayout()
        self.settings_row.setSpacing(scaled(8, self.scale_factor))

        burst_label = QLabel("Liên thanh")
        burst_label.setObjectName("fieldLabel")
        self.settings_row.addWidget(burst_label)

        self.burst_switch = ToggleSwitch(
            width=scaled(42, self.scale_factor),
            height=scaled(22, self.scale_factor),
        )
        self.settings_row.addWidget(self.burst_switch)

        # Cụm tốc độ bắn: chỉ hiện khi bật Liên thanh
        self.rate_container = QWidget()
        rate_layout = QHBoxLayout(self.rate_container)
        rate_layout.setContentsMargins(scaled(6, self.scale_factor), 0, 0, 0)
        rate_layout.setSpacing(scaled(8, self.scale_factor))

        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(500, 900)
        self.rate_slider.setValue(700)
        self.rate_slider.setSingleStep(10)
        self.rate_slider.setPageStep(50)
        self.rate_slider.setToolTip("Tốc độ bắn mô phỏng (500 - 900)")
        rate_layout.addWidget(self.rate_slider, 1)

        self.rate_value_label = QLabel("700")
        self.rate_value_label.setObjectName("valueLabel")
        self.rate_value_label.setMinimumWidth(scaled(46, self.scale_factor))
        self.rate_value_label.setAlignment(Qt.AlignCenter)
        rate_layout.addWidget(self.rate_value_label)

        self.settings_row.addWidget(self.rate_container, 1)
        self.settings_row.addStretch(0)  # index 3: giữ chỗ khi thanh tốc độ ẩn
        settings_layout.addLayout(self.settings_row)

        self.burst_switch.toggled.connect(self._on_burst_toggled)
        self.rate_slider.valueChanged.connect(self._on_rate_changed)
        self._on_burst_toggled(False)

        layout.addWidget(settings_box)

        # RESULT PANEL
        result_box = QGroupBox("KẾT QUẢ GHI NHẬN")
        result_layout = QVBoxLayout(result_box)
        result_layout.setContentsMargins(
            scaled(6, self.scale_factor),
            scaled(6, self.scale_factor),
            scaled(6, self.scale_factor),
            scaled(6, self.scale_factor),
        )
        result_layout.setSpacing(scaled(6, self.scale_factor))

        info_row = QHBoxLayout()
        info_row.setSpacing(scaled(6, self.scale_factor))

        self.target_name_label = QLabel("Tên mục tiêu: --")
        self.target_name_label.setObjectName("resultLabel")
        self.target_name_label.setWordWrap(True)
        info_row.addWidget(self.target_name_label, 1)

        self.score_label = QLabel("Kết quả: --")
        self.score_label.setObjectName("resultLabel")
        self.score_label.setWordWrap(True)
        info_row.addWidget(self.score_label, 1)

        result_layout.addLayout(info_row)

        image_title = QLabel("HÌNH ẢNH KẾT QUẢ")
        image_title.setObjectName("fieldLabel")
        result_layout.addWidget(image_title)

        self.result_image_label = QLabel("Chưa có ảnh kết quả")
        self.result_image_label.setAlignment(Qt.AlignCenter)
        self.result_image_label.setMinimumHeight(scaled(180, self.scale_factor))
        self.result_image_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.result_image_label.setStyleSheet(f"""
            background-color: {COLORS['surface_soft']};
            color: {COLORS['text_muted']};
            border: 1px dashed {COLORS['border_strong']};
            border-radius: {scaled(10, self.scale_factor)}px;
        """)
        result_layout.addWidget(self.result_image_label, 1)

        layout.addWidget(result_box, 1)

        self.back_button = QPushButton("VỀ MENU CHÍNH")
        self.back_button.setObjectName("backButton")
        self.back_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.back_button)

        return panel

    # ==============================================
    # CAMERA DISPLAY (giống màn hình B41)
    # ==============================================

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

    # ==============================================
    # TRAINING SETTINGS
    # ==============================================

    def is_burst_enabled(self) -> bool:
        """Trả về True nếu công tắc Liên thanh đang bật."""
        return self.burst_switch.isChecked()

    def _on_burst_toggled(self, checked):
        """Bật Liên thanh mới hiển thị thanh kéo tốc độ bắn."""
        self.rate_container.setVisible(checked)
        # Khi ẩn: spacer cuối hàng nhận phần dư; khi hiện: thanh tốc độ giãn ra
        self.settings_row.setStretch(2, 1 if checked else 0)
        self.settings_row.setStretch(3, 0 if checked else 1)
        if checked:
            self.rate_value_label.setText(str(self.rate_slider.value()))

    def _on_rate_changed(self, value):
        """Cập nhật con số hiển thị trên giao diện."""
        self.rate_value_label.setText(str(value))
