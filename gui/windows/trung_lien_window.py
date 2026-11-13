"""B41 - Trung Lien Window Controller."""

import logging
import time

import cv2
from PySide6.QtCore import QPoint, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMainWindow

from utils.camera import Camera, find_available_cameras

from ..ui.ui_trung_lien import TrungLienGui

logger = logging.getLogger(__name__)


class TrungLienWindow(QMainWindow):
    """Cửa sổ giao diện Trung liên: camera, zoom, hiệu chỉnh tâm (giống B41)."""

    def __init__(self, config=None):
        super().__init__()

        self.config = config or {}
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

        # --- KẾT NỐI TÍN HIỆU CAMERA ---
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)

        self.gui.camera_selector.currentIndexChanged.connect(self.on_camera_selected)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_list)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)

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
        logger.info("Màn hình Trung liên: kích hoạt camera...")
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
    # LIFECYCLE
    # ==============================================

    def shutdown_components(self):
        """Ngắt camera và đưa giao diện về trạng thái ban đầu khi rời màn hình."""
        self.disconnect_camera("Camera Trung liên chưa được kết nối")
        self.reset_ui_state()

    def reset_ui_state(self):
        """Đưa giao diện về trạng thái ban đầu."""

        self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Kết quả: --")

        self.gui.result_image_label.setPixmap(QPixmap())
        self.gui.result_image_label.setText("Chưa có ảnh kết quả")
