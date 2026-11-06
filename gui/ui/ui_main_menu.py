# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
)

class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        scale_factor = screen_height / 1080.0

        def scale_size(base_size): return max(1, int(base_size * scale_factor))
        def scale_font(base_size): return max(8, int(base_size * scale_factor))

        MainMenuWindow.setStyleSheet(f"""
            #MainMenuWindow {{
                background-color: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, 
                                                  stop:0 #f8fafc, 
                                                  stop:1 #e2e8f0);
            }}
            QPushButton {{
                background-color: #0ea5e9;
                color: white;
                border: none;
                border-radius: {scale_size(10)}px;
                padding: {scale_size(15)}px;
                font-size: {scale_font(20)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #0284c7; }}
            QPushButton:pressed {{ background-color: #0369a1; }}
            QPushButton#exitButton {{ background-color: #ef4444; }}
            QPushButton#exitButton:hover {{ background-color: #dc2626; }}
            QPushButton#exitButton:pressed {{ background-color: #b91c1c; }}
        """)

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(scale_size(40), scale_size(10), scale_size(40), scale_size(10))
        self.main_layout.setSpacing(scale_size(15))

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(scale_size(30), scale_size(20), scale_size(30), 0)
        header_layout.setSpacing(scale_size(20))

        logo_size_val = scale_size(120)
        
        self.logo_left = QLabel(header_widget)
        self.logo_left.setFixedSize(logo_size_val, logo_size_val)
        self.logo_left.setScaledContents(False)
        self.logo_left.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.logo_left)

        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(scale_size(5))

        self.customer_title_label = QLabel(title_container)
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        self.customer_title_label.setStyleSheet(f"color: #0284c7; font-size: {scale_font(22)}px; font-weight: bold; margin-bottom: {scale_size(5)}px;")
        title_layout.addWidget(self.customer_title_label)
        
        self.title_label = QLabel(title_container)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"color: #1e293b; font-size: {scale_font(34)}px; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        header_layout.addWidget(title_container, 1)

        self.logo_right = QLabel(header_widget)
        self.logo_right.setFixedSize(logo_size_val, logo_size_val)
        self.logo_right.setScaledContents(False)
        self.logo_right.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.logo_right)

        self.main_layout.addWidget(header_widget)
        self.main_layout.addStretch(1)

        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(scale_size(20))
        buttons_layout.setAlignment(Qt.AlignCenter)

        btn_size = QSize(scale_size(300), scale_size(70))

        self.practice_button = QPushButton("LUYỆN TẬP", buttons_container)
        self.practice_button.setMinimumSize(btn_size)
        buttons_layout.addWidget(self.practice_button)

        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", buttons_container)
        self.exit_button.setMinimumSize(btn_size)
        self.exit_button.setObjectName("exitButton")
        buttons_layout.addWidget(self.exit_button)

        self.main_layout.addWidget(buttons_container)
        self.main_layout.addStretch(2)

        self.footer_label = QLabel(self.centralwidget)
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet(f"color: #64748b; font-size: {scale_font(16)}px; font-style: italic; padding-bottom: {scale_size(10)}px;")
        self.main_layout.addWidget(self.footer_label)
        
        MainMenuWindow.setCentralWidget(self.centralwidget)