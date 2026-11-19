# file: core/database.py

import logging
import os
import shutil
import sqlite3
from datetime import datetime

from config import APP_DATA_DIR

logger = logging.getLogger(__name__)

# Thư mục lưu ảnh kết quả của từng phát bắn: captures/<id phiên>/shot_<số phát>.jpg
CAPTURES_DIR = os.path.join(APP_DATA_DIR, "captures")


def _rows_to_dicts(cursor) -> list:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _is_inside_captures(path: str) -> bool:
    """Chỉ cho phép xóa file nằm trong thư mục captures của ứng dụng."""
    try:
        root = os.path.abspath(CAPTURES_DIR)
        target = os.path.abspath(path)
        return os.path.commonpath([root, target]) == root and target != root
    except (ValueError, TypeError):
        return False


def save_shot_image(session_id: int, shot_number: int, image_bgr) -> str | None:
    """Lưu ảnh kết quả của một phát bắn và trả về đường dẫn file (None nếu lỗi)."""
    import cv2

    if image_bgr is None:
        return None
    try:
        session_dir = os.path.join(CAPTURES_DIR, str(session_id))
        os.makedirs(session_dir, exist_ok=True)
        path = os.path.join(session_dir, f"shot_{shot_number}.jpg")
        if not cv2.imwrite(path, image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92]):
            logger.error(f"Không ghi được ảnh phát bắn tại: {path}")
            return None
        return path
    except Exception as e:
        logger.error(f"Lỗi khi lưu ảnh phát bắn: {e}")
        return None


