# file: core/triggers.py

import logging
import time

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class BluetoothTrigger(QObject):
    # Tín hiệu cũ (B41 + Trung liên bắn đơn): có cooldown chống đúp cò
    triggered = Signal()
    # Tín hiệu mới (Trung liên liên thanh): bắt đầu đè cò / nhả cò
    pressed = Signal()
    released = Signal()

    # Nếu quá thời gian này không có sự kiện phím nào mà vẫn chưa thấy nhả,
    # coi như remote bị kẹt tín hiệu nhả và cho phép nhận lần bóp cò mới.
    HOLD_STALE_TIMEOUT = 1.5

    def __init__(self):
        super().__init__()
        self.trigger_key = keyboard.Key.media_volume_up
        self.listener = None
        self.is_active = False
        self.last_shot_time = 0
        self.cooldown = 0.5  # Nghỉ 0.5 giây giữa mỗi phát bắn để chống đúp cò

        # Theo dõi trạng thái đè cò (chỉ dùng cho tín hiệu pressed/released)
        self._key_down = False
        self._last_key_event = 0.0

    def _is_trigger_key(self, key) -> bool:
        """Kiểm tra phím bấm (bao quát cả chuẩn pynput và mã Virtual Key của Windows)."""
        if key == self.trigger_key:
            return True
        if hasattr(key, "vk") and key.vk == 175:  # 175 là mã VK_VOLUME_UP trên Windows
            return True
        return False

    def on_press(self, key):
        if not self.is_active:
            return

        # Bỏ comment dòng dưới nếu muốn xem Terminal in ra chính xác nút bạn bấm là gì
        # logger.info(f"[Debug] Phím vừa bấm: {key}")

        if not self._is_trigger_key(key):
            return

        current_time = time.time()

        # --- Theo dõi đè cò: chỉ xử lý ở lần nhấn đầu tiên ---
        # (Windows tự lặp sự kiện on_press khi giữ phím, nên cần lọc)
        if (
            self._key_down
            and current_time - self._last_key_event > self.HOLD_STALE_TIMEOUT
        ):
            self._key_down = False
        self._last_key_event = current_time

        # Đang đè cò: bỏ qua các sự kiện lặp để mỗi lần đè chỉ tính 1 lần
        if self._key_down:
            return

        self._key_down = True
        self.pressed.emit()

        # --- Tín hiệu bắn đơn: chỉ phát ở lần nhấn đầu tiên, vẫn có cooldown chống đúp cò ---
        if current_time - self.last_shot_time > self.cooldown:
            self.last_shot_time = current_time
            logger.info(f"🎯 Phát hiện tín hiệu bóp cò hợp lệ từ phím: {key}")
            self.triggered.emit()
        else:
            logger.info("⏳ Bỏ qua tín hiệu (đang trong thời gian cooldown).")

    def on_release(self, key):
        # Logic bắn đơn vẫn bỏ qua việc nhả phím (tránh kẹt cò từ remote Bluetooth).
        # Chỉ dùng sự kiện nhả để báo kết thúc đè cò cho chế độ liên thanh.
        if self._is_trigger_key(key) and self._key_down:
            self._key_down = False
            self.released.emit()

    def activate(self):
        """Bật chức năng lắng nghe."""
        logger.info("Trigger đã được BẬT.")
        self.is_active = True

    def deactivate(self):
        """Tắt chức năng lắng nghe."""
        logger.info("Trigger đã được TẮT.")
        self.is_active = False

    def start_global_listener(self):
        """Khởi động luồng lắng nghe một lần duy nhất."""
        if self.listener is None:
            self.listener = keyboard.Listener(
                on_press=self.on_press, on_release=self.on_release
            )
            self.listener.start()
            logger.info("Luồng lắng nghe phím bấm toàn cục đã bắt đầu.")

    def stop_global_listener(self):
        """Dừng luồng lắng nghe khi thoát ứng dụng."""
        if self.listener is not None:
            self.listener.stop()
            self.listener.join()
            self.listener = None
            logger.info("Luồng lắng nghe phím bấm toàn cục đã dừng.")
