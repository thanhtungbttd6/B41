# file: gui/ui/ui_manage.py
"""B41 - Management & Statistics Screen UI (theme sáng)."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .theme import COLORS, add_soft_shadow, scaled


class ResultImageView(QLabel):
    """Khung hiển thị ảnh kết quả, tự co giãn giữ nguyên tỷ lệ ảnh."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setObjectName("resultView")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(160, 120)
        self.setText("Chưa có ảnh")

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        # Vẽ nền, viền và chữ gợi ý trước
        super().paintEvent(event)
        if self._pixmap.isNull():
            return

        scaled_pixmap = self._pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(x, y, scaled_pixmap)


class ManageGui(QWidget):
    """Giao diện màn hình Quản lý - Thống kê."""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setObjectName("ManageScreen")

        screen = QApplication.primaryScreen()
        screen_height = screen.availableGeometry().height() if screen else 1080
        self.scale_factor = max(0.82, min(1.18, screen_height / 1080.0))

        self._apply_style()
        self.setupUi()
        self._apply_labels()

    # ==============================================
    # STYLE
    # ==============================================

    def _apply_style(self):
        def s(value):
            return scaled(value, self.scale_factor)

        def f(value):
            return max(9, scaled(value, self.scale_factor))

        self.setStyleSheet(f"""
            QWidget#ManageScreen {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                font-family: 'Segoe UI', 'Aptos', 'Arial', sans-serif;
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
                padding: {s(2)}px;
                background: transparent;
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
                color: #FFFFFF;
                background-color: {COLORS['primary']};
                border: 0;
                border-radius: {s(8)}px;
                font-size: {f(10)}px;
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
            QPushButton#navButton {{
                min-width: {s(84)}px;
            }}
            QLineEdit#searchBox {{
                min-height: {s(28)}px;
                padding: {s(2)}px {s(8)}px;
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {s(8)}px;
                font-size: {f(10)}px;
            }}
            QLineEdit#searchBox:focus {{
                border: 1px solid {COLORS['primary']};
            }}
            QListWidget, QTableWidget {{
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                alternate-background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(8)}px;
                gridline-color: {COLORS['border']};
                font-size: {f(10)}px;
                outline: 0;
            }}
            QTableWidget::item, QListWidget::item {{
                padding: {s(4)}px;
            }}
            QListWidget::item {{
                padding: {s(8)}px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QListWidget::item:hover, QTableWidget::item:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QListWidget::item:selected, QTableWidget::item:selected {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
            }}
            QHeaderView::section {{
                color: {COLORS['text_secondary']};
                background-color: {COLORS['surface_soft']};
                padding: {s(4)}px;
                border: 0;
                border-bottom: 1px solid {COLORS['border']};
                border-right: 1px solid {COLORS['border']};
                font-size: {f(10)}px;
                font-weight: 700;
            }}
            QLabel#statValue {{
                color: {COLORS['primary']};
                background: transparent;
                font-size: {f(18)}px;
                font-weight: 800;
            }}
            QLabel#statCaption {{
                color: {COLORS['text_secondary']};
                background: transparent;
                font-size: {f(9)}px;
                font-weight: 700;
            }}
            QFrame#statChip {{
                background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border']};
                border-radius: {s(8)}px;
            }}
            QLabel#shotIndexLabel {{
                color: {COLORS['primary']};
                background-color: {COLORS['primary_soft']};
                border: 1px solid #D9E5FF;
                border-radius: {s(7)}px;
                padding: {s(3)}px {s(10)}px;
                font-size: {f(11)}px;
                font-weight: 800;
            }}
            QLabel#resultView {{
                color: #D0D5DD;
                background-color: {COLORS['video_background']};
                border: 1px solid #344054;
                border-radius: {s(13)}px;
                font-size: {f(13)}px;
                font-weight: 600;
            }}
            QLabel#messageLabel {{
                color: {COLORS['text_muted']};
                background: transparent;
                font-size: {f(14)}px;
                font-weight: 600;
            }}
        """)

    # ==============================================
    # LAYOUT
    # ==============================================

    def setupUi(self):
        s = lambda value: scaled(value, self.scale_factor)  # noqa: E731

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(s(14), s(10), s(14), s(12))
        root_layout.setSpacing(s(8))

        self.title_label = QLabel()
        self.title_label.setObjectName("screenTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(self.title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(s(12))
        columns_layout.addWidget(self._create_left_column(), 22)
        columns_layout.addWidget(self._create_center_column(), 53)
        columns_layout.addWidget(self._create_right_column(), 25)
        root_layout.addLayout(columns_layout, 1)

    def _apply_labels(self):
        labels = self.config.get("labels", {})
        self.title_label.setText("QUẢN LÝ - THỐNG KÊ")
        self.soldier_box.setTitle(
            labels.get("trainee_list_title", "Danh sách Người học").upper()
        )
        self.soldier_table.setHorizontalHeaderLabels(
            [
                labels.get("trainee_list_header_name", "Họ và Tên"),
                labels.get("trainee_list_header_class", "Đơn vị"),
            ]
        )
        self.history_box.setTitle(labels.get("history_title_prefix", "Lịch sử bắn"))
        trainee_term = labels.get("trainee", "chiến sĩ")
        self.search_box.setPlaceholderText(f"Tìm kiếm {trainee_term.lower()}...")

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        add_soft_shadow(
            panel,
            blur=scaled(22, self.scale_factor),
            y_offset=scaled(5, self.scale_factor),
            alpha=15,
        )
        return panel

    def _panel_layout(self, panel: QFrame) -> QVBoxLayout:
        margin = scaled(10, self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(scaled(8, self.scale_factor))
        return layout

    def _create_message_page(self):
        """Trang thông báo dùng khi chưa có dữ liệu để hiển thị."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel("...")
        label.setObjectName("messageLabel")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        return widget, label

    # --- Cột trái: danh sách người bắn ---
    def _create_left_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = self._panel_layout(panel)

        self.soldier_box = QGroupBox()
        soldier_layout = QVBoxLayout(self.soldier_box)
        soldier_layout.setSpacing(scaled(6, self.scale_factor))

        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setClearButtonEnabled(True)
        soldier_layout.addWidget(self.search_box)

        self.soldier_table = QTableWidget(0, 2)
        self.soldier_table.verticalHeader().setVisible(False)
        self.soldier_table.setAlternatingRowColors(True)
        self.soldier_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.soldier_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.soldier_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.soldier_table.setContextMenuPolicy(Qt.CustomContextMenu)
        header = self.soldier_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        soldier_layout.addWidget(self.soldier_table)
        layout.addWidget(self.soldier_box, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(scaled(6, self.scale_factor))
        self.add_button = QPushButton("Thêm mới")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.back_button = QPushButton("Về Menu Chính")
        self.back_button.setObjectName("danger")
        self.back_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.back_button)
        layout.addLayout(buttons_layout)
        return panel

    # --- Cột giữa: phân tích, chi tiết phát bắn, ảnh kết quả ---
    def _create_center_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = self._panel_layout(panel)

        self.center_stack = QStackedWidget()
        layout.addWidget(self.center_stack)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(scaled(8, self.scale_factor))

        # Hàng trên: phân tích (trái) + chi tiết từng phát (phải)
        top_row = QHBoxLayout()
        top_row.setSpacing(scaled(8, self.scale_factor))
        top_row.addWidget(self._create_analysis_box(), 1)
        top_row.addWidget(self._create_shot_list_box(), 1)
        data_layout.addLayout(top_row, 3)

        # Hàng dưới: ảnh kết quả chiếm phần lớn diện tích
        data_layout.addWidget(self._create_shot_preview_box(), 5)

        message_widget, self.center_message_label = self._create_message_page()

        self.center_stack.addWidget(data_widget)
        self.center_stack.addWidget(message_widget)
        return panel

    def _create_stat_chip(self, caption: str):
        chip = QFrame()
        chip.setObjectName("statChip")
        layout = QVBoxLayout(chip)
        layout.setContentsMargins(
            scaled(6, self.scale_factor),
            scaled(4, self.scale_factor),
            scaled(6, self.scale_factor),
            scaled(4, self.scale_factor),
        )
        layout.setSpacing(0)

        value = QLabel("--")
        value.setObjectName("statValue")
        value.setAlignment(Qt.AlignCenter)
        text = QLabel(caption)
        text.setObjectName("statCaption")
        text.setAlignment(Qt.AlignCenter)
        layout.addWidget(value)
        layout.addWidget(text)
        return chip, value

    def _create_analysis_box(self) -> QGroupBox:
        box = QGroupBox("PHÂN TÍCH PHIÊN BẮN")
        layout = QVBoxLayout(box)
        layout.setSpacing(scaled(6, self.scale_factor))

        chips_row = QHBoxLayout()
        chips_row.setSpacing(scaled(6, self.scale_factor))
        chip_total, self.stat_total = self._create_stat_chip("Tổng phát")
        chip_hits, self.stat_hits = self._create_stat_chip("Trúng")
        chip_misses, self.stat_misses = self._create_stat_chip("Trượt")
        chip_ungraded, self.stat_ungraded = self._create_stat_chip("Chưa chấm")
        chip_rate, self.stat_rate = self._create_stat_chip("Tỷ lệ trúng")
        for chip in (chip_total, chip_hits, chip_misses, chip_ungraded, chip_rate):
            chips_row.addWidget(chip, 1)
        layout.addLayout(chips_row)

        self.target_table = QTableWidget(0, 4)
        self.target_table.setHorizontalHeaderLabels(
            ["Loại bia", "Số phát", "Trúng", "Tỷ lệ"]
        )
        self.target_table.verticalHeader().setVisible(False)
        self.target_table.setAlternatingRowColors(True)
        self.target_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.target_table.setFocusPolicy(Qt.NoFocus)
        self.target_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.target_table.verticalHeader().setDefaultSectionSize(
            scaled(26, self.scale_factor)
        )
        header = self.target_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        layout.addWidget(self.target_table, 1)
        return box

    def _create_shot_list_box(self) -> QGroupBox:
        box = QGroupBox("CHI TIẾT TỪNG PHÁT BẮN")
        layout = QVBoxLayout(box)

        self.shot_table = QTableWidget(0, 4)
        self.shot_table.setHorizontalHeaderLabels(
            ["Phát", "Loạt", "Mục tiêu", "Kết quả"]
        )
        self.shot_table.verticalHeader().setVisible(False)
        self.shot_table.setAlternatingRowColors(True)
        self.shot_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shot_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shot_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.shot_table.verticalHeader().setDefaultSectionSize(
            scaled(26, self.scale_factor)
        )
        header = self.shot_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.shot_table)
        return box

    def _create_shot_preview_box(self) -> QGroupBox:
        box = QGroupBox("ẢNH KẾT QUẢ")
        layout = QVBoxLayout(box)
        layout.setSpacing(scaled(6, self.scale_factor))

        self.result_image = ResultImageView()
        layout.addWidget(self.result_image, 1)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(scaled(6, self.scale_factor))

        self.prev_shot_button = QPushButton("◀ Trước")
        self.prev_shot_button.setObjectName("navButton")
        self.prev_shot_button.setCursor(Qt.PointingHandCursor)

        self.shot_index_label = QLabel("Phát 0/0")
        self.shot_index_label.setObjectName("shotIndexLabel")
        self.shot_index_label.setAlignment(Qt.AlignCenter)

        self.next_shot_button = QPushButton("Sau ▶")
        self.next_shot_button.setObjectName("navButton")
        self.next_shot_button.setCursor(Qt.PointingHandCursor)

        nav_layout.addWidget(self.prev_shot_button)
        nav_layout.addWidget(self.shot_index_label, 1)
        nav_layout.addWidget(self.next_shot_button)
        layout.addLayout(nav_layout)
        return box

    # --- Cột phải: lịch sử các phiên ---
    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = self._panel_layout(panel)

        self.right_stack = QStackedWidget()
        layout.addWidget(self.right_stack)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(0, 0, 0, 0)

        self.history_box = QGroupBox()
        history_layout = QVBoxLayout(self.history_box)
        self.history_list = QListWidget()
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        history_layout.addWidget(self.history_list)
        data_layout.addWidget(self.history_box)

        message_widget, self.right_message_label = self._create_message_page()

        self.right_stack.addWidget(data_widget)
        self.right_stack.addWidget(message_widget)
        return panel
