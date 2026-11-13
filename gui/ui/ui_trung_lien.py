"""B41 - Trung Lien Practice UI.
Giao diện độc lập, chưa kết nối phần cứng điều khiển.
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
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


class TrungLienVideoLabel(QLabel):
    """Khu vực hiển thị camera riêng của Trung liên."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
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

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return

        from PySide6.QtGui import QPainter

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
                border-radius: {s(17)}px;
            }}
            QLabel#screenTitle {{
                color: {COLORS['text']};
                font-size: {f(22)}px;
                font-weight: 800;
                background: transparent;
            }}
            QLabel#panelTitle {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border-radius: {s(9)}px;
                padding: {s(9)}px {s(14)}px;
                font-size: {f(13)}px;
                font-weight: 800;
            }}
            QLabel#fieldLabel {{
                color: {COLORS['text_secondary']};
                background: transparent;
                font-size: {f(11)}px;
                font-weight: 700;
            }}
            QLabel#valueLabel {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border: 1px solid #D9E5FF;
                border-radius: {s(9)}px;
                padding: {s(8)}px;
                font-size: {f(14)}px;
                font-weight: 800;
            }}
            QLabel#resultLabel {{
                color: {COLORS['text']};
                background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(9)}px;
                padding: {s(12)}px;
                font-size: {f(12)}px;
                font-weight: 600;
            }}
            QGroupBox {{
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(12)}px;
                margin-top: {s(13)}px;
                padding: {s(17)}px {s(12)}px {s(12)}px;
                font-size: {f(12)}px;
                font-weight: 800;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {s(12)}px;
                padding: {s(3)}px {s(8)}px;
                color: {COLORS['primary']};
                background-color: {COLORS['surface']};
            }}
            QPushButton {{
                min-height: {s(40)}px;
                padding: {s(8)}px {s(15)}px;
                color: white;
                background-color: {COLORS['primary']};
                border: none;
                border-radius: {s(10)}px;
                font-size: {f(11)}px;
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
                min-height: {s(36)}px;
                padding: {s(4)}px {s(10)}px;
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {s(9)}px;
            }}
            QSlider::groove:horizontal {{
                height: {s(6)}px;
                background: #E7ECF4;
                border-radius: {s(3)}px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['primary']};
                border-radius: {s(3)}px;
            }}
            QSlider::handle:horizontal {{
                width: {s(17)}px;
                height: {s(17)}px;
                margin: -{s(6)}px 0;
                background: white;
                border: 3px solid {COLORS['primary']};
                border-radius: {s(10)}px;
            }}
        """)

        # ROOT LAYOUT
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(s(22), s(18), s(22), s(20))
        root_layout.setSpacing(s(15))

        # SCREEN TITLE
        title = QLabel("MÀN HÌNH LUYỆN TẬP TRUNG LIÊN")
        title.setObjectName("screenTitle")
        title.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(title)

        # MAIN COLUMNS
        columns = QHBoxLayout()
        columns.setSpacing(s(17))
        columns.addWidget(self._create_camera_panel(), 6)
        columns.addWidget(self._create_right_panel(), 4)
        root_layout.addLayout(columns, 1)

    def _create_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        add_soft_shadow(panel, blur=25, y_offset=6, alpha=17)
        return panel

    def _create_camera_panel(self):
        panel = self._create_panel()
        margin = scaled(17, self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(margin)

        title = QLabel("HÌNH ẢNH CAMERA")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, 0, Qt.AlignHCenter)

        self.camera_view_label = TrungLienVideoLabel()
        self.camera_view_label.setText("Camera Trung liên chưa được kết nối")
        layout.addWidget(self.camera_view_label, 1)

        controls = QHBoxLayout()
        controls.setSpacing(scaled(9, self.scale_factor))

        self.camera_selector = QComboBox()
        self.camera_selector.setMinimumWidth(scaled(135, self.scale_factor))
        self.camera_selector.setPlaceholderText("Chọn Camera...")
        controls.addWidget(self.camera_selector)

        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.setObjectName("refreshButton")
        controls.addWidget(self.refresh_button)

        controls.addStretch(1)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 50)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setMaximumWidth(scaled(120, self.scale_factor))
        controls.addWidget(QLabel("Thu phóng"))
        controls.addWidget(self.zoom_slider)

        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("valueLabel")
        controls.addWidget(self.zoom_value_label)

        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        controls.addWidget(self.calibrate_button)

        layout.addLayout(controls)
        self.zoom_slider.valueChanged.connect(
            lambda value: self.zoom_value_label.setText(f"{value / 10:.1f}x")
        )
        return panel

    def _create_right_panel(self):
        panel = self._create_panel()
        margin = scaled(17, self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(scaled(12, self.scale_factor))

        # TRAINING SETTINGS
        settings_box = QGroupBox("THIẾT LẬP LUYỆN TẬP")
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.setSpacing(scaled(13, self.scale_factor))

        mode_label = QLabel("Chế độ mô phỏng")
        mode_label.setObjectName("fieldLabel")
        settings_layout.addWidget(mode_label)

        self.fire_mode_combo = QComboBox()
        self.fire_mode_combo.addItems(
            [
                "Phát một lần",
                "Mô phỏng liên tục",
            ]
        )
        settings_layout.addWidget(self.fire_mode_combo)

        rate_header = QHBoxLayout()
        rate_label = QLabel("Thông số mô phỏng")
        rate_label.setObjectName("fieldLabel")
        rate_header.addWidget(rate_label)
        rate_header.addStretch(1)

        self.rate_value_label = QLabel("700")
        self.rate_value_label.setObjectName("valueLabel")
        self.rate_value_label.setMinimumWidth(scaled(75, self.scale_factor))
        self.rate_value_label.setAlignment(Qt.AlignCenter)
        rate_header.addWidget(self.rate_value_label)
        settings_layout.addLayout(rate_header)

        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(500, 900)
        self.rate_slider.setValue(700)
        self.rate_slider.setSingleStep(10)
        self.rate_slider.setPageStep(50)
        self.rate_slider.setEnabled(False)
        settings_layout.addWidget(self.rate_slider)

        rate_scale = QHBoxLayout()
        rate_scale.addWidget(QLabel("500"))
        rate_scale.addStretch(1)
        rate_scale.addWidget(QLabel("900"))
        settings_layout.addLayout(rate_scale)

        self.rate_note_label = QLabel(
            "Thông số chỉ dùng cho giao diện mô phỏng; " "chưa kết nối phần cứng."
        )
        self.rate_note_label.setWordWrap(True)
        self.rate_note_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; "
            "font-size: 10px; background: transparent;"
        )
        settings_layout.addWidget(self.rate_note_label)

        self.fire_mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.rate_slider.valueChanged.connect(self._on_rate_changed)

        layout.addWidget(settings_box)

        # RESULT PANEL
        result_box = QGroupBox("KẾT QUẢ GHI NHẬN")
        result_layout = QVBoxLayout(result_box)
        result_layout.setSpacing(scaled(10, self.scale_factor))

        self.target_name_label = QLabel("Tên mục tiêu: --")
        self.target_name_label.setObjectName("resultLabel")
        result_layout.addWidget(self.target_name_label)

        self.score_label = QLabel("Kết quả: --")
        self.score_label.setObjectName("resultLabel")
        result_layout.addWidget(self.score_label)

        image_title = QLabel("HÌNH ẢNH KẾT QUẢ")
        image_title.setObjectName("fieldLabel")
        result_layout.addWidget(image_title)

        self.result_image_label = QLabel("Chưa có ảnh kết quả")
        self.result_image_label.setAlignment(Qt.AlignCenter)
        self.result_image_label.setMinimumHeight(scaled(145, self.scale_factor))
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

    def _on_mode_changed(self, index):
        """Hiển thị hoặc ẩn điều khiển thông số mô phỏng."""
        is_continuous_simulation = index == 1
        self.rate_slider.setEnabled(is_continuous_simulation)

        if not is_continuous_simulation:
            self.rate_value_label.setText("--")

        else:
            self.rate_value_label.setText(str(self.rate_slider.value()))

    def _on_rate_changed(self, value):
        """Cập nhật con số hiển thị trên giao diện."""
        self.rate_value_label.setText(str(value))
