"""Hộp thoại CÀI ĐẶT: thông tin hiển thị, hình ảnh và cập nhật model AI."""

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGraphicsOpacityEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from config import APP_DATA_DIR
from gui.ui.theme import COLORS
from utils.branding import (
    DEFAULT_BRANDING,
    clamp_opacity,
    find_branding_image,
    get_branding,
)

logger = logging.getLogger(__name__)

# (khóa, tên hiển thị, cạnh dài tối đa khi lưu)
IMAGE_SLOTS = (
    ("logo_left", "Logo trái", 1024),
    ("logo_right", "Logo phải", 1024),
    ("watermark_image", "Ảnh nền chìm", 2560),
)
IMAGE_FILTER = "Ảnh (*.png *.jpg *.jpeg *.bmp *.webp)"
CUSTOM_PREFIX = "custom_"

PREVIEW_W, PREVIEW_H = 150, 96


class SettingsDialog(QDialog):
    # Đường dẫn file model .pt mới người dùng vừa chọn
    model_update_requested = Signal(str)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self._branding = get_branding(config)
        self._original = dict(self._branding)  # để dọn ảnh tùy chỉnh cũ khi lưu
        self._pending = {}  # khóa ảnh -> đường dẫn ảnh mới chọn ("" = xóa ảnh)
        self._result = None
        self._model_busy = False

        self.setWindowTitle("Cài đặt")
        self.setModal(True)
        self._apply_style()
        self._build_ui()
        self._load_values()

    # ------------------------------------------------------------------
    # GIAO DIỆN
    # ------------------------------------------------------------------
    def _apply_style(self):
        c = COLORS
        self.setStyleSheet(f"""
            QDialog {{ background-color: {c['surface']}; }}
            QLabel {{ color: {c['text']}; font-size: 13px; background: transparent; }}
            QLabel#dialogTitle {{ font-size: 18px; font-weight: 800; }}
            QLabel#hint {{ color: {c['text_secondary']}; font-size: 12px; }}
            QLabel#preview {{
                color: {c['text_muted']}; font-size: 12px;
                background-color: {c['surface_soft']};
                border: 1px dashed {c['border_strong']}; border-radius: 8px;
            }}
            QGroupBox {{
                font-weight: 800; font-size: 12px; color: {c['primary']};
                border: 1px solid {c['border']}; border-radius: 10px;
                margin-top: 12px; padding: 14px 10px 10px 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 12px; padding: 0 6px;
            }}
            QLineEdit {{
                color: {c['text']}; background-color: {c['surface']};
                border: 1px solid {c['border_strong']}; border-radius: 8px;
                padding: 7px; font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {c['primary']}; }}
            QPushButton {{
                color: #FFFFFF; background-color: {c['primary']};
                border: 0; border-radius: 8px; padding: 7px 16px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {c['primary_hover']}; }}
            QPushButton:disabled {{ background-color: {c['border_strong']}; }}
            QPushButton#secondary {{
                color: {c['text']}; background-color: {c['surface_soft']};
                border: 1px solid {c['border_strong']};
            }}
            QPushButton#secondary:hover {{ background-color: {c['surface_hover']}; }}
            QPushButton#secondary:disabled {{ color: {c['text_muted']}; }}
            QPushButton#danger {{
                color: {c['danger']}; background-color: {c['danger_soft']};
                border: 1px solid {c['danger_soft']};
            }}
            QPushButton#danger:hover {{ background-color: #FFE1E1; }}
            QPushButton#danger:disabled {{ color: {c['text_muted']}; }}
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("CÀI ĐẶT")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        # ----- Cột trái: thông tin hiển thị + model AI -----
        left = QVBoxLayout()
        left.setSpacing(6)
        body.addLayout(left, 1)

        info_box = QGroupBox("THÔNG TIN HIỂN THỊ")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(4)
        self.text_edits = {}
        for key, caption in (
            ("title_1", "Tiêu đề 1"),
            ("title_2", "Tiêu đề 2"),
            ("footer_1", "Chân trang 1"),
            ("footer_2", "Chân trang 2"),
        ):
            info_layout.addWidget(QLabel(caption))
            edit = QLineEdit()
            edit.setPlaceholderText(
                "Gõ \\n để xuống dòng. Để trống nếu không dùng"
                if key == "title_2"
                else "Để trống nếu không dùng"
            )
            self.text_edits[key] = edit
            info_layout.addWidget(edit)
        left.addWidget(info_box)

        model_box = QGroupBox("MODEL AI")
        model_layout = QVBoxLayout(model_box)
        self.model_name_label = QLabel()
        model_layout.addWidget(self.model_name_label)
        self.model_button = QPushButton("Chọn file model AI mới (.pt)...")
        self.model_button.setCursor(Qt.PointingHandCursor)
        self.model_button.clicked.connect(self._choose_model)
        model_layout.addWidget(self.model_button)
        hint = QLabel(
            "Model được kiểm tra trước khi thay và áp dụng ngay, "
            "không cần bấm Lưu hay mở lại phần mềm."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        model_layout.addWidget(hint)
        left.addWidget(model_box)
        left.addStretch(1)

        # ----- Cột phải: hình ảnh -----
        images_box = QGroupBox("HÌNH ẢNH")
        images_layout = QVBoxLayout(images_box)
        images_layout.setSpacing(8)
        self.preview_labels = {}
        self.choose_buttons = {}
        self.clear_buttons = {}
        for key, caption, _max_side in IMAGE_SLOTS:
            row = QHBoxLayout()
            row.setSpacing(10)

            name = QLabel(caption)
            name.setFixedWidth(92)
            row.addWidget(name)

            preview = QLabel("Chưa có ảnh")
            preview.setObjectName("preview")
            preview.setAlignment(Qt.AlignCenter)
            preview.setFixedSize(PREVIEW_W, PREVIEW_H)
            self.preview_labels[key] = preview
            row.addWidget(preview)

            buttons = QVBoxLayout()
            buttons.setSpacing(6)
            choose = QPushButton("Chọn ảnh...")
            choose.setObjectName("secondary")
            choose.setCursor(Qt.PointingHandCursor)
            choose.clicked.connect(lambda _=False, k=key: self._choose_image(k))
            clear = QPushButton("Xóa ảnh")
            clear.setObjectName("danger")
            clear.setCursor(Qt.PointingHandCursor)
            clear.clicked.connect(lambda _=False, k=key: self._clear_image(k))
            self.choose_buttons[key] = choose
            self.clear_buttons[key] = clear
            buttons.addWidget(choose)
            buttons.addWidget(clear)
            row.addLayout(buttons)

            images_layout.addLayout(row)

        # Độ đậm của ảnh nền chìm
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(10)
        opacity_name = QLabel("Độ đậm nền")
        opacity_name.setFixedWidth(92)
        opacity_row.addWidget(opacity_name)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.opacity_slider, 1)
        self.opacity_value_label = QLabel()
        self.opacity_value_label.setFixedWidth(40)
        self.opacity_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        opacity_row.addWidget(self.opacity_value_label)
        images_layout.addLayout(opacity_row)

        # Khung xem trước ảnh nền hiển thị đúng độ đậm đang chọn
        self._preview_effect = QGraphicsOpacityEffect(self.preview_labels["watermark_image"])
        self.preview_labels["watermark_image"].setGraphicsEffect(self._preview_effect)

        hint_img = QLabel("Có thể để trống. Nên dùng ảnh PNG nền trong suốt cho logo.")
        hint_img.setObjectName("hint")
        hint_img.setWordWrap(True)
        images_layout.addWidget(hint_img)
        images_layout.addStretch(1)
        body.addWidget(images_box, 1)

        # ----- Hàng nút dưới cùng -----
        bottom = QHBoxLayout()
        self.restore_button = QPushButton("Khôi phục mặc định")
        self.restore_button.setObjectName("secondary")
        self.restore_button.setCursor(Qt.PointingHandCursor)
        self.restore_button.clicked.connect(self._restore_defaults)
        bottom.addWidget(self.restore_button)
        bottom.addStretch(1)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.setObjectName("secondary")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("Lưu")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self._on_save)
        bottom.addWidget(self.cancel_button)
        bottom.addWidget(self.save_button)
        root.addLayout(bottom)

    def _load_values(self):
        for key, edit in self.text_edits.items():
            edit.setText(self._branding.get(key, ""))
        self.opacity_slider.setValue(self._branding["watermark_opacity"])
        self._on_opacity_changed(self.opacity_slider.value())
        model_name = self.config.get("yolo_model_name") or "(chưa cấu hình)"
        self.model_name_label.setText(f"Model hiện tại: {model_name}")
        for key, _caption, _max_side in IMAGE_SLOTS:
            self._refresh_preview(key)

    # ------------------------------------------------------------------
    # HÌNH ẢNH
    # ------------------------------------------------------------------
    def _on_opacity_changed(self, value: int):
        self.opacity_value_label.setText(f"{value}%")
        self._preview_effect.setOpacity(max(0.15, value / 100.0))  # luôn đủ thấy để xem trước

    def _current_image_path(self, key: str) -> str:
        """Đường dẫn ảnh đang hiển thị: ảnh mới chọn nếu có, ngược lại ảnh đã lưu."""
        if key in self._pending:
            return self._pending[key]
        return find_branding_image(self._branding.get(key, "")) or ""

    def _refresh_preview(self, key: str):
        label = self.preview_labels[key]
        path = self._current_image_path(key)
        pixmap = QPixmap(path) if path else QPixmap()
        if pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("Chưa có ảnh")
            self.clear_buttons[key].setEnabled(False)
            return
        label.setText("")
        label.setPixmap(
            pixmap.scaled(
                PREVIEW_W - 8,
                PREVIEW_H - 8,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.clear_buttons[key].setEnabled(True)

    def _choose_image(self, key: str):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh", "", IMAGE_FILTER
        )
        if not path:
            return
        if QImage(path).isNull():
            QMessageBox.warning(
                self, "Cài đặt", "Không đọc được file ảnh này. Vui lòng chọn ảnh khác."
            )
            return
        self._pending[key] = path
        self._refresh_preview(key)

    def _clear_image(self, key: str):
        self._pending[key] = ""
        self._refresh_preview(key)

    @staticmethod
    def _import_image(src_path: str, key: str, max_side: int, assets_dir: str) -> str:
        """Chép ảnh vào thư mục dữ liệu (PNG, thu nhỏ nếu quá lớn); trả về tên file."""
        image = QImage(src_path)
        if image.isNull():
            raise ValueError(f"Không đọc được ảnh: {src_path}")
        if max(image.width(), image.height()) > max_side:
            image = image.scaled(
                max_side, max_side, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        file_name = f"{CUSTOM_PREFIX}{key}.png"
        if not image.save(os.path.join(assets_dir, file_name), "PNG"):
            raise OSError(f"Không lưu được ảnh vào {assets_dir}")
        return file_name

    @staticmethod
    def _remove_old_custom_image(old_name: str, new_name: str, assets_dir: str):
        """Xóa ảnh tùy chỉnh cũ không còn dùng (chỉ trong thư mục assets của ứng dụng)."""
        if not old_name or old_name == new_name or not old_name.startswith(CUSTOM_PREFIX):
            return
        old_path = os.path.abspath(os.path.join(assets_dir, old_name))
        if os.path.dirname(old_path) == os.path.abspath(assets_dir) and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError as e:
                logger.warning(f"Không xóa được ảnh cũ {old_path}: {e}")

    # ------------------------------------------------------------------
    # MẶC ĐỊNH / LƯU
    # ------------------------------------------------------------------
    def _restore_defaults(self):
        for key, edit in self.text_edits.items():
            edit.setText(DEFAULT_BRANDING[key])
        for key, _caption, _max_side in IMAGE_SLOTS:
            self._branding[key] = DEFAULT_BRANDING[key]
            self._pending.pop(key, None)
            self._refresh_preview(key)
        self.opacity_slider.setValue(DEFAULT_BRANDING["watermark_opacity"])

    def _on_save(self):
        result = dict(self._branding)
        for key, edit in self.text_edits.items():
            result[key] = edit.text().strip()
        result["watermark_opacity"] = clamp_opacity(self.opacity_slider.value())

        assets_dir = os.path.join(APP_DATA_DIR, "assets")
        try:
            os.makedirs(assets_dir, exist_ok=True)
            for key, _caption, max_side in IMAGE_SLOTS:
                if key not in self._pending:
                    continue
                source = self._pending[key]
                if source:
                    result[key] = self._import_image(source, key, max_side, assets_dir)
                else:
                    result[key] = ""
            for key, _caption, _max_side in IMAGE_SLOTS:
                self._remove_old_custom_image(
                    self._original.get(key, ""), result[key], assets_dir
                )
        except Exception as e:
            logger.error(f"Lỗi lưu cài đặt giao diện: {e}", exc_info=True)
            QMessageBox.warning(self, "Cài đặt", f"Không thể lưu hình ảnh: {e}")
            return

        self._result = result
        self.accept()

    def get_branding(self) -> dict:
        """Cấu hình giao diện đã lưu (chỉ hợp lệ sau khi hộp thoại được chấp nhận)."""
        return dict(self._result or self._branding)

    # ------------------------------------------------------------------
    # MODEL AI
    # ------------------------------------------------------------------
    def _choose_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file model AI mới (.pt)", "", "Model YOLO (*.pt)"
        )
        if not path:
            return
        self.set_model_busy(True)
        self.model_update_requested.emit(path)

    def set_model_busy(self, busy: bool):
        """Khóa nút khi đang kiểm tra/nạp model để tránh bấm lặp hoặc đóng giữa chừng."""
        self._model_busy = busy
        self.model_button.setEnabled(not busy)
        self.model_button.setText(
            "ĐANG CẬP NHẬT..." if busy else "Chọn file model AI mới (.pt)..."
        )
        for button in (self.save_button, self.cancel_button, self.restore_button):
            button.setEnabled(not busy)

    def reject(self):
        if self._model_busy:
            return
        super().reject()
