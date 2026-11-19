"""Hàm dùng chung để hiển thị tên bia."""


def display_target_name(raw) -> str:
    """Đổi tên lớp của model (ví dụ 'bia_so_15') thành tên hiển thị ('Bia số 15')."""
    if raw == "Chưa nhận diện":
        return "Chưa nhận diện"
    if not raw or raw == "Trượt":
        return "Ngoài bia"
    if raw == "bia_so_7_8":  # dữ liệu của phiên bản cũ
        return "Bia số 7"
    if raw.startswith("bia_so_"):
        return f"Bia số {raw[len('bia_so_'):]}"
    text = raw.replace("_", " ").strip()
    return text[:1].upper() + text[1:]
