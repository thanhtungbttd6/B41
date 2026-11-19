"""B41 - Main Menu UI | Minimal Modern Light Design."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QGraphicsOpacityEffect,
)

from .theme import COLORS, scaled


class WatermarkLabel(QLabel):
    """Hiển thị ảnh nền in chìm, tự điều chỉnh khi thay đổi kích thước."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = QPixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: transparent; border: none;")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.45)
        self.setGraphicsEffect(self.opacity_effect)

    def set_watermark(self, pixmap: QPixmap):
        """Nạp ảnh gốc và cập nhật hiển thị."""
        self.original_pixmap = pixmap
        self.update_watermark()

    def set_opacity(self, opacity: float):
        """Thay đổi độ mờ của ảnh nền."""
        self.opacity_effect.setOpacity(max(0.0, min(1.0, opacity)))

    def update_watermark(self):
        """Tự tính kích thước ảnh nền theo cửa sổ."""
        if self.original_pixmap.isNull():
            self.clear()
            return

        target_width = min(560, int(self.width() * 0.45))
        target_height = min(560, int(self.height() * 0.72))

        if target_width <= 0 or target_height <= 0:
            return

        scaled_pixmap = self.original_pixmap.scaled(
            QSize(target_width, target_height),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        super().setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_watermark()


class Ui_MainMenuWindow(object):

    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        MainMenuWindow.setMinimumSize(1100, 700)

        screen = QApplication.primaryScreen()
        screen_height = screen.availableGeometry().height() if screen else 1080
        self.scale_factor = max(0.85, min(1.15, screen_height / 1080.0))

        def s(value):
            return scaled(value, self.scale_factor)

        def f(value):
            return max(9, scaled(value, self.scale_factor))

        MainMenuWindow.setStyleSheet(f"""
            QMainWindow#MainMenuWindow {{
                background-color: {COLORS['background']};
            }}
            QWidget#centralwidget {{
                background-color: {COLORS['background']};
            }}
            QWidget#contentWidget,
            QWidget#headerWidget,
            QWidget#titleContainer,
            QWidget#buttonContainer {{
                background: transparent;
                border: none;
            }}
            QLabel#logoLabel {{
                background: transparent;
                border: none;
                padding: 0;
            }}
            QLabel#unitLabel {{
                color: {COLORS['primary']};
                font-size: {f(17)}px;
                font-weight: 800;
                letter-spacing: 1.2px;
                background: transparent;
            }}
            QLabel#appTitle {{
                color: {COLORS['text']};
                font-size: {f(30)}px;
                font-weight: 800;
                background: transparent;
            }}
            QLabel#footerLabel {{
                color: {COLORS['text_secondary']};
                font-size: {f(15)}px;
                font-weight: 600;
                background: transparent;
                padding: {s(5)}px;
            }}
            QPushButton {{
                min-height: {s(58)}px;
                padding: {s(10)}px {s(25)}px;
                color: #FFFFFF;
                background-color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: {s(12)}px;
                font-size: {f(15)}px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
                border-color: {COLORS['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary_pressed']};
            }}
            QPushButton:focus {{
                border: 2px solid #93B4FF;
            }}
            QPushButton#trungLienButton {{
                color: #FFFFFF;
                background-color: #0D9488;
                border-color: #0D9488;
            }}
            QPushButton#trungLienButton:hover {{
                background-color: #0F766E;
                border-color: #0F766E;
            }}
            QPushButton#trungLienButton:pressed {{
                background-color: #115E59;
            }}
            QPushButton#exitButton {{
                color: {COLORS['danger']};
                background-color: {COLORS['danger_soft']};
                border: 1px solid #F3D2D2;
            }}
            QPushButton#exitButton:hover {{
                color: #FFFFFF;
                background-color: {COLORS['danger']};
                border-color: {COLORS['danger']};
            }}
            QPushButton#exitButton:pressed {{
                background-color: {COLORS['danger_hover']};
            }}
        """)

        # CENTRAL WIDGET VÀ LỚP ẢNH NỀN
        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.stacked_layout = QStackedLayout(self.centralwidget)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_layout.setStackingMode(QStackedLayout.StackAll)

        # WATERMARK BACKGROUND
        self.watermark_label = WatermarkLabel(self.centralwidget)
        self.watermark_label.setObjectName("watermarkLabel")
        self.stacked_layout.addWidget(self.watermark_label)

        # CONTENT LAYER
        self.content_widget = QWidget(self.centralwidget)
        self.content_widget.setObjectName("contentWidget")
        self.content_widget.setAttribute(Qt.WA_TranslucentBackground, True)

        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(s(45), s(35), s(45), s(24))
        self.main_layout.setSpacing(s(15))

        # HEADER
        header_widget = QWidget(self.content_widget)
        header_widget.setObjectName("headerWidget")

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(s(5), s(15), s(5), s(10))
        header_layout.setSpacing(s(25))

        # LOGO SIZE: 250 X 250 PX
        logo_size = s(250)

        self.logo_left = QLabel(header_widget)
        self.logo_left.setObjectName("logoLabel")
        self.logo_left.setFixedSize(logo_size, logo_size)
        self.logo_left.setAlignment(Qt.AlignCenter)
        self.logo_left.setScaledContents(False)
        header_layout.addWidget(self.logo_left, 0, Qt.AlignVCenter)

        # CENTER TITLE
        title_container = QWidget(header_widget)
        title_container.setObjectName("titleContainer")

        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(s(8), 0, s(8), 0)
        title_layout.setSpacing(s(13))

        self.customer_title_label = QLabel(title_container)
        self.customer_title_label.setObjectName("unitLabel")
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        self.customer_title_label.setWordWrap(True)
        title_layout.addWidget(self.customer_title_label)

        self.title_label = QLabel(title_container)
        self.title_label.setObjectName("appTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setFont(QFont("Segoe UI", f(30), QFont.Bold))
        title_layout.addWidget(self.title_label)

        header_layout.addWidget(title_container, 1)

        # RIGHT LOGO
        self.logo_right = QLabel(header_widget)
        self.logo_right.setObjectName("logoLabel")
        self.logo_right.setFixedSize(logo_size, logo_size)
        self.logo_right.setAlignment(Qt.AlignCenter)
        self.logo_right.setScaledContents(False)
        header_layout.addWidget(self.logo_right, 0, Qt.AlignVCenter)

        self.main_layout.addWidget(header_widget)
        self.main_layout.addStretch(2)

        # BUTTON CONTAINER
        button_container = QWidget(self.content_widget)
        button_container.setObjectName("buttonContainer")

        buttons_layout = QVBoxLayout(button_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(s(16))
        buttons_layout.setAlignment(Qt.AlignCenter)

        button_size = QSize(s(370), s(62))

        # B41 PRACTICE BUTTON
        self.practice_button = QPushButton("LUYỆN TẬP B41", button_container)
        self.practice_button.setObjectName("practiceButton")
        self.practice_button.setMinimumSize(button_size)
        self.practice_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.practice_button)

        # TRUNG LIEN PRACTICE BUTTON
        self.trung_lien_button = QPushButton(
            "LUYỆN TẬP TRUNG LIÊN",
            button_container,
        )
        self.trung_lien_button.setObjectName("trungLienButton")
        self.trung_lien_button.setMinimumSize(button_size)
        self.trung_lien_button.setCursor(Qt.PointingHandCursor)
        self.trung_lien_button.setToolTip(
            "Chức năng luyện tập Trung liên sẽ được phát triển ở phiên bản tiếp theo."
        )
        buttons_layout.addWidget(self.trung_lien_button)

        # EXIT BUTTON
        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", button_container)
        self.exit_button.setObjectName("exitButton")
        self.exit_button.setMinimumSize(button_size)
        self.exit_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.exit_button)

        self.main_layout.addWidget(button_container, 0, Qt.AlignHCenter)
        self.main_layout.addStretch(2)

        # FOOTER
        self.footer_label = QLabel(self.content_widget)
        self.footer_label.setObjectName("footerLabel")
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setWordWrap(True)
        self.footer_label.setMinimumHeight(s(55))
        self.main_layout.addWidget(self.footer_label)

        self.stacked_layout.addWidget(self.content_widget)
        self.stacked_layout.setCurrentWidget(self.content_widget)

        MainMenuWindow.setCentralWidget(self.centralwidget)
