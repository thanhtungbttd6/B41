# utils/audio.py
import logging
import os

import pygame
from PySide6.QtCore import QTimer

from utils.resource_path import resource_path

logger = logging.getLogger(__name__)


class AudioManager:
    """
    Lớp quản lý âm thanh sử dụng pygame.mixer.

    Ngoài việc phát âm thanh rời, lớp này hỗ trợ phát NỐI TIẾP một chuỗi âm thanh
    (ví dụ: tiếng bắn -> tiếng nổ -> thông báo kết quả) trên một kênh riêng,
    đảm bảo âm thanh sau chỉ phát khi âm thanh trước đã kết thúc.
    """

    SEQUENCE_POLL_MS = 15

    def __init__(self):
        self._queue = []
        self._seq_channel = None
        self._seq_timer = QTimer()
        self._seq_timer.setInterval(self.SEQUENCE_POLL_MS)
        self._seq_timer.timeout.connect(self._advance_sequence)

        try:
            pygame.mixer.init()
            # Tăng số kênh để tiếng nổ liên thanh không bị cắt khi bắn nhanh
            pygame.mixer.set_num_channels(16)
            # Dành riêng kênh 0 cho chuỗi âm thanh nối tiếp
            pygame.mixer.set_reserved(1)
            self._seq_channel = pygame.mixer.Channel(0)
            self.sounds = {}
            logger.info("Pygame mixer đã được khởi tạo thành công.")
            self._load_sounds()
        except pygame.error as e:
            logger.error(
                f"Lỗi khi khởi tạo pygame.mixer: {e}. Âm thanh sẽ không hoạt động."
            )
            self.sounds = None

    def _load_sounds(self):
        """Tải các file âm thanh cần thiết."""
        if self.sounds is None:
            return
        logger.info("Đang tải các file âm thanh...")

        sounds_dir = resource_path(os.path.join("assets", "sounds"))

        # Load các file cứng: shot (dự phòng), miss, hit và tiếng nổ riêng của Trung liên
        sound_names = ["shot", "miss", "hit", "trung_lien_shot"]

        for name in sound_names:
            file_name = f"{name}.mp3"
            sound_path = os.path.join(sounds_dir, file_name)

            if os.path.exists(sound_path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(sound_path)
                except pygame.error as e:
                    logger.error(f"Lỗi khi tải file âm thanh '{name}': {e}")
            else:
                logger.warning(f"Không tìm thấy file âm thanh: {sound_path}")

    def has_sound(self, name: str) -> bool:
        """Kiểm tra một âm thanh đã được tải thành công hay chưa."""
        return bool(self.sounds) and name in self.sounds

    def play_sound(self, name: str):
        """Phát một âm thanh đã được tải dựa theo tên."""
        if self.sounds and name in self.sounds:
            self.sounds[name].play()
        elif self.sounds is None:
            logger.warning(
                "Không thể phát âm thanh vì pygame.mixer chưa được khởi tạo."
            )
        else:
            logger.warning(f"Không tìm thấy âm thanh có tên: '{name}'")

    # ==============================================
    # CHUỖI ÂM THANH NỐI TIẾP
    # ==============================================

    def start_sequence(self, names):
        """Dừng chuỗi đang phát (nếu có) và bắt đầu chuỗi mới."""
        self.stop_sequence()
        self.enqueue_sounds(names)

    def enqueue_sounds(self, names):
        """Thêm âm thanh vào cuối hàng đợi; phát ngay nếu kênh đang rảnh."""
        if self.sounds is None or self._seq_channel is None:
            logger.warning(
                "Không thể phát âm thanh vì pygame.mixer chưa được khởi tạo."
            )
            return
        self._queue.extend(names)
        if not self._seq_timer.isActive():
            self._seq_timer.start()
        self._advance_sequence()

    def stop_sequence(self):
        """Dừng và xóa toàn bộ chuỗi âm thanh nối tiếp."""
        self._queue.clear()
        self._seq_timer.stop()
        if self._seq_channel is not None:
            self._seq_channel.stop()

    def _advance_sequence(self):
        """Phát âm thanh kế tiếp khi âm thanh trước đã kết thúc."""
        if self.sounds is None or self._seq_channel is None:
            self._queue.clear()
            self._seq_timer.stop()
            return

        if not self._seq_channel.get_busy():
            while self._queue:
                name = self._queue.pop(0)
                sound = self.sounds.get(name)
                if sound is None:
                    logger.warning(f"Bỏ qua âm thanh không tồn tại: '{name}'")
                    continue
                self._seq_channel.play(sound)
                break

        if not self._queue:
            self._seq_timer.stop()

    # Thêm các hàm hỗ trợ logic Trúng/Trượt trực tiếp
    def play_hit(self):
        """Phát tiếng báo Trúng."""
        self.play_sound("hit")

    def play_miss(self):
        """Phát tiếng báo Trượt."""
        self.play_sound("miss")

    def play_shot(self):
        """Phát tiếng Nổ súng."""
        self.play_sound("shot")

    def play_trung_lien_shot(self):
        """Phát tiếng nổ riêng của Trung liên (dùng cho liên thanh).

        Nếu chưa có file assets/sounds/trung_lien_shot.mp3 thì tạm dùng
        tiếng nổ mặc định (shot.mp3) để chức năng vẫn hoạt động.
        """
        if self.sounds and "trung_lien_shot" in self.sounds:
            self.sounds["trung_lien_shot"].play()
        else:
            self.play_shot()
