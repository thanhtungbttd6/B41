"""Cấu hình giao diện (tiêu đề, chân trang, logo, ảnh nền chìm) do người dùng tự cài đặt.

Dữ liệu lưu trong config.json, mục "branding". Máy chưa từng cài đặt thì lấy
giá trị từ các khóa cũ của config (labels.app_footer, labels.logo_left...)
nên giao diện không đổi sau khi cập nhật phần mềm.
"""

import json
import logging
import os

from config import APP_DATA_DIR
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

TEXT_KEYS = ("title_1", "title_2", "footer_1", "footer_2")
IMAGE_KEYS = ("logo_left", "logo_right", "watermark_image")
BRANDING_KEYS = TEXT_KEYS + IMAGE_KEYS

# Giá trị mặc định (dùng cho nút "Khôi phục mặc định")
DEFAULT_BRANDING = {
    "title_1": "SÁNG KIẾN CẢI TIẾN KỸ THUẬT",
    "title_2": "ỨNG DỤNG AI KIỂM TRA ĐƯỜNG NGẮM SÚNG HỎA LỰC BỘ BINH",
    "footer_1": "Thông tin cá nhân",
    "footer_2": "Thông tin đơn vị",
    "logo_left": "logo_left.png",
    "logo_right": "logo_right.png",
    "watermark_image": "watermark.png",
}


def _legacy_branding(config: dict) -> dict:
    """Giá trị lấy từ các khóa cũ, dùng khi người dùng chưa cài đặt lần nào."""
    labels = config.get("labels", {}) or {}
    branding = dict(DEFAULT_BRANDING)

    footer_text = labels.get("app_footer") or ""
    if footer_text.strip():
        lines = footer_text.split("\n")
        branding["footer_1"] = lines[0].strip()
        branding["footer_2"] = " ".join(x.strip() for x in lines[1:]).strip()

    branding["logo_left"] = (
        config.get("logo_left") or labels.get("logo_left") or DEFAULT_BRANDING["logo_left"]
    )
    branding["logo_right"] = (
        config.get("logo_right")
        or labels.get("logo_right")
        or DEFAULT_BRANDING["logo_right"]
    )
    branding["watermark_image"] = (
        config.get("watermark_image") or DEFAULT_BRANDING["watermark_image"]
    )
    return branding


def get_branding(config: dict) -> dict:
    """Cấu hình giao diện hiện hành. Giá trị rỗng ('') nghĩa là người dùng cố ý để trống."""
    branding = _legacy_branding(config)
    stored = config.get("branding")
    if isinstance(stored, dict):
        for key in BRANDING_KEYS:
            value = stored.get(key)
            if isinstance(value, str):
                branding[key] = value
    return branding


def footer_text(branding: dict) -> str:
    """Ghép chân trang 1 và 2 (bỏ dòng trống)."""
    lines = [branding.get("footer_1", "").strip(), branding.get("footer_2", "").strip()]
    return "\n".join(x for x in lines if x)


def find_branding_image(path_raw):
    """Tìm file ảnh trong thư mục dữ liệu và thư mục ứng dụng; không thấy thì trả None."""
    if not path_raw:
        return None

    candidates = [
        path_raw,
        os.path.join(APP_DATA_DIR, "assets", os.path.basename(path_raw)),
        os.path.join(APP_DATA_DIR, path_raw),
        resource_path(path_raw),
        resource_path(os.path.join("assets", os.path.basename(path_raw))),
    ]
    checked = set()
    for candidate in candidates:
        full_path = os.path.abspath(os.path.normpath(candidate))
        if full_path in checked:
            continue
        checked.add(full_path)
        if os.path.isfile(full_path):
            return full_path
    return None


def save_config(config: dict, path: str | None = None):
    """Ghi config.json an toàn (ghi file tạm rồi đổi tên để không hỏng file khi mất điện)."""
    path = path or os.path.join(APP_DATA_DIR, "config.json")
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    os.replace(tmp_path, path)
