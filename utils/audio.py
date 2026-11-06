# utils/audio.py
import logging
import os
import pygame
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class AudioManager:
    """
    Lớp quản lý âm thanh sử dụng pygame.mixer.
    """
    def __init__(self):
        try:
            pygame.mixer.init()
            self.sounds = {}
            logger.info("Pygame mixer đã được khởi tạo thành công.")
            self._load_sounds()
        except pygame.error as e:
            logger.error(f"Lỗi khi khởi tạo pygame.mixer: {e}. Âm thanh sẽ không hoạt động.")
            self.sounds = None

    def _load_sounds(self):
        """Tải các file âm thanh cần thiết."""
        if self.sounds is None: return
        logger.info("Đang tải các file âm thanh...")
        
        sounds_dir = resource_path(os.path.join("assets", "sounds"))

        # Load các file cứng: shot, miss, hit
        sound_names = ['shot', 'miss', 'hit']
        
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

    def play_sound(self, name: str):
        """Phát một âm thanh đã được tải dựa theo tên."""
        if self.sounds and name in self.sounds:
            self.sounds[name].play()
        elif self.sounds is None:
            logger.warning("Không thể phát âm thanh vì pygame.mixer chưa được khởi tạo.")
        else:
            logger.warning(f"Không tìm thấy âm thanh có tên: '{name}'")
            
    # Thêm các hàm hỗ trợ logic Trúng/Trượt trực tiếp
    def play_hit(self):
        """Phát tiếng báo Trúng."""
        self.play_sound('hit')

    def play_miss(self):
        """Phát tiếng báo Trượt."""
        self.play_sound('miss')

    def play_shot(self):
        """Phát tiếng Nổ súng."""
        self.play_sound('shot')