# file: gui/windows/manage_window.py

import logging
import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.database import DatabaseManager
from gui.ui.theme import COLORS
from gui.ui.ui_manage import ManageGui

logger = logging.getLogger(__name__)


def display_target_name(raw) -> str:
    """Đổi tên lớp của model (ví dụ 'bia_so_4') thành tên hiển thị."""
    if raw == "Chưa nhận diện":
        return "Chưa nhận diện"
    if not raw or raw == "Trượt":
        return "Ngoài bia"
    if raw == "bia_so_7_8":  # dữ liệu của phiên bản cũ
        return "Bia số 7"
    if raw.startswith("bia_so_"):
        return f"Bia số {raw[len('bia_so_'):]}"
    text = raw.replace("_", " ").strip()
    return text[:1].upper() + text[1:]


# =============================================================================
# === HỘP THOẠI THÊM / SỬA NGƯỜI BẮN ===
# =============================================================================
class AddSoldierDialog(QDialog):
    def __init__(self, config: dict, is_edit_mode: bool = False, parent=None):
        super().__init__(parent)
        labels = config.get("labels", {})

        if is_edit_mode:
            title = labels.get("edit_trainee_dialog_title", "Chỉnh sửa thông tin")
        else:
            title = labels.get("add_trainee_dialog_title", "Thêm mới")
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        self.default_style = f"border: 1px solid {COLORS['border_strong']};"
        self.error_style = f"border: 2px solid {COLORS['danger']};"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['surface']}; }}
            QLabel {{ color: {COLORS['text']}; font-size: 13px; background: transparent; }}
            QLabel#dialogTitle {{ font-size: 17px; font-weight: 800; margin-bottom: 6px; }}
            QLineEdit {{
                color: {COLORS['text']};
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: 8px; padding: 7px; font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['primary']}; }}
            QPushButton {{
                color: #FFFFFF; background-color: {COLORS['primary']};
                border: 0; border-radius: 8px; padding: 7px 18px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {COLORS['primary_hover']}; }}
            QPushButton#cancelButton {{
                color: {COLORS['text']}; background-color: {COLORS['surface_soft']};
                border: 1px solid {COLORS['border_strong']};
            }}
        """)

        main_layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.name_input = QLineEdit()
        self.class_name_input = QLineEdit()
        form_layout.addRow(labels.get("trainee_name_prompt", "Họ và Tên:"), self.name_input)
        form_layout.addRow(labels.get("trainee_class_prompt", "Đơn vị:"), self.class_name_input)
        main_layout.addLayout(form_layout)

        buttons = QDialogButtonBox()
        buttons.addButton("Hoàn tất", QDialogButtonBox.AcceptRole)
        cancel_button = buttons.addButton("Hủy", QDialogButtonBox.RejectRole)
        cancel_button.setObjectName("cancelButton")
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "class_name": self.class_name_input.text().strip(),
        }

    def validate_and_accept(self):
        self.name_input.setStyleSheet(self.default_style)
        if self.get_data()["name"]:
            self.accept()
        else:
            self.name_input.setStyleSheet(self.error_style)
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền Họ và Tên.")


# =============================================================================
# === CỬA SỔ QUẢN LÝ - THỐNG KÊ ===
# =============================================================================
class ManageWindow(QMainWindow):
    DATA_PAGE = 0
    MESSAGE_PAGE = 1

    def __init__(self, config: dict, db: DatabaseManager):
        super().__init__()
        self.config = config
        self.db = db
        labels = self.config.get("labels", {})

        self.setWindowTitle(labels.get("app_title", "Quản lý"))

        self.ui = ManageGui(self.config)
        self.setCentralWidget(self.ui)

        self.current_soldier_id = None
        self.current_session_id = None
        self.current_shots = []
        self.current_shot_index = -1

        self.connect_signals()
        self.set_panels_state("NO_SOLDIER_SELECTED")

    def connect_signals(self):
        ui = self.ui
        ui.add_button.clicked.connect(self.open_add_soldier_dialog)
        ui.soldier_table.itemSelectionChanged.connect(self.on_soldier_selected)
        ui.history_list.itemSelectionChanged.connect(self.on_session_selected)
        ui.prev_shot_button.clicked.connect(self.show_previous_shot)
        ui.next_shot_button.clicked.connect(self.show_next_shot)
        ui.shot_table.itemSelectionChanged.connect(self.on_shot_table_selected)
        ui.soldier_table.customContextMenuRequested.connect(self.show_soldier_context_menu)
        ui.history_list.customContextMenuRequested.connect(self.show_session_context_menu)
        ui.search_box.textChanged.connect(self.filter_soldiers)

    # ==============================================
    # TÌM KIẾM
    # ==============================================

    def filter_soldiers(self):
        """Lọc danh sách theo nội dung ô tìm kiếm (tên hoặc đơn vị)."""
        search_text = self.ui.search_box.text().strip().lower()
        table = self.ui.soldier_table
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            class_item = table.item(row, 1)
            name_ok = bool(name_item) and search_text in name_item.text().lower()
            class_ok = bool(class_item) and search_text in class_item.text().lower()
            table.setRowHidden(row, not (name_ok or class_ok))

    # ==============================================
    # TRẠNG THÁI CÁC KHUNG
    # ==============================================

    def set_panels_state(self, state: str):
        labels = self.config.get("labels", {})
        trainee_term = labels.get("trainee", "Người học")

        if state == "NO_SOLDIER_SELECTED":
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.right_stack.setCurrentIndex(self.MESSAGE_PAGE)
            prompt = labels.get(
                "manage_select_trainee_prompt",
                "◀ Vui lòng chọn một {trainee} từ danh sách",
            )
            message = prompt.format(trainee=trainee_term.lower())
            self.ui.center_message_label.setText(message)
            self.ui.right_message_label.setText(message)
        elif state == "NO_SESSIONS":
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.right_stack.setCurrentIndex(self.MESSAGE_PAGE)
            prompt = labels.get(
                "manage_no_sessions_prompt", "{trainee} này chưa thực hiện phiên tập nào"
            )
            message = prompt.format(trainee=trainee_term.capitalize())
            self.ui.center_message_label.setText(message)
            self.ui.right_message_label.setText(message)
        elif state == "SOLDIER_SELECTED":
            self.ui.right_stack.setCurrentIndex(self.DATA_PAGE)
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.center_message_label.setText(
                "Vui lòng chọn một phiên tập ở danh sách bên phải để xem chi tiết"
            )
        elif state == "SHOW_DATA":
            self.ui.center_stack.setCurrentIndex(self.DATA_PAGE)
            self.ui.right_stack.setCurrentIndex(self.DATA_PAGE)

    # ==============================================
    # DANH SÁCH NGƯỜI BẮN
    # ==============================================

    def load_soldiers(self):
        self.ui.search_box.clear()
        self.current_soldier_id = None
        self.current_session_id = None
        self.ui.soldier_table.setRowCount(0)
        try:
            soldiers = self.db.get_all_soldiers()
            if not soldiers:
                self.set_panels_state("NO_SOLDIER_SELECTED")
                return
            self.ui.soldier_table.setRowCount(len(soldiers))
            for row, soldier in enumerate(soldiers):
                name_item = QTableWidgetItem(soldier["name"])
                name_item.setData(Qt.UserRole, soldier["id"])
                class_item = QTableWidgetItem(soldier.get("class_name") or "")
                class_item.setTextAlignment(Qt.AlignCenter)
                self.ui.soldier_table.setItem(row, 0, name_item)
                self.ui.soldier_table.setItem(row, 1, class_item)
            self.set_panels_state("NO_SOLDIER_SELECTED")
        except Exception as e:
            logger.error(f"Lỗi khi tải danh sách người bắn: {e}", exc_info=True)

    def on_soldier_selected(self):
        selected_items = self.ui.soldier_table.selectedItems()
        if not selected_items:
            self.current_soldier_id = None
            self.current_session_id = None
            self.set_panels_state("NO_SOLDIER_SELECTED")
            return

        name_item = self.ui.soldier_table.item(selected_items[0].row(), 0)
        soldier_id = name_item.data(Qt.UserRole)

        if soldier_id is not None and self.current_soldier_id != soldier_id:
            self.current_soldier_id = soldier_id
            self.current_session_id = None
            labels = self.config.get("labels", {})
            prefix = labels.get("history_title_prefix", "Lịch sử của")
            self.ui.history_box.setTitle(f"{prefix} {name_item.text()}")
            self.load_shooting_history(soldier_id)

    def open_add_soldier_dialog(self):
        dialog = AddSoldierDialog(self.config, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_data()
        if self.db.add_soldier(**data):
            QMessageBox.information(self, "Thành công", f"Đã thêm '{data['name']}'.")
            self.load_soldiers()
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể thêm người này.")

    def show_soldier_context_menu(self, pos):
        item = self.ui.soldier_table.itemAt(pos)
        if not item:
            return
        row = item.row()
        name_item = self.ui.soldier_table.item(row, 0)
        soldier_id = name_item.data(Qt.UserRole)
        if soldier_id is None:
            return
        soldier_name = name_item.text()

        menu = QMenu(self)
        menu.addAction("Sửa thông tin").triggered.connect(lambda: self.edit_soldier(row))
        menu.addAction("Xóa người này").triggered.connect(
            lambda: self.delete_soldier(soldier_id, soldier_name)
        )
        menu.exec(self.ui.soldier_table.mapToGlobal(pos))

    def edit_soldier(self, row):
        name_item = self.ui.soldier_table.item(row, 0)
        class_item = self.ui.soldier_table.item(row, 1)
        soldier_id = name_item.data(Qt.UserRole)

        dialog = AddSoldierDialog(self.config, is_edit_mode=True, parent=self)
        dialog.name_input.setText(name_item.text())
        dialog.class_name_input.setText(class_item.text() if class_item else "")
        if dialog.exec() != QDialog.Accepted:
            return

        if self.db.update_soldier(soldier_id, **dialog.get_data()):
            QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin.")
            selected_id = self.current_soldier_id
            self.load_soldiers()
            if selected_id is not None:
                for i in range(self.ui.soldier_table.rowCount()):
                    if self.ui.soldier_table.item(i, 0).data(Qt.UserRole) == selected_id:
                        self.ui.soldier_table.selectRow(i)
                        break
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể cập nhật thông tin.")

    def delete_soldier(self, soldier_id, soldier_name):
        reply = QMessageBox.warning(
            self,
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa '{soldier_name}'?\n"
            "TOÀN BỘ lịch sử bắn và ảnh của người này cũng sẽ bị xóa vĩnh viễn.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if self.db.delete_soldier(soldier_id):
            QMessageBox.information(self, "Thành công", f"Đã xóa '{soldier_name}'.")
            self.load_soldiers()
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể xóa người này.")

    # ==============================================
    # LỊCH SỬ CÁC PHIÊN
    # ==============================================

    def load_shooting_history(self, soldier_id):
        self.ui.history_list.clear()
        try:
            sessions = self.db.get_sessions_for_soldier(soldier_id)
            if not sessions:
                self.set_panels_state("NO_SESSIONS")
                return
            self.set_panels_state("SOLDIER_SELECTED")
            for session in sessions:
                name = session.get("exercise_name") or f"Phiên tập #{session['id']}"
                try:
                    date_obj = datetime.strptime(session["session_date"], "%Y-%m-%d %H:%M:%S")
                    date_text = date_obj.strftime("%H:%M - %d/%m/%Y")
                except (ValueError, TypeError):
                    date_text = session["session_date"]
                item = QListWidgetItem(f"{name}\n{date_text}")
                item.setData(Qt.UserRole, session["id"])
                self.ui.history_list.addItem(item)
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử bắn: {e}", exc_info=True)

    def on_session_selected(self):
        selected_items = self.ui.history_list.selectedItems()
        if not selected_items:
            self.current_session_id = None
            if self.current_soldier_id is not None and self.ui.history_list.count() > 0:
                self.set_panels_state("SOLDIER_SELECTED")
            return
        session_id = selected_items[0].data(Qt.UserRole)
        if session_id is not None:
            self.current_session_id = session_id
            self.set_panels_state("SHOW_DATA")
            self.load_session_details(session_id)

    def show_session_context_menu(self, pos):
        item = self.ui.history_list.itemAt(pos)
        if not item:
            return
        session_id = item.data(Qt.UserRole)
        session_name = item.text().split("\n")[0]

        menu = QMenu(self)
        menu.addAction("Đổi tên phiên").triggered.connect(
            lambda: self.edit_session_name(session_id)
        )
        menu.addAction("Xóa phiên").triggered.connect(
            lambda: self.delete_session(session_id, session_name)
        )
        menu.exec(self.ui.history_list.mapToGlobal(pos))

    def edit_session_name(self, session_id):
        session = self.db.get_session_by_id(session_id)
        if not session:
            return
        current_name = session.get("exercise_name") or ""
        while True:
            new_name, ok = QInputDialog.getText(
                self, "Đổi tên Phiên tập", "Nhập tên mới:", QLineEdit.Normal, current_name
            )
            if not ok:
                return
            stripped = new_name.strip()
            if not stripped:
                continue
            if self.db.session_name_exists(
                stripped, soldier_id=self.current_soldier_id, exclude_session_id=session_id
            ):
                QMessageBox.warning(
                    self,
                    "Tên bị trùng",
                    f"Người này đã có phiên tập tên '{stripped}'.\n"
                    "Vui lòng chọn một tên khác.",
                )
                current_name = stripped
                continue
            break

        if self.db.update_session_name(session_id, stripped):
            QMessageBox.information(self, "Thành công", "Đã đổi tên phiên tập.")
            self.load_shooting_history(self.current_soldier_id)
            for i in range(self.ui.history_list.count()):
                if self.ui.history_list.item(i).data(Qt.UserRole) == session_id:
                    self.ui.history_list.setCurrentRow(i)
                    break
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể đổi tên phiên tập.")

    def delete_session(self, session_id, session_name):
        reply = QMessageBox.warning(
            self,
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa phiên '{session_name}' không?\n"
            "Toàn bộ dữ liệu và ảnh của phiên này sẽ bị xóa vĩnh viễn.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if self.db.delete_session(session_id):
            QMessageBox.information(self, "Thành công", f"Đã xóa phiên '{session_name}'.")
            self.current_session_id = None
            self.load_shooting_history(self.current_soldier_id)
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể xóa phiên tập.")

    # ==============================================
    # CHI TIẾT PHIÊN
    # ==============================================

    def load_session_details(self, session_id):
        self.current_shots = self.db.get_shots_for_session(session_id)
        stats = self.db.get_session_stats(session_id)

        self.ui.stat_total.setText(str(stats["total"]))
        self.ui.stat_hits.setText(str(stats["hits"]))
        self.ui.stat_misses.setText(str(stats["misses"]))
        self.ui.stat_ungraded.setText(str(stats["ungraded"]))
        graded = stats["hits"] + stats["misses"]
        self.ui.stat_rate.setText(f"{stats['rate']:.1f}%" if graded else "--")

        self._fill_target_table(stats["by_target"])
        self._fill_shot_table()

        if self.current_shots:
            self.ui.shot_table.selectRow(0)
            self.current_shot_index = 0
        else:
            self.current_shot_index = -1
        self.update_shot_display()

    def _fill_target_table(self, by_target: list):
        table = self.ui.target_table
        table.setRowCount(len(by_target))
        for row, entry in enumerate(by_target):
            total, hits, graded = entry["total"], entry["hits"], entry["graded"]
            rate = f"{hits / graded * 100:.0f}%" if graded else "--"
            cells = [display_target_name(entry["target"]), str(total), str(hits), rate]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, column, item)

    def _fill_shot_table(self):
        table = self.ui.shot_table
        table.blockSignals(True)
        table.clearSelection()
        table.setRowCount(len(self.current_shots))
        for row, shot in enumerate(self.current_shots):
            try:
                ts = datetime.strptime(shot["timestamp"], "%Y-%m-%d %H:%M:%S")
                time_text = ts.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                time_text = str(shot["timestamp"])

            score = shot.get("score")
            if score is None:
                result_item = QTableWidgetItem("Chưa chấm")
                result_item.setForeground(QColor(COLORS["text_muted"]))
            elif score > 0:
                result_item = QTableWidgetItem("Trúng")
                result_item.setForeground(QColor(COLORS["success"]))
            else:
                result_item = QTableWidgetItem("Trượt")
                result_item.setForeground(QColor(COLORS["danger"]))

            cells = [
                QTableWidgetItem(str(shot["shot_number"])),
                QTableWidgetItem(time_text),
                QTableWidgetItem(display_target_name(shot.get("target_detected"))),
                result_item,
            ]
            for column, item in enumerate(cells):
                if column != 2:
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, column, item)
        table.blockSignals(False)

    # ==============================================
    # ẢNH KẾT QUẢ VÀ ĐIỀU HƯỚNG
    # ==============================================

    def update_shot_display(self):
        total = len(self.current_shots)
        has_shots = 0 <= self.current_shot_index < total

        self.ui.prev_shot_button.setEnabled(has_shots and self.current_shot_index > 0)
        self.ui.next_shot_button.setEnabled(has_shots and self.current_shot_index < total - 1)

        if not has_shots:
            self.ui.shot_index_label.setText("Phát 0/0")
            self.ui.result_image.setPixmap(QPixmap())
            self.ui.result_image.setText("Chưa có phát bắn")
            return

        shot = self.current_shots[self.current_shot_index]
        self.ui.shot_index_label.setText(f"Phát {self.current_shot_index + 1}/{total}")

        image_path = shot.get("image_path")
        pixmap = QPixmap(image_path) if image_path and os.path.isfile(image_path) else QPixmap()
        if pixmap.isNull():
            self.ui.result_image.setPixmap(QPixmap())
            self.ui.result_image.setText("Không tìm thấy ảnh")
        else:
            self.ui.result_image.setText("")
            self.ui.result_image.setPixmap(pixmap)

    def show_previous_shot(self):
        if self.current_shot_index > 0:
            self.ui.shot_table.selectRow(self.current_shot_index - 1)

    def show_next_shot(self):
        if self.current_shot_index < len(self.current_shots) - 1:
            self.ui.shot_table.selectRow(self.current_shot_index + 1)

    def on_shot_table_selected(self):
        selected_rows = self.ui.shot_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if self.current_shot_index != row:
            self.current_shot_index = row
            self.update_shot_display()