class DatabaseManager:
    def __init__(self, db_name="shooting_range.db"):
        """Khởi tạo và kết nối tới database SQLite trong thư mục dữ liệu ứng dụng."""
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        self.db_path = os.path.join(APP_DATA_DIR, db_name)
        self.conn = None
        self.cursor = None
        try:
            # check_same_thread=False: an toàn vì chỉ dùng trên luồng giao diện
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self._create_tables()
            logger.info(f"Đã kết nối database tại: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kết nối hoặc tạo database: {e}")

    def _create_tables(self):
        """Tạo các bảng nếu chưa tồn tại (giữ nguyên cấu trúc cũ để dùng lại dữ liệu)."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS soldiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                class_name TEXT,
                created_at TEXT NOT NULL
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                soldier_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                exercise_name TEXT,
                notes TEXT,
                FOREIGN KEY (soldier_id) REFERENCES soldiers (id) ON DELETE CASCADE
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS shots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                shot_number INTEGER NOT NULL,
                target_detected TEXT,
                score INTEGER,
                hit_coordinate_x REAL,
                hit_coordinate_y REAL,
                image_path TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            );
        """)
        self.conn.commit()

    # ======================================================================
    # CHIẾN SĨ
    # ======================================================================
    def add_soldier(self, name: str, class_name: str) -> int | None:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO soldiers (name, class_name, created_at) VALUES (?, ?, ?)",
                (name, class_name, timestamp),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thêm chiến sĩ: {e}")
            return None

    def get_all_soldiers(self) -> list:
        try:
            self.cursor.execute(
                "SELECT id, name, class_name FROM soldiers "
                "ORDER BY class_name ASC, name ASC"
            )
            return _rows_to_dicts(self.cursor)
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách chiến sĩ: {e}")
            return []

    def update_soldier(self, soldier_id: int, name: str, class_name: str) -> bool:
        try:
            self.cursor.execute(
                "UPDATE soldiers SET name = ?, class_name = ? WHERE id = ?",
                (name, class_name, soldier_id),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi cập nhật chiến sĩ: {e}")
            return False

    def delete_soldier(self, soldier_id: int) -> bool:
        """Xóa chiến sĩ cùng toàn bộ phiên, phát bắn và ảnh liên quan."""
        try:
            self.cursor.execute(
                "SELECT id FROM sessions WHERE soldier_id = ?", (soldier_id,)
            )
            session_ids = [row[0] for row in self.cursor.fetchall()]
            self.cursor.execute("DELETE FROM soldiers WHERE id = ?", (soldier_id,))
            self.conn.commit()
            for session_id in session_ids:
                self._remove_session_images(session_id)
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa chiến sĩ: {e}")
            return False

    # ======================================================================
    # PHIÊN BẮN
    # ======================================================================
    def create_session(
        self, soldier_id: int, exercise_name: str = "Bài bắn tự do", notes: str = ""
    ) -> int | None:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO sessions (soldier_id, session_date, exercise_name, notes) "
                "VALUES (?, ?, ?, ?)",
                (soldier_id, timestamp, exercise_name, notes),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo phiên bắn: {e}")
            return None

    def end_session(self, session_id: int):
        """Được gọi khi phiên kết thúc (hiện chỉ ghi log)."""
        if session_id:
            logger.info(f"Phiên bắn ID {session_id} đã hoàn tất.")

    def get_session_by_id(self, session_id: int) -> dict | None:
        try:
            self.cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            rows = _rows_to_dicts(self.cursor)
            return rows[0] if rows else None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy phiên bắn ID {session_id}: {e}")
            return None

    def get_sessions_for_soldier(self, soldier_id: int) -> list:
        """Các phiên của một chiến sĩ, mới nhất trước."""
        try:
            self.cursor.execute(
                "SELECT * FROM sessions WHERE soldier_id = ? "
                "ORDER BY session_date DESC, id DESC",
                (soldier_id,),
            )
            return _rows_to_dicts(self.cursor)
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách phiên bắn: {e}")
            return []

    def update_session_name(self, session_id: int, new_name: str) -> bool:
        try:
            self.cursor.execute(
                "UPDATE sessions SET exercise_name = ? WHERE id = ?",
                (new_name, session_id),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi đổi tên phiên {session_id}: {e}")
            return False

    def delete_session(self, session_id: int) -> bool:
        """Xóa phiên cùng các phát bắn và ảnh liên quan."""
        try:
            self.cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            self._remove_session_images(session_id)
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa phiên {session_id}: {e}")
            return False

    def session_name_exists(
        self, name: str, soldier_id: int, exclude_session_id: int | None = None
    ) -> bool:
        """Kiểm tra tên phiên đã tồn tại cho chiến sĩ này chưa."""
        try:
            if exclude_session_id:
                sql = (
                    "SELECT 1 FROM sessions "
                    "WHERE exercise_name = ? AND soldier_id = ? AND id != ?"
                )
                params = (name, soldier_id, exclude_session_id)
            else:
                sql = "SELECT 1 FROM sessions WHERE exercise_name = ? AND soldier_id = ?"
                params = (name, soldier_id)
            self.cursor.execute(sql, params)
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kiểm tra tên phiên: {e}")
            return True  # Mặc định coi là trùng để tránh ghi đè dữ liệu

    # ======================================================================
    # PHÁT BẮN
    # ======================================================================
    def add_shot(
        self,
        session_id: int,
        shot_number: int,
        target_detected: str,
        score: int | None,
        coords: tuple | None,
        image_path: str | None,
    ) -> bool:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            coord_x = float(coords[0]) if coords else None
            coord_y = float(coords[1]) if coords else None
            self.cursor.execute(
                """
                INSERT INTO shots
                (session_id, shot_number, target_detected, score,
                 hit_coordinate_x, hit_coordinate_y, image_path, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    shot_number,
                    target_detected,
                    score,
                    coord_x,
                    coord_y,
                    image_path,
                    timestamp,
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lưu phát bắn: {e}")
            return False

    def get_shot_count_for_session(self, session_id: int) -> int:
        try:
            self.cursor.execute(
                "SELECT COUNT(id) FROM shots WHERE session_id = ?", (session_id,)
            )
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi đếm phát bắn của phiên {session_id}: {e}")
            return 0

    def get_shots_for_session(self, session_id: int) -> list:
        try:
            self.cursor.execute(
                "SELECT * FROM shots WHERE session_id = ? ORDER BY shot_number ASC",
                (session_id,),
            )
            return _rows_to_dicts(self.cursor)
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy chi tiết các phát bắn: {e}")
            return []

    # ======================================================================
    # THỐNG KÊ
    # ======================================================================
    def get_session_stats(self, session_id: int) -> dict:
        """Thống kê của một phiên: tổng, trúng, trượt, chưa chấm, theo từng loại bia.

        Phát có score NULL (liên thanh, chưa nhận diện) được đếm là "chưa chấm"
        và KHÔNG tính vào tỷ lệ trúng.
        """
        stats = {
            "total": 0,
            "hits": 0,
            "misses": 0,
            "ungraded": 0,
            "rate": 0.0,
            "by_target": [],
        }
        try:
            self.cursor.execute(
                "SELECT target_detected, COUNT(*), "
                "SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN score IS NOT NULL AND score <= 0 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN score IS NULL THEN 1 ELSE 0 END) "
                "FROM shots WHERE session_id = ? "
                "GROUP BY target_detected ORDER BY target_detected ASC",
                (session_id,),
            )
            for target, total, hits, misses, ungraded in self.cursor.fetchall():
                hits, misses, ungraded = hits or 0, misses or 0, ungraded or 0
                stats["total"] += total
                stats["hits"] += hits
                stats["misses"] += misses
                stats["ungraded"] += ungraded
                stats["by_target"].append(
                    {
                        "target": target,
                        "total": total,
                        "hits": hits,
                        "graded": hits + misses,
                    }
                )
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thống kê phiên {session_id}: {e}")
            return stats

        graded = stats["hits"] + stats["misses"]
        if graded > 0:
            stats["rate"] = stats["hits"] / graded * 100.0
        return stats

    # ======================================================================
    # DỌN DẸP
    # ======================================================================
    def _remove_session_images(self, session_id: int):
        """Xóa thư mục ảnh của phiên (chỉ trong thư mục captures)."""
        session_dir = os.path.join(CAPTURES_DIR, str(session_id))
        if _is_inside_captures(session_dir) and os.path.isdir(session_dir):
            try:
                shutil.rmtree(session_dir)
            except OSError as e:
                logger.error(f"Không xóa được thư mục ảnh {session_dir}: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Đã đóng kết nối database.")
