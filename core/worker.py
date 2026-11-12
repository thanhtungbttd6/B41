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

        self.confidence_threshold = self.config.get('yolo_confidence_threshold', 0.40) # Mức 0.40 như đã fix
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
    def process_image(self, photo_frame, calibrated_center, timestamp):
        if not self.detector or not self.detector.model:
            logger.error("Detector chưa được khởi tạo. Hủy bỏ xử lý ảnh.")
            error_package = {
                'time_str': datetime.now().strftime('%H:%M:%S'),
                'target_name': "Lỗi Model AI",
                'score': 0, 'result_frame': photo_frame, 'coords': None,
                'image_path': timestamp, 'target_detected_raw': "ERROR"
            }
            self.finished.emit(error_package)
            return
            
        # ========================================================
        # 1. TẠO BẢN SAO ẢNH SẠCH (CHƯA VẼ GÌ) 
        # ========================================================
        clean_frame = photo_frame.copy()
        img_h, img_w = clean_frame.shape[:2]

        # KHỞI TẠO CẤU TRÚC THƯ MỤC DATASET AUTO VÀ THƯ MỤC DEBUG
        dataset_dir = os.path.join(APP_DATA_DIR, "auto_dataset")
        hits_img_dir = os.path.join(dataset_dir, "hits", "images")
        hits_lbl_dir = os.path.join(dataset_dir, "hits", "labels")
        misses_dir = os.path.join(dataset_dir, "misses")
        
        # Thư mục chứa ảnh thực tế truyền vào AI để kiểm tra (Debug)
        debug_ai_dir = os.path.join(APP_DATA_DIR, "debug_ai_frames") 
        
        os.makedirs(hits_img_dir, exist_ok=True)
        os.makedirs(hits_lbl_dir, exist_ok=True)
        os.makedirs(misses_dir, exist_ok=True)
        os.makedirs(debug_ai_dir, exist_ok=True)

        # LƯU ẢNH DEBUG KIỂM CHỨNG TRƯỚC KHI AI PHÂN TÍCH
        debug_img_path = os.path.join(debug_ai_dir, f"{timestamp}_input.jpg")
        cv2.imwrite(debug_img_path, clean_frame)
        logger.info(f"Đã lưu ảnh đầu vào AI tại: {debug_img_path}")

        # AI BẮT ĐẦU NHẬN DIỆN
        detections = self.detector.detect(image=photo_frame, conf=self.confidence_threshold)

        logger.info("\n" + "="*50)
        logger.info("📸 BẮT ĐẦU PHÂN TÍCH ẢNH BẮN")
        
        if len(detections) == 0:
            logger.warning("❌ [YOLO] KHÔNG nhận diện được bia nào (Do mờ, hoặc chưa đạt ngưỡng tin cậy).")
        else:
            for i, det in enumerate(detections):
                class_name = det.get('class_name', 'Unknown')
                conf = det.get('conf', 0) * 100
                box = det.get('box', [0,0,0,0])
                
                logger.info(f"🎯 [YOLO] Phát hiện mục tiêu {i+1}: '{class_name}' | Độ tin cậy: {conf:.2f}%")
                
                if calibrated_center:
                    cx, cy = calibrated_center
                    if int(box[0]) <= cx <= int(box[2]) and int(box[1]) <= cy <= int(box[3]):
                        logger.info("✅ Điểm ngắm NẰM TRONG khung nhận diện của bia (Đợi OpenCV xét màu).")
                    else:
                        logger.warning("⚠️ Điểm ngắm NẰM NGOÀI khung nhận diện của bia này.")
        logger.info("="*50 + "\n")

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
                 # 1. Vẽ lên photo_frame CHỈ để gửi trả về màn hình hiển thị
                 cv2.circle(photo_frame, (int(aim_point[0]), int(aim_point[1])), 5, (0, 255, 0), -1)
                 result_data = {'target': detected_name, 'score': 1, 'image': photo_frame, 'coords': aim_point}
                 
                 # ========================================================
                 # 2. XUẤT DATASET HITS CHO YOLO (Lấy ẢNH SẠCH + TÍNH TOÁN BOX)
                 # ========================================================
                 img_path = os.path.join(hits_img_dir, f"{timestamp}.jpg")
                 lbl_path = os.path.join(hits_lbl_dir, f"{timestamp}.txt")
                 
                 # Lưu ảnh không tì vết
                 cv2.imwrite(img_path, clean_frame)
                 
                 # Chuyển đổi tọa độ Box sang tỷ lệ chuẩn YOLO (x_center, y_center, width, height)
                 x1, y1, x2, y2 = target_box
                 x_center = ((x1 + x2) / 2.0) / img_w
                 y_center = ((y1 + y2) / 2.0) / img_h
                 w = (x2 - x1) / img_w
                 h = (y2 - y1) / img_h
                 
                 # Tìm class_id (Index của class trong YOLO model)
                 class_id = 0
                 if hasattr(self.detector.model, 'names'):
                     for k, v in self.detector.model.names.items():
                         if v == detected_name:
                             class_id = k
                             break
                             
                 # Ghi tọa độ ra file txt
                 with open(lbl_path, "w") as f:
                     f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")
                     
                 logger.info(f"✅ Đã trích xuất Dataset TRÚNG (Ảnh + Label) tại: auto_dataset/hits")
            else:
                logger.warning(f"⚠️ Kết luận cuối: Bắn vào bia '{detected_name}' nhưng trượt phần đen hồng tâm.")
                cv2.drawMarker(photo_frame, (int(aim_point[0]), int(aim_point[1])), (0, 0, 255), markerType=cv2.MARKER_TILTED_CROSS, markerSize=20, thickness=3)
                result_data = {'target': detected_name, 'score': 0, 'image': photo_frame, 'coords': aim_point}
                
                # Lưu ảnh sạch TRƯỢT
                miss_img_path = os.path.join(misses_dir, f"{timestamp}.jpg")
                cv2.imwrite(miss_img_path, clean_frame)
                logger.info(f"Đã lưu Dataset TRƯỢT tại: auto_dataset/misses")
        else:
            aim_point = hit_info.get('shot_point', (photo_frame.shape[1]//2, photo_frame.shape[0]//2))
            cv2.drawMarker(photo_frame, (int(aim_point[0]), int(aim_point[1])), (0, 0, 255), markerType=cv2.MARKER_TILTED_CROSS, markerSize=20, thickness=3)
            
            result_data = {'target': "Ngoài bia", 'score': 0, 'image': photo_frame, 'coords': aim_point}
            target_detected_raw = "Trượt" 
            
            # Lưu ảnh sạch TRƯỢT
            miss_img_path = os.path.join(misses_dir, f"{timestamp}.jpg")
            cv2.imwrite(miss_img_path, clean_frame)
            logger.info(f"Đã lưu Dataset TRƯỢT tại: auto_dataset/misses")

        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target', hit_status),
            'score': result_data.get('score', 0),
            'result_frame': result_data.get('image', photo_frame), # Vẫn trả về ảnh đã vẽ để UI hiển thị
            'coords': result_data.get('coords'),
            'image_path': timestamp, 
            'target_detected_raw': target_detected_raw
        }
        
        self.finished.emit(final_package)