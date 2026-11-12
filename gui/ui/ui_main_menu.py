"""Giao diện màn hình chính B41 – Light UI."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .theme import COLORS, add_soft_shadow, scaled


class Ui_MainMenuWindow(object):

    def setupUi(self, MainMenuWindow):

        MainMenuWindow.setObjectName("MainMenuWindow")
        MainMenuWindow.setMinimumSize(760, 560)

        screen = QApplication.primaryScreen()

        screen_height = screen.availableGeometry().height() if screen else 1080

        self.scale_factor = max(0.82, min(1.18, screen_height / 1080.0))

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
                background-image: none;
            }}

            QFrame#headerCard,
            QFrame#actionCard {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(22)}px;
            }}

            QLabel#unitLabel {{
                color: {COLORS['primary']};
                font-size: {f(16)}px;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
            }}

            QLabel#appTitle {{
                color: {COLORS['text']};
                font-size: {f(31)}px;
                font-weight: 800;
                background: transparent;
            }}

            QLabel#footerLabel {{
                color: {COLORS['text_secondary']};
                font-size: {f(12)}px;
                background: transparent;
            }}

            QLabel#logoLabel {{
                background: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(16)}px;
            }}

            QPushButton {{
                min-height: {s(58)}px;
                padding: {s(12)}px {s(28)}px;
                color: #FFFFFF;
                background-color: {COLORS['primary']};
                border: 0;
                border-radius: {s(14)}px;
                font-size: {f(16)}px;
                font-weight: 700;
            }}

            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}

            QPushButton:pressed {{
                background-color: {COLORS['primary_pressed']};
                padding-top: {s(14)}px;
            }}

            QPushButton:focus {{
                border: 2px solid #93B4FF;
            }}

            QPushButton#exitButton {{
                color: {COLORS['danger']};
                background-color: {COLORS['danger_soft']};
                border: 1px solid #F5D1D1;
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

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_layout = QVBoxLayout(self.centralwidget)

        self.main_layout.setContentsMargins(s(42), s(30), s(42), s(24))

        self.main_layout.setSpacing(s(22))

        self.main_layout.addStretch(1)

        # ==========================================
        # HEADER CARD
        # ==========================================

        self.header_card = QFrame(self.centralwidget)
        self.header_card.setObjectName("headerCard")

        add_soft_shadow(self.header_card, blur=s(30), y_offset=s(8), alpha=16)

        header_layout = QHBoxLayout(self.header_card)

        header_layout.setContentsMargins(s(28), s(28), s(28), s(28))

        header_layout.setSpacing(s(24))

        logo_size = s(116)

        self.logo_left = QLabel(self.header_card)
        self.logo_left.setObjectName("logoLabel")
        self.logo_left.setFixedSize(logo_size, logo_size)
        self.logo_left.setScaledContents(False)
        self.logo_left.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(self.logo_left, 0, Qt.AlignVCenter)

        # ==========================================
        # TITLE
        # ==========================================

        title_container = QWidget(self.header_card)
        title_container.setStyleSheet("background: transparent;")

        title_layout = QVBoxLayout(title_container)

        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(s(12))

        self.customer_title_label = QLabel(title_container)
        self.customer_title_label.setObjectName("unitLabel")
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        self.customer_title_label.setWordWrap(True)

        title_layout.addWidget(self.customer_title_label)

        self.title_label = QLabel(title_container)
        self.title_label.setObjectName("appTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)

        self.title_label.setFont(QFont("Segoe UI", f(31), QFont.Bold))

        title_layout.addWidget(self.title_label)

        header_layout.addWidget(title_container, 1)

        # ==========================================
        # RIGHT LOGO
        # ==========================================

        self.logo_right = QLabel(self.header_card)
        self.logo_right.setObjectName("logoLabel")
        self.logo_right.setFixedSize(logo_size, logo_size)
        self.logo_right.setScaledContents(False)
        self.logo_right.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(self.logo_right, 0, Qt.AlignVCenter)

        self.main_layout.addWidget(self.header_card)

        self.main_layout.addStretch(1)

        # ==========================================
        # ACTION CARD
        # ==========================================

        self.action_card = QFrame(self.centralwidget)
        self.action_card.setObjectName("actionCard")

        add_soft_shadow(self.action_card, blur=s(26), y_offset=s(7), alpha=13)

        buttons_layout = QVBoxLayout(self.action_card)

        buttons_layout.setContentsMargins(s(48), s(38), s(48), s(38))

        buttons_layout.setSpacing(s(18))
        buttons_layout.setAlignment(Qt.AlignCenter)

        self.practice_button = QPushButton("BẮT ĐẦU LUYỆN TẬP", self.action_card)

        self.practice_button.setObjectName("practiceButton")

        self.practice_button.setMinimumSize(QSize(s(330), s(62)))

        self.practice_button.setCursor(Qt.PointingHandCursor)

        buttons_layout.addWidget(self.practice_button)

        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", self.action_card)

        self.exit_button.setObjectName("exitButton")

        self.exit_button.setMinimumSize(QSize(s(330), s(54)))

        self.exit_button.setCursor(Qt.PointingHandCursor)

        buttons_layout.addWidget(self.exit_button)

        self.main_layout.addWidget(self.action_card, 0, Qt.AlignHCenter)

        self.main_layout.addStretch(1)

        # ==========================================
        # FOOTER
        # ==========================================

        self.footer_label = QLabel(self.centralwidget)
        self.footer_label.setObjectName("footerLabel")
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setWordWrap(True)

        self.main_layout.addWidget(self.footer_label)

        MainMenuWindow.setCentralWidget(self.centralwidget)
