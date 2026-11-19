# core/worker.py
import logging
import os
import shutil
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from config import APP_DATA_DIR
from module.detection_module import ObjectDetector
from utils.processing import check_object_center

logger = logging.getLogger(__name__)

# Số bản model cũ được giữ lại để có thể quay về khi model mới chạy không tốt
MAX_MODEL_BACKUPS = 3

# Kích thước ảnh nhận diện mặc định và giới hạn cho phép của khóa "yolo_imgsz"
DEFAULT_IMGSZ = 320
MIN_IMGSZ, MAX_IMGSZ = 160, 1280


class ProcessingWorker(QObject):
    finished = Signal(dict)
    # (thành công?, nội dung thông báo) - gửi về giao diện sau khi cập nhật model
    model_update_finished = Signal(bool, str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.detector = None
        self.imgsz = self._read_imgsz()

        self._initialize_detector()

        self.confidence_threshold = self.config.get("yolo_confidence_threshold", 0.40)
        logger.info(
            f"Worker initialized with confidence threshold: {self.confidence_threshold}"
        )

        # Công tắc lưu ảnh training/debug đọc từ config.json (không hiện trên giao diện)
        self.save_training_images = bool(self.config.get("save_training_images", True))
        self.save_debug_frames = bool(self.config.get("save_debug_frames", False))
        logger.info(
            f"Kích thước nhận diện (imgsz): {self.imgsz} | "
            f"Lưu ảnh training: {'BẬT' if self.save_training_images else 'TẮT'} | "
            f"Lưu ảnh debug: {'BẬT' if self.save_debug_frames else 'TẮT'}"
        )

        if self.detector:
            logger.info("Worker: Thực hiện warm-up cho mô hình YOLO...")
            try:
                dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
                self.detector.detect(dummy_image)
                logger.info("Worker: Warm-up hoàn tất.")
            except Exception as e:
                logger.error(f"Worker: Lỗi trong quá trình warm-up: {e}")

    # ------------------------------------------------------------------
    # MODEL
    # ------------------------------------------------------------------
    def _model_dest_path(self):
        model_filename = self.config.get("yolo_model_name")
        if not model_filename:
            return None
        return os.path.join(APP_DATA_DIR, model_filename)

    def _read_imgsz(self) -> int:
        """Đọc "yolo_imgsz" từ config; giá trị sai thì dùng mặc định, lệch thì làm tròn về bội số của 32."""
        raw = self.config.get("yolo_imgsz", DEFAULT_IMGSZ)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            logger.warning(f"yolo_imgsz '{raw}' không hợp lệ, dùng mặc định {DEFAULT_IMGSZ}.")
            return DEFAULT_IMGSZ
        value = max(MIN_IMGSZ, min(MAX_IMGSZ, value))
        rounded = max(MIN_IMGSZ, round(value / 32) * 32)
        if rounded != int(raw):
            logger.warning(f"yolo_imgsz {raw} được điều chỉnh thành {rounded} (bội số của 32).")
        return rounded

    def _initialize_detector(self):
        model_path = self._model_dest_path()
        if not model_path:
            logger.critical(
                "Config không chứa 'yolo_model_name'. Không thể khởi tạo AI."
            )
            return

        if not os.path.exists(model_path):
            logger.critical(
                f"Không tìm thấy file model tại đường dẫn '{model_path}'. Worker không thể hoạt động."
            )
            return

        logger.info(f"Đang khởi tạo detector với model tại: {model_path}")
        self.detector = ObjectDetector(model_path=model_path, imgsz=self.imgsz)

    @Slot(str)
    def reload_model(self, new_model_path: str):
        """
        Cập nhật model AI từ một file .pt do người dùng chọn.
        Chạy trên luồng của worker nên không xung đột với việc đang nhận diện ảnh.
        Chỉ thay model khi file mới nạp và chạy thử thành công; nếu lỗi thì
        giữ nguyên model đang dùng.
        """
        try:
            dest_path = self._model_dest_path()
            if not dest_path:
                self.model_update_finished.emit(
                    False, "Cấu hình thiếu 'yolo_model_name' nên không thể cập nhật."
                )
                return
            if not new_model_path or not os.path.isfile(new_model_path):
                self.model_update_finished.emit(False, "Không tìm thấy file đã chọn.")
                return

            # 1. Nạp và chạy thử model mới TRƯỚC khi đụng vào model đang dùng
            candidate = ObjectDetector(model_path=new_model_path, imgsz=self.imgsz)
            if candidate.model is None:
                self.model_update_finished.emit(
                    False,
                    "File không phải model YOLO hợp lệ hoặc bị hỏng.\n"
                    "Model hiện tại vẫn được giữ nguyên.",
                )
                return

            names = getattr(candidate.model, "names", None) or {}
            if not names:
                self.model_update_finished.emit(
                    False,
                    "Model không có danh sách lớp (class) để nhận diện.\n"
                    "Model hiện tại vẫn được giữ nguyên.",
                )
                return

            candidate.detect(np.zeros((480, 640, 3), dtype=np.uint8))

            # 2. Sao lưu model cũ rồi thay bằng model mới (ghi file tạm rồi đổi tên)
            same_file = os.path.exists(dest_path) and os.path.samefile(
                new_model_path, dest_path
            )
            if not same_file:
                if os.path.exists(dest_path):
                    self._backup_current_model(dest_path)
                tmp_path = dest_path + ".new"
                shutil.copyfile(new_model_path, tmp_path)
                os.replace(tmp_path, dest_path)

            # 3. Chuyển sang model mới
            self.detector = candidate
            class_list = ", ".join(str(v) for v in names.values())
            logger.info(f"Đã cập nhật model AI từ '{new_model_path}'. Lớp: {class_list}")
            self.model_update_finished.emit(
                True, f"Đã cập nhật model AI thành công.\nCác lớp nhận diện: {class_list}"
            )
        except Exception as e:
            logger.error(f"Lỗi cập nhật model: {e}", exc_info=True)
            self.model_update_finished.emit(
                False, f"Không thể cập nhật model: {e}\nModel hiện tại vẫn được giữ nguyên."
            )

    def _backup_current_model(self, current_path: str):
        """Lưu bản model đang dùng vào models_backup/ và chỉ giữ vài bản gần nhất."""
        try:
            backup_dir = os.path.join(APP_DATA_DIR, "models_backup")
            os.makedirs(backup_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base, ext = os.path.splitext(os.path.basename(current_path))
            shutil.copyfile(current_path, os.path.join(backup_dir, f"{base}_{stamp}{ext}"))

            backups = sorted(
                (f for f in os.listdir(backup_dir) if f.endswith(ext)),
                key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)),
                reverse=True,
            )
            for old in backups[MAX_MODEL_BACKUPS:]:
                try:
                    os.remove(os.path.join(backup_dir, old))
                except OSError:
                    pass
        except Exception as e:
            logger.warning(f"Không thể sao lưu model cũ: {e}")

    # ------------------------------------------------------------------
    # LƯU ẢNH TRAINING / DEBUG
    # ------------------------------------------------------------------
    def _save_debug_input(self, clean_frame, timestamp):
        if not self.save_debug_frames:
            return
        try:
            debug_dir = os.path.join(APP_DATA_DIR, "debug_ai_frames")
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(os.path.join(debug_dir, f"{timestamp}_input.jpg"), clean_frame)
        except Exception as e:
            logger.warning(f"Không lưu được ảnh debug: {e}")

    def _save_training_hit(self, clean_frame, timestamp, target_box, detected_name):
        """Lưu ảnh sạch + nhãn YOLO của phát TRÚNG."""
        if not self.save_training_images:
            return
        try:
            img_h, img_w = clean_frame.shape[:2]
            hits_img_dir = os.path.join(APP_DATA_DIR, "auto_dataset", "hits", "images")
            hits_lbl_dir = os.path.join(APP_DATA_DIR, "auto_dataset", "hits", "labels")
            os.makedirs(hits_img_dir, exist_ok=True)
            os.makedirs(hits_lbl_dir, exist_ok=True)

            cv2.imwrite(os.path.join(hits_img_dir, f"{timestamp}.jpg"), clean_frame)

            # Tọa độ box theo tỷ lệ chuẩn YOLO (x_center, y_center, width, height)
            x1, y1, x2, y2 = target_box
            x_center = ((x1 + x2) / 2.0) / img_w
            y_center = ((y1 + y2) / 2.0) / img_h
            w = (x2 - x1) / img_w
            h = (y2 - y1) / img_h

            class_id = 0
            if self.detector and hasattr(self.detector.model, "names"):
                for k, v in self.detector.model.names.items():
                    if v == detected_name:
                        class_id = k
                        break

            with open(
                os.path.join(hits_lbl_dir, f"{timestamp}.txt"), "w", encoding="utf-8"
            ) as f:
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")

            logger.info("✅ Đã trích xuất Dataset TRÚNG (Ảnh + Label) tại: auto_dataset/hits")
        except Exception as e:
            logger.warning(f"Không lưu được dataset trúng: {e}")

    def _save_training_miss(self, clean_frame, timestamp):
        """Lưu ảnh sạch của phát TRƯỢT (ngoài bia)."""
        if not self.save_training_images:
            return
        try:
            misses_dir = os.path.join(APP_DATA_DIR, "auto_dataset", "misses")
            os.makedirs(misses_dir, exist_ok=True)
            cv2.imwrite(os.path.join(misses_dir, f"{timestamp}.jpg"), clean_frame)
            logger.info("Đã lưu Dataset TRƯỢT tại: auto_dataset/misses")
        except Exception as e:
            logger.warning(f"Không lưu được dataset trượt: {e}")

    # ------------------------------------------------------------------
    # NHẬN DIỆN
    # ------------------------------------------------------------------
    @Slot(np.ndarray, object, str)
    def process_image(self, photo_frame, calibrated_center, timestamp):
        if not self.detector or not self.detector.model:
            logger.error("Detector chưa được khởi tạo. Hủy bỏ xử lý ảnh.")
            error_package = {
                "time_str": datetime.now().strftime("%H:%M:%S"),
                "target_name": "Lỗi Model AI",
                "score": 0,
                "result_frame": photo_frame,
                "coords": None,
                "image_path": timestamp,
                "target_detected_raw": "ERROR",
            }
            self.finished.emit(error_package)
            return

        # Bản sao ảnh sạch (chưa vẽ gì) dùng để lưu dataset
        clean_frame = photo_frame.copy()

        self._save_debug_input(clean_frame, timestamp)

        # AI nhận diện
        detections = self.detector.detect(
            image=photo_frame, conf=self.confidence_threshold
        )

        logger.info("\n" + "=" * 50)
        logger.info("📸 BẮT ĐẦU PHÂN TÍCH ẢNH BẮN")

        if len(detections) == 0:
            logger.warning(
                "❌ [YOLO] KHÔNG nhận diện được bia nào (Do mờ, hoặc chưa đạt ngưỡng tin cậy)."
            )
        else:
            for i, det in enumerate(detections):
                class_name = det.get("class_name", "Unknown")
                conf = det.get("conf", 0) * 100
                box = det.get("box", [0, 0, 0, 0])

                logger.info(
                    f"🎯 [YOLO] Phát hiện mục tiêu {i+1}: '{class_name}' | Độ tin cậy: {conf:.2f}%"
                )

                if calibrated_center:
                    cx, cy = calibrated_center
                    if int(box[0]) <= cx <= int(box[2]) and int(box[1]) <= cy <= int(
                        box[3]
                    ):
                        logger.info("✅ Điểm ngắm NẰM TRONG khung nhận diện của bia.")
                    else:
                        logger.warning(
                            "⚠️ Điểm ngắm NẰM NGOÀI khung nhận diện của bia này."
                        )
        logger.info("=" * 50 + "\n")

        status, hit_info = check_object_center(
            detections, photo_frame, calibrated_center
        )

        result_data = {}
        target_detected_raw = None

        if status == "BIA_NHAN_DIEN":
            # Điểm ngắm nằm trong khung của bia được nhận diện => TRÚNG
            detected_name = hit_info.get("name")
            target_detected_raw = detected_name

            aim_point = hit_info["shot_point_absolute"]
            target_box = hit_info["box"]

            # Chỉ vẽ lên photo_frame để hiển thị; ảnh dataset dùng clean_frame
            cv2.circle(
                photo_frame,
                (int(aim_point[0]), int(aim_point[1])),
                5,
                (0, 255, 0),
                -1,
            )
            result_data = {
                "target": detected_name,
                "score": 1,
                "image": photo_frame,
                "coords": aim_point,
            }

            self._save_training_hit(clean_frame, timestamp, target_box, detected_name)
        else:
            aim_point = hit_info.get(
                "shot_point", (photo_frame.shape[1] // 2, photo_frame.shape[0] // 2)
            )
            cv2.drawMarker(
                photo_frame,
                (int(aim_point[0]), int(aim_point[1])),
                (0, 0, 255),
                markerType=cv2.MARKER_TILTED_CROSS,
                markerSize=20,
                thickness=3,
            )

            result_data = {
                "target": "Ngoài bia",
                "score": 0,
                "image": photo_frame,
                "coords": aim_point,
            }
            target_detected_raw = "Trượt"

            self._save_training_miss(clean_frame, timestamp)

        final_package = {
            "time_str": datetime.now().strftime("%H:%M:%S"),
            "target_name": result_data.get("target", "Trượt"),
            "score": result_data.get("score", 0),
            "result_frame": result_data.get("image", photo_frame),
            "coords": result_data.get("coords"),
            "image_path": timestamp,
            "target_detected_raw": target_detected_raw,
        }

        self.finished.emit(final_package)
