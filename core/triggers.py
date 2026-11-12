# file: core/triggers.py

import logging
import time
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

logger = logging.getLogger(__name__)

class BluetoothTrigger(QObject):
    triggered = Signal()

    def __init__(self):
        super().__init__()
        self.trigger_key = keyboard.Key.media_volume_up
        self.listener = None
        self.is_active = False
        self.last_shot_time = 0
        self.cooldown = 0.5  # Nghỉ 0.5 giây giữa mỗi phát bắn để chống đúp cò

    def on_press(self, key):
        if not self.is_active:
            return
        
        # Bỏ comment dòng dưới nếu muốn xem Terminal in ra chính xác nút bạn bấm là gì
        # logger.info(f"[Debug] Phím vừa bấm: {key}") 
        
        # Kiểm tra phím bấm (bao quát cả chuẩn pynput và mã Virtual Key của Windows)
        is_trigger = False
        if key == self.trigger_key:
            is_trigger = True
        elif hasattr(key, 'vk') and key.vk == 175: # 175 là mã VK_VOLUME_UP trên Windows
            is_trigger = True
            
        if is_trigger:
            current_time = time.time()
            if current_time - self.last_shot_time > self.cooldown:
                self.last_shot_time = current_time
                logger.info(f"🎯 Phát hiện tín hiệu bóp cò hợp lệ từ phím: {key}")
                self.triggered.emit()
            else:
                logger.info("⏳ Bỏ qua tín hiệu (đang trong thời gian cooldown).")

    def on_release(self, key):
        # Bỏ qua hoàn toàn logic nhả phím để tránh lỗi kẹt cò từ remote Bluetooth
        pass

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
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.start()
            logger.info("Luồng lắng nghe phím bấm toàn cục đã bắt đầu.")

    def stop_global_listener(self):
        """Dừng luồng lắng nghe khi thoát ứng dụng."""
        if self.listener is not None:
            self.listener.stop()
            self.listener.join()
            self.listener = None
            logger.info("Luồng lắng nghe phím bấm toàn cục đã dừng.")