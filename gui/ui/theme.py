"""Bộ nhận diện giao diện sáng cho ứng dụng B41.

Chỉ sử dụng Qt Style Sheet và font có sẵn trên hệ điều hành.
Không tải font, stylesheet, icon hoặc tài nguyên từ Internet;
ứng dụng có thể hoạt động hoàn toàn offline.
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

COLORS = {
    "background": "#F4F7FB",
    "surface": "#FFFFFF",
    "surface_soft": "#F8FAFD",
    "surface_hover": "#EEF4FA",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "primary_pressed": "#1E40AF",
    "primary_soft": "#EAF1FF",
    "text": "#172033",
    "text_secondary": "#667085",
    "text_muted": "#98A2B3",
    "border": "#E3E9F2",
    "border_strong": "#CBD5E1",
    "success": "#159B72",
    "success_soft": "#E8F7F1",
    "danger": "#DC4C4C",
    "danger_hover": "#C83B3B",
    "danger_soft": "#FFF0F0",
    "warning": "#B7791F",
    "warning_soft": "#FFF7E6",
    "video_background": "#101828",
}


def scaled(base_value: int, scale_factor: float, minimum: int = 1) -> int:
    """Tính kích thước theo màn hình."""
    return max(minimum, int(round(base_value * scale_factor)))


def add_soft_shadow(widget, blur: int = 28, y_offset: int = 7, alpha: int = 18):
    """Thêm bóng đổ nhẹ cho panel."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(15, 23, 42, alpha))
    effect.setOffset(0, y_offset)
    widget.setGraphicsEffect(effect)
    return effect


def application_stylesheet() -> str:
    """QSS dùng chung cho hộp thoại và widget chưa có stylesheet riêng."""

    c = COLORS

    return f"""
        QWidget {{
            color: {c['text']};
            font-family: 'Segoe UI', 'Aptos', 'Arial', sans-serif;
            font-size: 10pt;
        }}

        QDialog, QMessageBox, QInputDialog {{
            background-color: {c['surface']};
        }}

        QMessageBox QLabel, QInputDialog QLabel {{
            color: {c['text']};
            background: transparent;
            min-width: 280px;
        }}

        QMessageBox QPushButton,
        QDialogButtonBox QPushButton {{
            min-width: 88px;
            min-height: 34px;
            padding: 6px 16px;
            color: {c['text']};
            background: {c['surface_soft']};
            border: 1px solid {c['border']};
            border-radius: 9px;
            font-weight: 600;
        }}

        QMessageBox QPushButton:hover,
        QDialogButtonBox QPushButton:hover {{
            background: {c['surface_hover']};
            border-color: {c['border_strong']};
        }}

        QLineEdit, QSpinBox, QDoubleSpinBox {{
            min-height: 34px;
            padding: 5px 10px;
            color: {c['text']};
            background: {c['surface']};
            border: 1px solid {c['border_strong']};
            border-radius: 9px;
            selection-background-color: {c['primary']};
            selection-color: white;
        }}

        QLineEdit:focus,
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: 1px solid {c['primary']};
        }}

        QToolTip {{
            color: white;
            background: #263449;
            border: 0;
            border-radius: 6px;
            padding: 6px 9px;
        }}

        QScrollBar:vertical {{
            width: 9px;
            background: transparent;
            margin: 2px;
        }}

        QScrollBar::handle:vertical {{
            min-height: 28px;
            background: #C7D2E1;
            border-radius: 4px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: #94A3B8;
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
            background: transparent;
        }}

        QScrollBar:horizontal {{
            height: 9px;
            background: transparent;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal {{
            min-width: 28px;
            background: #C7D2E1;
            border-radius: 4px;
        }}

        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
            background: transparent;
        }}
    """
