import os
from typing import List, Optional, Tuple

import cv2
import numpy as np


def friendly_object_name(filename: str) -> str:
    base = filename.split("/")[-1]
    name, _ = base.split(".") if "." in base else (base, "")
    return name.replace("_", " ")


def check_object_center(detections, image, calibrated_center):
    if calibrated_center:
        center_x, center_y = calibrated_center
    else:
        h, w, _ = image.shape
        center_x, center_y = w // 2, h // 2

    highest_conf_hit = None
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        if x1 <= center_x <= x2 and y1 <= center_y <= y2:
            if highest_conf_hit is None or det["conf"] > highest_conf_hit["conf"]:
                highest_conf_hit = det

    if highest_conf_hit:
        x1, y1, x2, y2 = highest_conf_hit["box"]

        hit_info = {
            "name": highest_conf_hit["class_name"],
            "crop": image[y1:y2, x1:x2].copy(),
            "shot_point_relative": (center_x - x1, center_y - y1),
            "shot_point_absolute": (
                center_x,
                center_y,
            ),  # Đảm bảo trả về tọa độ tuyệt đối
            "conf": highest_conf_hit["conf"],
            "box": (x1, y1, x2, y2),  # Cần truyền box để tách màu
        }
        print(f"✅ BIA NHẬN DIỆN: {hit_info['name']} (Conf: {hit_info['conf']:.2f})")
        return "BIA_NHAN_DIEN", hit_info

    print("❌ TRƯỢT | Tâm ngắm không nằm trong bất kỳ mục tiêu nào.")
    return "TRƯỢT", {"shot_point": (center_x, center_y)}


def calculate_hit_result_by_color(
    frame: np.ndarray,
    target_box: Tuple[int, int, int, int],
    aim_point: Tuple[float, float],
) -> str:
    """
    Xác định kết quả Trúng/Trượt dựa trên nhận diện vùng màu đen thực tế của bia.
    """
    x_min, y_min, x_max, y_max = [int(v) for v in target_box]
    hit_x, hit_y = int(aim_point[0]), int(aim_point[1])

    if not (x_min <= hit_x <= x_max and y_min <= hit_y <= y_max):
        return "Trượt"

    roi = frame[y_min:y_max, x_min:x_max]
    if roi.size == 0:
        return "Trượt"

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Tách ngưỡng nhị phân để lọc màu đen (Đen thành Trắng 255, Trắng thành Đen 0)
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "Trượt"

    largest_contour = max(contours, key=cv2.contourArea)
    bx, by, bw, bh = cv2.boundingRect(largest_contour)

    black_x_min = x_min + bx
    black_y_min = y_min + by
    black_x_max = black_x_min + bw
    black_y_max = black_y_min + bh

    if (black_x_min <= hit_x <= black_x_max) and (black_y_min <= hit_y <= black_y_max):
        return "Trúng"

    return "Trượt"


def warp_crop_to_original(
    original_img: np.ndarray,
    obj_crop: np.ndarray,
    shot_point: Optional[Tuple[float, float]] = None,
    min_inliers: int = 5,
    ratio_thresh: float = 0.75,
    ransac_thresh: float = 4.0,
    max_reproj: float = 5.0,
) -> Tuple[Optional[np.ndarray], Optional[Tuple[float, float]]]:
    if original_img is None or obj_crop is None:
        print("[warp_crop_to_original] ERROR: Ảnh đầu vào bị None")
        return None, None

    orb = cv2.ORB_create(
        nfeatures=1500, scaleFactor=1.2, edgeThreshold=15, patchSize=31
    )
    kp1, des1 = orb.detectAndCompute(original_img, None)
    kp2, des2 = orb.detectAndCompute(obj_crop, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        print("[warp_crop_to_original] Không đủ đặc trưng để match.")
        return None, None

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches12 = bf.knnMatch(des1, des2, k=2)
    matches21 = bf.knnMatch(des2, des1, k=2)

    # Lọc các điểm match tốt bằng Lowe's ratio test
    good12 = [m for m, n in matches12 if m.distance < ratio_thresh * n.distance]
    good21 = [m for m, n in matches21 if m.distance < ratio_thresh * n.distance]

    # Lọc các điểm match tương hỗ (mutual matches)
    mutual = []
    reverse_map = {(m.trainIdx, m.queryIdx) for m in good21}
    for m in good12:
        if (m.queryIdx, m.trainIdx) in reverse_map:
            mutual.append(m)

    if len(mutual) < min_inliers:
        print(f"[warp_crop_to_original] Mutual matches quá ít: {len(mutual)}")
        return None, None

    src_pts = np.float32([kp1[m.queryIdx].pt for m in mutual]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in mutual]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, ransac_thresh)
    if H is None or abs(np.linalg.det(H)) < 1e-6:
        print("[warp_crop_to_original] Homography không hợp lệ hoặc suy biến.")
        return None, None

    transformed_point = None
    if shot_point is not None:
        try:
            px, py = float(shot_point[0]), float(shot_point[1])
            src_pt = np.array([[[px, py]]], dtype=np.float32)
            warped_pt = cv2.perspectiveTransform(src_pt, H)[0][0]
            transformed_point = (float(warped_pt[0]), float(warped_pt[1]))
            print(
                f"[warp_crop_to_original] Tọa độ vết đạn chuyển sang ảnh gốc: {transformed_point}"
            )
        except Exception as e:
            print(f"[warp_crop_to_original] Lỗi chuyển tọa độ điểm: {e}")

    print("[warp_crop_to_original] Warp ảnh thành công")
    warped = cv2.warpPerspective(
        obj_crop,
        H,
        (original_img.shape[1], original_img.shape[0]),
        flags=cv2.INTER_LINEAR,
    )
    return warped, transformed_point
