"""B41 - Trung Lien Window Controller."""

import logging
import time
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QPoint, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMainWindow

from utils.audio import AudioManager
from utils.camera import Camera, find_available_cameras

from ..ui.ui_trung_lien import TrungLienGui

logger = logging.getLogger(__name__)


class TrungLienWindow(QMainWindow):
    """Cửa sổ giao diện Trung liên: camera, zoom, hiệu chỉnh tâm, bắn đơn/liên thanh."""

    # Gửi ảnh đến worker nhận diện (chỉ dùng ở chế độ phát một)
    request_processing = Signal(np.ndarray, object, str)

    # Giới hạn số viên tối đa trong một loạt bắn (chống đè cò)
    MAX_BURST_SHOTS = 7
    # Chu kỳ kiểm tra thời điểm bắn của liên thanh (ms)
    BURST_TICK_MS = 5

    def __init__(self, config=None, trigger=None):
        super().__init__()

        self.config = config or {}
        self.bt_trigger = trigger
        self.gui = TrungLienGui()

        self.setWindowTitle("LUYỆN TẬP TRUNG LIÊN")
        self.setMinimumSize(1100, 720)
        self.setCentralWidget(self.gui)

        self.back_button = self.gui.back_button

        # --- TRẠNG THÁI CAMERA (logic giống PracticeWindow) ---
        self.cam = None
        self.final_size = (480, 640)
        self.zoom_level = 1.0
        self.calibrated_center = None
        self.is_camera_connected = False
        self.frame_read_failures = 0
        self.FRAME_FAILURE_THRESHOLD = 3

        self.clean_zoomed_frame_for_processing = None
        self.shot_point_on_zoomed_frame = None

        self.video_timer = QTimer(self)

        # --- TRẠNG THÁI BẮN ---
        self.audio_manager = AudioManager()
        self._screen_active = False

        # Mã phát bắn đơn đang chờ kết quả nhận diện (None = không chờ)
        self._last_single_timestamp = None

        # Các phát đã chụp của loạt bắn hiện tại
        self.shot_results = []
        self.current_shot_index = -1

        # Trạng thái loạt bắn liên thanh
        self._burst_active = False
        self._burst_interval = 0.0
        self._burst_start_time = 0.0
        self._burst_shots_fired = 0
        self.burst_timer = QTimer(self)
        self.burst_timer.setTimerType(Qt.PreciseTimer)
        self.burst_timer.setInterval(self.BURST_TICK_MS)
        self.burst_timer.timeout.connect(self._on_burst_tick)

        # --- KẾT NỐI TÍN HIỆU CAMERA ---
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)

        self.gui.camera_selector.currentIndexChanged.connect(self.on_camera_selected)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_list)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)

        # --- KẾT NỐI ĐIỀU HƯỚNG ẢNH KẾT QUẢ ---
        self.gui.prev_shot_button.clicked.connect(self.show_previous_shot)
        self.gui.next_shot_button.clicked.connect(self.show_next_shot)

        logger.info("Đã khởi tạo giao diện Trung liên.")

    # ==============================================
    # CAMERA SELECTION
    # ==============================================

    def on_camera_selected(self, index):
        cam_idx = self.gui.camera_selector.currentData()
        if cam_idx is None:
            return
        if (
            self.cam
            and hasattr(self.cam, "index")
            and self.cam.index == cam_idx
            and self.cam.isOpened()
        ):
            return
        logger.info(f"Trung liên: người dùng chọn chuyển sang Camera {cam_idx}")
        self.connect_camera(cam_idx)
        self.config["camera_index"] = cam_idx

    def refresh_camera_list(self):
        logger.info("Trung liên: đang làm mới danh sách camera...")
        self.gui.camera_selector.blockSignals(True)
        self.gui.camera_selector.clear()

        available_indexes = find_available_cameras()

        if not available_indexes:
            self.gui.camera_selector.addItem("Không tìm thấy Camera", None)
            self.disconnect_camera("Không tìm thấy thiết bị nào")
        else:
            target_index = self.config.get("camera_index", 0)
            best_match_index = 0

            for i, cam_idx in enumerate(available_indexes):
                display_name = f"Camera {cam_idx}"
                self.gui.camera_selector.addItem(display_name, cam_idx)
                if cam_idx == target_index:
                    best_match_index = i

            self.gui.camera_selector.setCurrentIndex(best_match_index)
            selected_cam_idx = self.gui.camera_selector.itemData(best_match_index)
            self.connect_camera(selected_cam_idx)

        self.gui.camera_selector.blockSignals(False)

    def start_camera(self):
        logger.info("Màn hình Trung liên: kích hoạt camera và trigger...")
        self._screen_active = True
        if self.bt_trigger:
            self.bt_trigger.activate()
        self.refresh_camera_list()

    # ==============================================
    # CAMERA CONNECTION
    # ==============================================

    def connect_camera(self, index):
        self.disconnect_camera()

        logger.info(f"Trung liên: đang thử kết nối camera index {index}...")
        self.cam = Camera(index)

        if not self.cam.isOpened():
            logger.error(f"Lỗi driver camera {index}.")
            self.gui.clear_video_feed(f"Lỗi kết nối Camera {index}")
            return

        attempts = 0
        success = False
        while attempts < 10:
            ret, frame = self.cam.read()
            if ret and frame is not None:
                success = True
                break
            time.sleep(0.2)
            attempts += 1

        if success:
            self.is_camera_connected = True
            self.video_timer.start(30)
            logger.info(f"Trung liên: kết nối thành công Camera {index}")
        else:
            logger.error(f"Camera {index} mở được nhưng không trả về hình ảnh.")
            self.disconnect_camera("Camera không phản hồi hình ảnh")

    def disconnect_camera(self, message="Vui lòng chọn camera"):
        self._finish_burst()
        self.video_timer.stop()
        if self.cam:
            self.cam.release()
        self.cam = None
        self.is_camera_connected = False
        self.gui.clear_video_feed(message)
        logger.info(f"Trung liên: đã ngắt kết nối camera. Lý do: {message}")

    # ==============================================
    # FRAME PROCESSING
    # ==============================================

    def update_frame(self):
        if not (self.cam and self.cam.isOpened()):
            return

        ret, frame = self.cam.read()
        if not ret or frame is None:
            self.frame_read_failures += 1
            if self.frame_read_failures > self.FRAME_FAILURE_THRESHOLD:
                self.disconnect_camera(
                    "Mất kết nối với camera...\nVui lòng kiểm tra và nhấn 'Làm mới'."
                )
            return

        self.frame_read_failures = 0
        if not self.is_camera_connected:
            self.is_camera_connected = True

        processed_frame = self.crop_and_resize_frame(frame)
        if processed_frame is None:
            return

        self.clean_zoomed_frame_for_processing = self.apply_digital_zoom(
            processed_frame, self.zoom_level
        )

        point_to_draw = None
        h_orig, w_orig, _ = processed_frame.shape
        h_zoom, w_zoom, _ = self.clean_zoomed_frame_for_processing.shape

        if self.calibrated_center:
            cx, cy = self.calibrated_center
            start_x_on_orig = (w_orig - int(w_orig / self.zoom_level)) // 2
            start_y_on_orig = (h_orig - int(h_orig / self.zoom_level)) // 2

            if cx >= start_x_on_orig and cy >= start_y_on_orig:
                zoomed_cx = int((cx - start_x_on_orig) * self.zoom_level)
                zoomed_cy = int((cy - start_y_on_orig) * self.zoom_level)
                if zoomed_cx < w_zoom and zoomed_cy < h_zoom:
                    point_to_draw = (zoomed_cx, zoomed_cy)
        else:
            point_to_draw = (w_zoom // 2, h_zoom // 2)

        self.shot_point_on_zoomed_frame = point_to_draw

        frame_to_display = self.clean_zoomed_frame_for_processing.copy()
        if self.shot_point_on_zoomed_frame:
            cv2.drawMarker(
                frame_to_display,
                self.shot_point_on_zoomed_frame,
                (0, 0, 255),
                cv2.MARKER_CROSS,
                15,
                1,
            )

        self.gui.display_frame(frame_to_display)

    def crop_and_resize_frame(self, frame):
        h, w, _ = frame.shape
        target_aspect_ratio = 3.0 / 4.0
        new_w = int(h * target_aspect_ratio)
        start_x = (w - new_w) // 2 if w > new_w else 0
        cropped_frame = frame[:, start_x : start_x + new_w]
        return cv2.resize(cropped_frame, self.final_size, interpolation=cv2.INTER_AREA)

    def apply_digital_zoom(self, frame, zoom):
        if frame is None or zoom <= 1.0:
            return frame
        h, w, _ = frame.shape
        crop_w, crop_h = int(w / zoom), int(h / zoom)
        start_x, start_y = (w - crop_w) // 2, (h - crop_h) // 2
        cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_CUBIC)

    # ==============================================
    # CALIBRATION & ZOOM
    # ==============================================

    def toggle_calibration_mode(self):
        is_calibrating = not self.gui.camera_view_label._is_calibrating
        self.gui.camera_view_label.set_calibration_mode(is_calibrating)
        self.gui.calibrate_button.setText("Hủy" if is_calibrating else "Hiệu chỉnh tâm")

    def set_new_center(self, click_pos: QPoint):
        widget_size = self.gui.camera_view_label.size()
        img_w, img_h = self.final_size
        scale = min(widget_size.width() / img_w, widget_size.height() / img_h)
        display_w, display_h = int(img_w * scale), int(img_h * scale)
        offset_x, offset_y = (widget_size.width() - display_w) // 2, (
            widget_size.height() - display_h
        ) // 2
        if not (
            offset_x <= click_pos.x() < offset_x + display_w
            and offset_y <= click_pos.y() < offset_y + display_h
        ):
            return
        click_on_display_x = click_pos.x() - offset_x
        click_on_display_y = click_pos.y() - offset_y
        click_on_zoomed_image_x = int(click_on_display_x / scale)
        click_on_zoomed_image_y = int(click_on_display_y / scale)
        start_x_on_original = (img_w - int(img_w / self.zoom_level)) // 2
        start_y_on_original = (img_h - int(img_h / self.zoom_level)) // 2
        final_img_x = int(
            start_x_on_original + (click_on_zoomed_image_x / self.zoom_level)
        )
        final_img_y = int(
            start_y_on_original + (click_on_zoomed_image_y / self.zoom_level)
        )
        self.calibrated_center = (final_img_x, final_img_y)
        self.toggle_calibration_mode()

    def on_zoom_changed(self, value):
        self.zoom_level = value / 10.0

    # ==============================================
    # SHOOTING: TRIGGER HANDLERS
    # ==============================================

    def _can_shoot(self) -> bool:
        """Kiểm tra điều kiện để chụp một phát."""
        if not self._screen_active:
            return False
        if not self.is_camera_connected:
            logger.warning("Trung liên: bắn bị chặn vì camera chưa kết nối.")
            return False
        if self.clean_zoomed_frame_for_processing is None:
            logger.error("Trung liên: chưa có khung hình sạch để chụp.")
            return False
        return True

    @Slot()
    def on_trigger_single(self):
        """Bóp cò ở chế độ bắn đơn (Liên thanh TẮT): chụp 1 phát, nhận diện, báo kết quả."""
        if self.gui.is_burst_enabled() or self._burst_active:
            return
        if not self._can_shoot():
            return

        self.shot_results = []
        self.current_shot_index = -1
        self._last_single_timestamp = None
        self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Kết quả: --")

        if not self._capture_shot(single=True):
            return

        shot = self.shot_results[-1]
        self._last_single_timestamp = shot["timestamp"]
        # Gửi bản sao để worker không vẽ đè lên ảnh sạch đã lưu
        self.request_processing.emit(
            shot["frame"].copy(), shot["point"], shot["timestamp"]
        )

    @Slot(dict)
    def on_processing_finished(self, result):
        """Nhận kết quả nhận diện của phát bắn đơn và đọc thông báo Trúng/Trượt."""
        if not self._screen_active:
            return
        # Bỏ qua kết quả không phải của phát bắn đơn hiện tại
        # (kết quả của B41, của phát cũ, hoặc khi đã chuyển sang liên thanh)
        if (
            self._last_single_timestamp is None
            or result.get("image_path") != self._last_single_timestamp
        ):
            return

        score = result.get("score", 0)
        if score == 1:
            self.audio_manager.enqueue_sounds(["hit"])
            score_text = "TRÚNG"
        else:
            self.audio_manager.enqueue_sounds(["miss"])
            score_text = "TRƯỢT"

        self.gui.target_name_label.setText(f"Tên mục tiêu: {result.get('target_name')}")
        self.gui.score_label.setText(f"Kết quả: {score_text}")

        result_frame = result.get("result_frame")
        if result_frame is not None:
            self.gui.show_result_image(result_frame)

    @Slot()
    def on_trigger_pressed(self):
        """Bắt đầu đè cò: nếu Liên thanh BẬT thì khởi động loạt bắn."""
        if not self._screen_active:
            return
        if not self.gui.is_burst_enabled() or self._burst_active:
            return
        if not self._can_shoot():
            return
        self._start_burst()

    @Slot()
    def on_trigger_released(self):
        """Nhả cò: kết thúc loạt bắn đang chạy (nếu có)."""
        if self._burst_active:
            logger.info(
                f"Trung liên: nhả cò, kết thúc loạt bắn ({self._burst_shots_fired} viên)."
            )
            self._finish_burst()

    # ==============================================
    # SHOOTING: BURST MECHANISM
    # ==============================================

    def _start_burst(self):
        rate = max(1, self.gui.rate_slider.value())  # viên/phút
        self._burst_interval = 60.0 / rate  # giây giữa hai viên
        self._burst_shots_fired = 0
        self._burst_active = True

        self.shot_results = []
        self.current_shot_index = -1

        # Liên thanh không nhận diện: bỏ kết quả bắn đơn cũ (nếu còn chờ)
        self._last_single_timestamp = None
        self.audio_manager.stop_sequence()
        self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Kết quả: --")

        logger.info(
            f"Trung liên: bắt đầu loạt bắn {rate} viên/phút "
            f"(tối đa {self.MAX_BURST_SHOTS} viên)."
        )

        self._burst_start_time = time.perf_counter()
        self.burst_timer.start()
        # Viên đầu tiên bắn ngay khi bóp cò
        self._on_burst_tick()

    def _on_burst_tick(self):
        """Bắn viên kế tiếp khi đến thời điểm tương ứng với tốc độ bắn.

        Dùng mốc thời gian tuyệt đối thay vì cộng dồn khoảng trễ của timer,
        nên tốc độ trung bình luôn đúng với giá trị trên thanh kéo.
        """
        if not self._burst_active:
            return

        elapsed = time.perf_counter() - self._burst_start_time
        shots_due = int(elapsed / self._burst_interval) + 1

        if (
            shots_due > self._burst_shots_fired
            and self._burst_shots_fired < self.MAX_BURST_SHOTS
        ):
            if self._capture_shot():
                self._burst_shots_fired += 1
            else:
                # Không chụp được (mất camera/khung hình) -> dừng loạt bắn
                self._finish_burst()
                return

        if self._burst_shots_fired >= self.MAX_BURST_SHOTS:
            logger.info(
                f"Trung liên: đạt giới hạn {self.MAX_BURST_SHOTS} viên/loạt, "
                "bỏ qua phần đè cò còn lại."
            )
            self._finish_burst()

    def _finish_burst(self):
        """Dừng loạt bắn (an toàn khi gọi nhiều lần)."""
        self.burst_timer.stop()
        self._burst_active = False

    # ==============================================
    # SHOOTING: CAPTURE & RESULT DISPLAY
    # ==============================================

    def _capture_shot(self, single=False) -> bool:
        """Chụp một phát: phát tiếng nổ, lưu khung hình sạch và hiển thị.

        single=True (bắn đơn): tiếng nổ phát trên kênh nối tiếp để thông báo
        Trúng/Trượt được đọc sau khi tiếng nổ kết thúc.
        single=False (liên thanh): phát tiếng nổ chồng lên nhau, không báo kết quả.
        """
        frame = self.clean_zoomed_frame_for_processing
        if frame is None:
            return False

        if single:
            shot_name = (
                "trung_lien_shot"
                if self.audio_manager.has_sound("trung_lien_shot")
                else "shot"
            )
            self.audio_manager.start_sequence([shot_name])
        else:
            self.audio_manager.play_trung_lien_shot()

        self.shot_results.append(
            {
                "frame": frame.copy(),  # ảnh sạch, dùng cho nhận diện
                "point": self.shot_point_on_zoomed_frame,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
            }
        )
        self.current_shot_index = len(self.shot_results) - 1
        self._refresh_result_view()
        return True

    def _refresh_result_view(self):
        """Hiển thị phát đang chọn lên khung kết quả và cập nhật điều hướng."""
        total = len(self.shot_results)
        if total == 0 or not (0 <= self.current_shot_index < total):
            self.gui.clear_result_image()
            return

        shot = self.shot_results[self.current_shot_index]
        image = shot["frame"].copy()
        if shot["point"]:
            cv2.drawMarker(
                image,
                shot["point"],
                (0, 0, 255),
                cv2.MARKER_CROSS,
                15,
                1,
            )

        self.gui.show_result_image(image)
        self.gui.set_shot_navigation(self.current_shot_index, total)

    def show_previous_shot(self):
        if self.current_shot_index > 0:
            self.current_shot_index -= 1
            self._refresh_result_view()

    def show_next_shot(self):
        if self.current_shot_index < len(self.shot_results) - 1:
            self.current_shot_index += 1
            self._refresh_result_view()

    # ==============================================
    # LIFECYCLE
    # ==============================================

    def shutdown_components(self):
        """Ngắt camera, tắt trigger và đưa giao diện về trạng thái ban đầu."""
        self._screen_active = False
        self._last_single_timestamp = None
        self._finish_burst()
        self.audio_manager.stop_sequence()
        self.disconnect_camera("Camera Trung liên chưa được kết nối")
        if self.bt_trigger:
            self.bt_trigger.deactivate()
        self.reset_ui_state()

    def reset_ui_state(self):
        """Đưa giao diện về trạng thái ban đầu."""
        self.shot_results = []
        self.current_shot_index = -1

        self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Kết quả: --")

        self.gui.clear_result_image()
