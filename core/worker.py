# core/worker.py
import logging
import cv2
import numpy as np
import os
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot

from module.detection_module import ObjectDetector
from utils.processing import check_object_center, calculate_hit_result_by_color
from utils.resource_path import resource_path
from config import APP_DATA_DIR

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    finished = Signal(dict)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.detector = None
        
        self._initialize_detector()

        self.confidence_threshold = self.config.get('yolo_confidence_threshold', 0.75)
        logger.info(f"Worker initialized with confidence threshold: {self.confidence_threshold}")

        if self.detector:
            logger.info("Worker: Thực hiện warm-up cho mô hình YOLO...")
            try:
                dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
                self.detector.detect(dummy_image)
                logger.info("Worker: Warm-up hoàn tất.")
            except Exception as e:
                logger.error(f"Worker: Lỗi trong quá trình warm-up: {e}")

    def _initialize_detector(self):
        model_filename = self.config.get("yolo_model_name")
        if not model_filename:
            logger.critical("Config không chứa 'yolo_model_name'. Không thể khởi tạo AI.")
            return

        model_path = os.path.join(APP_DATA_DIR, model_filename)

        if not os.path.exists(model_path):
            logger.critical(f"Không tìm thấy file model tại đường dẫn '{model_path}'. Worker không thể hoạt động.")
            return

        logger.info(f"Đang khởi tạo detector với model tại: {model_path}")
        self.detector = ObjectDetector(model_path=model_path)

    @Slot(np.ndarray, object, str)
    def process_image(self, photo_frame, calibrated_center, image_path):
        if not self.detector or not self.detector.model:
            logger.error("Detector chưa được khởi tạo. Hủy bỏ xử lý ảnh.")
            error_package = {
                'time_str': datetime.now().strftime('%H:%M:%S'),
                'target_name': "Lỗi Model AI",
                'score': 0, 'result_frame': photo_frame, 'coords': None,
                'image_path': image_path, 'target_detected_raw': "ERROR"
            }
            self.finished.emit(error_package)
            return
            
        detections = self.detector.detect(image=photo_frame, conf=self.confidence_threshold)

        # ============ LOG THEO DÕI QUÁ TRÌNH NHẬN DIỆN YOLO ============
        logger.info("\n" + "="*50)
        logger.info("📸 BẮT ĐẦU PHÂN TÍCH ẢNH BẮN")
        
        if len(detections) == 0:
            logger.warning("❌ [YOLO] KHÔNG nhận diện được bia nào (Do mờ, hoặc chưa đạt ngưỡng tin cậy).")
        else:
            for i, det in enumerate(detections):
                # Det thường chứa: class_name, confidence, [x1, y1, x2, y2]
                class_name = det.get('name', 'Unknown')
                conf = det.get('confidence', 0) * 100
                box = det.get('box', [0,0,0,0])
                
                logger.info(f"🎯 [YOLO] Phát hiện mục tiêu {i+1}: '{class_name}' | Độ tin cậy: {conf:.2f}%")
                logger.info(f"   -> Tọa độ Box: X:{int(box[0])}, Y:{int(box[1])} đến X:{int(box[2])}, Y:{int(box[3])}")
                
                if calibrated_center:
                    cx, cy = calibrated_center
                    logger.info(f"📍 Điểm ngắm (Hiệu chỉnh tâm): X:{cx}, Y:{cy}")
                    
                    if int(box[0]) <= cx <= int(box[2]) and int(box[1]) <= cy <= int(box[3]):
                        logger.info("✅ Điểm ngắm NẰM TRONG khung nhận diện của bia (Đợi OpenCV xét màu).")
                    else:
                        logger.warning("⚠️ Điểm ngắm NẰM NGOÀI khung nhận diện của bia này.")
                else:
                    logger.warning("⚠️ Chưa có tọa độ hiệu chỉnh tâm bóp cò (calibrated_center is None).")
        logger.info("="*50 + "\n")
        # ===============================================================

        status, hit_info = check_object_center(detections, photo_frame, calibrated_center)

        result_data = {}
        target_detected_raw = None
        hit_status = "Trượt"
        
        if status == "BIA_NHAN_DIEN":
            detected_name = hit_info.get('name')
            target_detected_raw = detected_name
            
            aim_point = hit_info['shot_point_absolute']
            target_box = hit_info['box']
            
            # Tính Trúng/Trượt bằng hàm lọc màu đen
            hit_status = calculate_hit_result_by_color(photo_frame, target_box, aim_point)
            
            if hit_status == "Trúng":
                 # Vẽ CHẤM XANH LÁ khi Trúng
                 cv2.circle(photo_frame, (int(aim_point[0]), int(aim_point[1])), 5, (0, 255, 0), -1)
                 result_data = {'target': detected_name, 'score': 1, 'image': photo_frame, 'coords': aim_point}
                 logger.info(f"✅ Kết luận cuối: Bắn TRÚNG hồng tâm '{detected_name}'!")
            else:
                logger.warning(f"⚠️ Kết luận cuối: Bắn vào bia '{detected_name}' nhưng trượt phần đen hồng tâm.")
                # Vẽ DẤU X ĐỎ khi Trượt (MARKER_TILTED_CROSS là hình chữ X)
                cv2.drawMarker(photo_frame, (int(aim_point[0]), int(aim_point[1])), (0, 0, 255), markerType=cv2.MARKER_TILTED_CROSS, markerSize=20, thickness=3)
                result_data = {'target': detected_name, 'score': 0, 'image': photo_frame, 'coords': aim_point}
        else:
            # Trường hợp bắn hoàn toàn ra ngoài (AI không nhận diện được bia)
            aim_point = hit_info.get('shot_point', (photo_frame.shape[1]//2, photo_frame.shape[0]//2)) # Lấy điểm ngắm hoặc tâm màn hình
            cv2.drawMarker(photo_frame, (int(aim_point[0]), int(aim_point[1])), (0, 0, 255), markerType=cv2.MARKER_TILTED_CROSS, markerSize=20, thickness=3)
            
            result_data = {'target': "Ngoài bia", 'score': 0, 'image': photo_frame, 'coords': aim_point}
            target_detected_raw = "Trượt" 
            logger.warning("❌ Kết luận cuối: Bắn HOÀN TOÀN TRƯỢT ra ngoài (Không trúng bia nào).")

        if result_data.get('score') is not None and result_data.get('score') > 0:
            final_image_to_save = result_data.get('image')
            if final_image_to_save is not None:
                try:
                    cv2.imwrite(image_path, final_image_to_save)
                    logger.info(f"Worker: Đã ghi đè ảnh kết quả tại {image_path}")
                except Exception as e:
                    logger.error(f"Worker: Lỗi khi ghi đè ảnh kết quả: {e}")

        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target', hit_status),
            'score': result_data.get('score', 0),
            'result_frame': result_data.get('image', photo_frame),
            'coords': result_data.get('coords'),
            'image_path': image_path,
            'target_detected_raw': target_detected_raw
        }
        
        self.finished.emit(final_package)
        logger.info(f"Worker: Đã gửi kết quả hiển thị lên GUI.")