# file: gui/windows/practice_window.py

import logging
import os
import time
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QPoint, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap, QScreen
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
)

from config import APP_DATA_DIR
from core.database import DatabaseManager, save_shot_image
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from utils.audio import AudioManager
from utils.camera import Camera, find_available_cameras

from utils.display import display_target_name as format_target_name

from ..ui.ui_practice import MainGui

logger = logging.getLogger(__name__)


class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)

    def __init__(
        self,
        worker: ProcessingWorker,
        trigger: BluetoothTrigger,
        config: dict,
        db: DatabaseManager,
    ):
        super().__init__()
        self.config = config
        self.db = db
        labels = self.config.get("labels", {})
        app_title = labels.get("app_title", "Phần Mềm Bắn Súng")
        self.setWindowTitle(app_title)
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)

        self.gui = MainGui(self.config)
        self.setCentralWidget(self.gui)

        self.worker = worker
        self.bt_trigger = trigger
        self.cam = None
        self.final_size = (480, 640)
        self.zoom_level = 1.0
        self.calibrated_center = None
        self.is_camera_connected = False
        self.frame_read_failures = 0
        self.FRAME_FAILURE_THRESHOLD = 3

        self.clean_zoomed_frame_for_processing = None
        self.shot_point_on_zoomed_frame = None

        # Mã phát bắn gần nhất: chỉ kết quả của phát này mới được đọc thông báo
        self._last_shot_timestamp = None

        # --- PHIÊN BẮN ---
        self.active_session_id = None
        self.is_session_active = False
        self.shot_counter = 0
        # Phát bắn đã gửi đi nhưng chưa có kết quả: {timestamp: id phiên}
        self._pending_shots = {}

        self.audio_manager = AudioManager()
        self.video_timer = QTimer(self)

        # --- KẾT NỐI TÍN HIỆU CAMERA ---
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)

        self.gui.camera_selector.currentIndexChanged.connect(self.on_camera_selected)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_list)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)

        self.gui.session_button.clicked.connect(self.toggle_session)
        self.gui.soldier_selector.currentIndexChanged.connect(self.reset_ui_state)

        self.reset_ui_state()
        self.populate_soldier_selector()

        try:
            self.configured_camera_index = int(self.config.get("camera_index", 0))
        except (ValueError, TypeError):
            self.configured_camera_index = 0

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
        logger.info(f"Người dùng chọn chuyển sang Camera {cam_idx}")
        self.connect_camera(cam_idx)
        self.config["camera_index"] = cam_idx

    def refresh_camera_list(self):
        logger.info("Đang làm mới danh sách camera...")
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
        logger.info("Màn hình luyện tập: Kích hoạt camera và trigger...")
        if self.bt_trigger:
            self.bt_trigger.activate()
        if not self.is_session_active:
            self.populate_soldier_selector()
        self.refresh_camera_list()

    def connect_camera(self, index):
        self.disconnect_camera()

        logger.info(f"Đang thử kết nối camera index {index}...")
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
            logger.info(f"Kết nối thành công Camera {index}")
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
        logger.info(f"Đã ngắt kết nối camera. Lý do: {message}")

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

    def capture_photo(self):
        if not self.is_camera_connected:
            logger.warning("Shot blocked: Camera not connected.")
            return

        frame_for_analysis = self.clean_zoomed_frame_for_processing
        if frame_for_analysis is None:
            logger.error("Không có frame đã zoom (sạch) để phân tích.")
            return

        shot_center_for_analysis = self.shot_point_on_zoomed_frame

        # SỬA LỖI: KHÔNG dùng _pixmap.toImage() nữa để tránh dính ảnh tâm đỏ.
        # Tạo thẳng mã Timestamp và truyền cho Worker tự xử lý việc lưu ảnh Dataset.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self._last_shot_timestamp = timestamp
        if self.is_session_active:
            self._pending_shots[timestamp] = self.active_session_id

        # Trình tự âm thanh: tiếng bắn -> tiếng nổ -> (khi có kết quả) thông báo
        self.audio_manager.start_sequence(["shot", "explosion"])

        self.request_processing.emit(
            frame_for_analysis, shot_center_for_analysis, timestamp
        )

    @Slot(dict)
    def on_processing_finished(self, result):
        display_target_name = format_target_name(result.get("target_name"))
        score = result.get("score", 0)
        final_image_to_display = result.get("result_frame")

        self._record_shot(result)

        # Thông báo kết quả được xếp hàng phía sau tiếng bắn và tiếng nổ.
        # Bỏ qua âm thanh của kết quả cũ (đã có phát bắn mới hơn) hoặc khi
        # đã rời màn hình luyện tập.
        is_current_shot = (
            self._last_shot_timestamp is not None
            and result.get("image_path") == self._last_shot_timestamp
        )

        if score == 1:
            if is_current_shot:
                self.audio_manager.enqueue_sounds(["hit"])
            display_score_text = "TRÚNG"
        else:
            if is_current_shot:
                self.audio_manager.enqueue_sounds(["miss"])
            display_score_text = "TRƯỢT"

        self.gui.update_results(
            target_name=display_target_name,
            score=display_score_text,
            result_frame=final_image_to_display,
        )

    def shutdown_components(self):
        self._last_shot_timestamp = None
        self._pending_shots.clear()
        self.audio_manager.stop_sequence()
        self.disconnect_camera()
        if self.bt_trigger:
            self.bt_trigger.deactivate()
        self.reset_ui_state()

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
        # =========================================================
        # ĐÃ SỬA: Đổi INTER_LINEAR thành INTER_CUBIC để chống vỡ hạt
        # giúp AI nhận diện nét hơn khi zoom to mục tiêu ngoài thực địa
        # =========================================================
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_CUBIC)

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

    def reset_ui_state(self, *_):
        """Đưa vùng kết quả về trạng thái ban đầu (không ảnh hưởng phiên đang chạy)."""
        self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Kết quả: --")
        self.gui.score_label.setStyleSheet("")
        self.gui.result_image_label.setText("Chưa có ảnh kết quả")
        self.gui.result_image_label.setPixmap(QPixmap())

    # ==============================================
    # PHIÊN BẮN & NGƯỜI BẮN
    # ==============================================

    def _trainee_term(self) -> str:
        return self.config.get("labels", {}).get("trainee", "Chiến sĩ")

    def populate_soldier_selector(self):
        """Nạp danh sách người bắn từ cơ sở dữ liệu (giữ lại người đang chọn)."""
        previous = self.gui.soldier_selector.currentData()
        previous_id = previous.get("id") if isinstance(previous, dict) else None

        self.gui.soldier_selector.blockSignals(True)
        self.gui.soldier_selector.clear()
        soldiers = self.db.get_all_soldiers()

        if soldiers:
            select_index = 0
            for index, soldier in enumerate(soldiers):
                name = soldier.get("name") or "Không tên"
                class_name = soldier.get("class_name")
                text = f"{name}  -  {class_name}" if class_name else name
                self.gui.soldier_selector.addItem(text, userData=soldier)
                if soldier.get("id") == previous_id:
                    select_index = index
            self.gui.soldier_selector.setCurrentIndex(select_index)
        else:
            prompt = self.config.get("labels", {}).get(
                "practice_no_trainees_in_selector", "Chưa có {trainee} nào"
            )
            self.gui.soldier_selector.addItem(
                prompt.format(trainee=self._trainee_term().lower())
            )
        self.gui.soldier_selector.blockSignals(False)

    def toggle_session(self):
        if self.is_session_active:
            self._end_session()
        else:
            self._start_session()

    def _start_session(self):
        if not self.is_camera_connected:
            QMessageBox.warning(
                self,
                "Chưa kết nối Camera",
                "Vui lòng kết nối camera USB và chờ tín hiệu hiển thị "
                "trước khi bắt đầu.",
            )
            return

        soldier = self.gui.soldier_selector.currentData()
        if not isinstance(soldier, dict):
            prompt = self.config.get("labels", {}).get(
                "practice_select_trainee_first",
                "Vui lòng chọn một {trainee} trước khi bắt đầu.",
            )
            QMessageBox.warning(
                self,
                self._trainee_term(),
                prompt.format(trainee=self._trainee_term().lower()),
            )
            return

        session_id = self.db.create_session(soldier["id"])
        if not session_id:
            QMessageBox.critical(
                self, "Lỗi dữ liệu", "Không thể tạo phiên tập mới trong cơ sở dữ liệu."
            )
            return

        self.active_session_id = session_id
        self.is_session_active = True
        self.shot_counter = 0
        self._pending_shots.clear()
        self.reset_ui_state()
        logger.info(
            f"Bắt đầu phiên tập ID {session_id} cho người bắn ID {soldier['id']}"
        )
        self._update_session_ui()

    def _end_session(self):
        if self._pending_shots:
            QMessageBox.information(
                self,
                "Đang xử lý",
                "Phát bắn vừa rồi đang được xử lý.\nVui lòng chờ vài giây rồi kết thúc.",
            )
            return

        shot_count = self.db.get_shot_count_for_session(self.active_session_id)

        if shot_count == 0:
            box = QMessageBox(self)
            box.setWindowTitle("Xác nhận Kết thúc")
            box.setText("Bạn chưa thực hiện phát bắn nào.")
            box.setInformativeText("Bạn có muốn kết thúc và xóa luôn phiên tập này?")
            box.setIcon(QMessageBox.Question)
            delete_button = box.addButton(
                "Kết thúc và Xóa", QMessageBox.DestructiveRole
            )
            box.addButton("Hủy", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() != delete_button:
                return
            self.db.delete_session(self.active_session_id)
            logger.info(f"Đã xóa phiên trống ID {self.active_session_id}")
            self._finalize_session()
            return

        soldier = self.gui.soldier_selector.currentData()
        soldier_id = soldier["id"] if isinstance(soldier, dict) else None
        default_name = f"Phiên tập #{self.active_session_id}"

        while True:
            name, ok = QInputDialog.getText(
                self,
                "Đặt tên Phiên tập",
                "Nhập tên để lưu lại phiên tập này:",
                QLineEdit.Normal,
                default_name,
            )
            if not ok:
                return  # Hủy: tiếp tục phiên
            final_name = name.strip() or default_name
            if self.db.session_name_exists(
                final_name,
                soldier_id=soldier_id,
                exclude_session_id=self.active_session_id,
            ):
                QMessageBox.warning(
                    self,
                    "Tên bị trùng",
                    f"{self._trainee_term()} này đã có phiên tập tên '{final_name}'."
                    "\nVui lòng chọn một tên khác.",
                )
                default_name = final_name
                continue
            self.db.update_session_name(self.active_session_id, final_name)
            self._finalize_session()
            return

    def _finalize_session(self):
        self.db.end_session(self.active_session_id)
        logger.info(f"Đã kết thúc phiên tập ID {self.active_session_id}")
        self.is_session_active = False
        self.active_session_id = None
        self.shot_counter = 0
        self._pending_shots.clear()
        self._update_session_ui()

    def _update_session_ui(self):
        """Đồng bộ nút/nhãn với trạng thái phiên (đang bắn hoặc chưa bắt đầu)."""
        active = self.is_session_active
        button = self.gui.session_button
        button.setText("KẾT THÚC" if active else "BẮT ĐẦU")
        button.setObjectName("danger" if active else "")
        button.style().unpolish(button)
        button.style().polish(button)

        self.gui.back_button.setEnabled(not active)
        self.gui.soldier_selector.setEnabled(not active)
        if active:
            self.gui.session_status_label.setText(
                f"Đang ghi phiên - đã lưu {self.shot_counter} phát"
            )
        else:
            self.gui.session_status_label.setText(
                "Chưa bắt đầu phiên - kết quả không được lưu"
            )

    def _record_shot(self, result: dict):
        """Lưu kết quả của một phát bắn vào phiên (nếu phát này thuộc một phiên)."""
        session_id = self._pending_shots.pop(result.get("image_path"), None)
        if session_id is None:
            return
        if result.get("target_detected_raw") == "ERROR":
            logger.warning("Bỏ qua phát bắn bị lỗi model AI, không lưu vào phiên.")
            return

        self.shot_counter += 1
        image_path = save_shot_image(
            session_id, self.shot_counter, result.get("result_frame")
        )
        self.db.add_shot(
            session_id=session_id,
            shot_number=self.shot_counter,
            target_detected=result.get("target_detected_raw"),
            score=1 if result.get("score") == 1 else 0,
            coords=result.get("coords"),
            image_path=image_path,
        )
        self._update_session_ui()

    def abort_session_on_exit(self):
        """Gọi khi đóng ứng dụng: xóa phiên trống, giữ phiên đã có phát bắn."""
        if self.is_session_active and self.active_session_id:
            if self.db.get_shot_count_for_session(self.active_session_id) == 0:
                self.db.delete_session(self.active_session_id)
        self.is_session_active = False
        self.active_session_id = None
