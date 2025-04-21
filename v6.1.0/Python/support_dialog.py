import json
import os
import re
import html
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QIcon, QPalette
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QApplication, QFileDialog, QLineEdit
)
from edit_menu_dialog import EditMenuDialog

class BackupRestoreDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sao lưu/Khôi phục")
        self.setModal(True)
        self.result = None
        self.initUI()

        try:
            # Đặt kích thước cố định cho cửa sổ
            self.setFixedSize(250, 200)
            parent_rect = parent.geometry()
            dialog_rect = self.geometry()
            dialog_x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
            dialog_y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
            self.move(dialog_x, dialog_y)
        except Exception:
            pass

    def initUI(self):
        layout = QVBoxLayout()

        # Thêm tiêu đề
        title_label = QLabel("Sao lưu hoặc Khôi phục ghi chú")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        layout.addSpacing(10)  # Khoảng cách giữa tiêu đề và nút

        backup_button = QPushButton("Sao lưu")
        backup_button.setStyleSheet("""
            background-color: #4CAF50; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #388E3C;
            font-weight: bold;
        """)
        backup_button.setFixedSize(150, 40)  # Đặt kích thước cố định cho nút
        backup_button.clicked.connect(lambda: self.done(1))

        restore_button = QPushButton("Khôi phục")
        restore_button.setStyleSheet("""
            background-color: #FFB300; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #FF8F00;
            font-weight: bold;
        """)
        restore_button.setFixedSize(150, 40)  # Đặt kích thước cố định cho nút
        restore_button.clicked.connect(lambda: self.done(2))

        cancel_button = QPushButton("Hủy")
        cancel_button.setStyleSheet("""
            background-color: #F44336; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #D32F2F;
            font-weight: bold;
        """)
        cancel_button.setFixedSize(150, 40)  # Đặt kích thước cố định cho nút
        cancel_button.clicked.connect(self.reject)

        # Đặt các nút vào layout với căn giữa
        layout.addWidget(backup_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)  # Khoảng cách giữa các nút
        layout.addWidget(restore_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)  # Khoảng cách giữa các nút
        layout.addWidget(cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

class SupportDialog(QDialog):
    _instance = None  # Biến class-level để theo dõi instance duy nhất

    def __init__(self, main_window=None):
        super().__init__(None)  # Không đặt parent để độc lập
        try:
            # Kiểm tra nếu đã có instance tồn tại
            if SupportDialog._instance is not None:
                try:
                    SupportDialog._instance.show()
                    SupportDialog._instance.raise_()
                    SupportDialog._instance.activateWindow()
                    return
                except RuntimeError:
                    SupportDialog._instance = None

            SupportDialog._instance = self
            self.main_window = main_window
            self.setWindowTitle("Ghi chú")
            self.setModal(False)
            self.is_pinned = False

            # Thiết lập cờ cửa sổ
            self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowSystemMenuHint)

            parent_width = 400
            dialog_height = 300  # Chiều cao mặc định 300px
            if main_window:
                parent_rect = main_window.geometry()
                dialog_x = parent_rect.x() + parent_rect.width()
                dialog_y = parent_rect.y()
                self.move(dialog_x, dialog_y)

            self.setFixedWidth(parent_width)
            self.setFixedHeight(dialog_height)
            self.setMinimumHeight(300)
            self.setMaximumHeight(568)

            # Đồng bộ màu nền với main_window
            if main_window:
                palette = main_window.palette()
                background_color = palette.color(QPalette.ColorRole.Window).name()
                self.setStyleSheet(f"QDialog {{ background-color: {background_color}; }}")
            else:
                self.setStyleSheet("QDialog { background-color: #F0F0F0; }")

            # Kiểm tra sự tồn tại của file biểu tượng
            icon_path = 'images/icon.ico'
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))

            # Đặt đường dẫn cho file support_menu.json
            documents_path = os.path.expanduser("~/Documents")
            app_folder = os.path.join(documents_path, "Flight Ticket Calculator")
            try:
                os.makedirs(app_folder, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Không thể tạo thư mục lưu trữ: {str(e)}")

            self.menu_file = os.path.join(app_folder, "support_menu.json")
            self.menus = self.load_menus()
            self.initUI()

            # Cài đặt event filter để kiểm soát sự kiện
            if main_window:
                main_window.installEventFilter(self)

        except Exception as e:
            SupportDialog._instance = None
            raise

    def eventFilter(self, obj, event):
        """Chặn sự kiện thu nhỏ khi ghim."""
        try:
            if obj == self.main_window and self.is_pinned:
                if event.type() == QEvent.Type.WindowStateChange:
                    if self.main_window.isMinimized():
                        self.showNormal()
                        self.raise_()
                        self.activateWindow()
                        return True
            return super().eventFilter(obj, event)
        except Exception:
            return False

    def changeEvent(self, event):
        """Xử lý sự kiện thay đổi trạng thái của cửa sổ chính."""
        try:
            super().changeEvent(event)
            if event.type() == QEvent.Type.WindowStateChange and self.main_window and not self.is_pinned:
                if self.main_window.isMinimized():
                    if not self.isMinimized():
                        self.showMinimized()
                elif self.main_window.windowState() & Qt.WindowState.WindowNoState:
                    if self.isMinimized():
                        self.showNormal()
        except Exception:
            pass

    def closeEvent(self, event):
        """Ẩn cửa sổ khi ghim, đóng khi không ghim."""
        try:
            if self.is_pinned:
                self.hide()
                event.ignore()
            else:
                SupportDialog._instance = None
                super().closeEvent(event)
        except Exception:
            super().closeEvent(event)

    def initUI(self):
        try:
            layout = QVBoxLayout()

            # Tiêu đề và nút ghim
            title_layout = QHBoxLayout()
            title_label = QLabel("Tìm kiếm")
            title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
            self.pin_button = QPushButton("📌")
            self.pin_button.setStyleSheet("""
                background-color: transparent; 
                color: white; 
                border-radius: 5px; 
                padding: 3px;
                border: none;
            """)
            self.pin_button.setFixedSize(30, 30)
            self.pin_button.setToolTip("Ghim cửa sổ lên trên cùng")
            self.pin_button.clicked.connect(self.toggle_pin_window)
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            title_layout.addWidget(self.pin_button)
            layout.addLayout(title_layout)

            # Trường tìm kiếm
            search_layout = QVBoxLayout()
            search_input_layout = QHBoxLayout()
            self.search_input = QComboBox()
            self.search_input.setEditable(True)
            self.search_input.setPlaceholderText("Tìm kiếm ghi chú...")
            self.search_input.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
            self.search_input.lineEdit().textChanged.connect(self.limit_search_input_text)
            self.search_input.lineEdit().textChanged.connect(self.filter_menus)

            self.search_scope_combobox = QComboBox()
            self.search_scope_combobox.addItems(["Tên", "Tất cả"])
            self.search_scope_combobox.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
            self.search_scope_combobox.setMaximumWidth(60)
            self.search_scope_combobox.currentIndexChanged.connect(self.filter_menus)

            search_input_layout.addWidget(self.search_input)
            search_input_layout.addWidget(self.search_scope_combobox)

            self.search_results_list = QListWidget()
            self.search_results_list.setStyleSheet("""
                QListWidget { 
                    border: 1px solid #CCCCCC; 
                    border-radius: 5px; 
                    padding: 5px; 
                }
                QListWidget::item { 
                    color: #000000; 
                }
                QListWidget::item:hover { 
                    background-color: #B2EBF2; 
                    color: #000000; 
                }
                QListWidget::item:selected { 
                    background-color: #B2EBF2; 
                    color: #000000; 
                }
                QToolTip { 
                    background-color: #B2EBF2; 
                    color: #000000; 
                    border: 1px solid #B2EBF2; 
                    padding: 2px; 
                    max-width: 400px; 
                    white-space: pre-wrap; 
                }
            """)
            self.search_results_list.setMaximumHeight(120)
            self.search_results_list.hide()
            self.search_results_list.itemClicked.connect(self.edit_menu_from_search)

            search_layout.addLayout(search_input_layout)
            search_layout.addWidget(self.search_results_list)
            layout.addLayout(search_layout)

            # 2 cột danh sách menu
            self.lists_layout = QHBoxLayout()
            self.menu_list_1 = QListWidget()
            self.menu_list_2 = QListWidget()

            for menu_list in [self.menu_list_1, self.menu_list_2, self.search_results_list]:
                menu_list.setStyleSheet("""
                    QListWidget { 
                        border: 1px solid #CCCCCC; 
                        border-radius: 5px; 
                        padding: 5px; 
                    }
                    QListWidget::item { 
                        color: #000000; 
                    }
                    QListWidget::item:hover { 
                        background-color: #B2EBF2; 
                        color: #000000; 
                    }
                    QListWidget::item:selected { 
                        background-color: #B2EBF2; 
                        color: #000000; 
                    }
                    QToolTip { 
                        background-color: #B2EBF2; 
                        color: #000000; 
                        border: 1px solid #B2EBF2; 
                        padding: 2px; 
                        max-width: 400px; 
                        white-space: pre-wrap; 
                    }
                """)
                menu_list.setFixedWidth(200) if menu_list != self.search_results_list else None
                menu_list.setTextElideMode(Qt.TextElideMode.ElideRight)
                menu_list.setWordWrap(False)
                menu_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                menu_list.itemClicked.connect(self.select_menu)  # Sử dụng select_menu cho tất cả
                menu_list.itemDoubleClicked.connect(self.edit_menu)
                menu_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                menu_list.customContextMenuRequested.connect(self.copy_menu_content)
                self.lists_layout.addWidget(menu_list) if menu_list != self.search_results_list else None

            self.populate_menu_lists()
            layout.addLayout(self.lists_layout)

            # Các nút điều khiển
            button_layout = QHBoxLayout()
            self.add_button = QPushButton("➕ Thêm")
            self.add_button.setStyleSheet("""
                background-color: #4CAF50; 
                color: white; 
                border-radius: 5px; 
                padding: 5px;
                border: 1px solid #388E3C;
                font-weight: bold;
            """)
            self.add_button.setToolTip("Thêm ghi chú mới (Ctrl+N)")
            self.add_button.clicked.connect(self.add_menu)

            self.delete_button = QPushButton("🗑️ Xóa")
            self.delete_button.setStyleSheet("""
                background-color: #F44336; 
                color: white; 
                border-radius: 5px; 
                padding: 5px;
                border: 1px solid #D32F2F;
                font-weight: bold;
            """)
            self.delete_button.setToolTip("Xóa ghi chú đã chọn (Ctrl+D)")
            self.delete_button.clicked.connect(self.delete_menu)

            self.delete_all_button = QPushButton("🗑️ Xóa tất cả")
            self.delete_all_button.setStyleSheet("""
                background-color: #D32F2F; 
                color: white; 
                border-radius: 5px; 
                padding: 5px;
                border: 1px solid #B71C1C;
                font-weight: bold;
            """)
            self.delete_all_button.setToolTip("Xóa toàn bộ ghi chú (Ctrl+Shift+D)")
            self.delete_all_button.clicked.connect(self.delete_all_menus)

            self.backup_restore_button = QPushButton("💾 Sao lưu")
            self.backup_restore_button.setStyleSheet("""
                background-color: #FFB300; 
                color: white; 
                border-radius: 5px; 
                padding: 5px;
                border: 1px solid #FF8F00;
                font-weight: bold;
            """)
            self.backup_restore_button.setToolTip("Sao lưu hoặc khôi phục ghi chú")
            self.backup_restore_button.clicked.connect(self.show_backup_restore_dialog)

            button_layout.addWidget(self.add_button)
            button_layout.addWidget(self.delete_button)
            button_layout.addWidget(self.delete_all_button)
            button_layout.addWidget(self.backup_restore_button)
            layout.addLayout(button_layout)

            self.setLayout(layout)

            # Điều chỉnh chiều cao cửa sổ
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.adjust_window_height)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể khởi tạo giao diện: {str(e)}")

    def toggle_pin_window(self):
        """Chuyển đổi trạng thái ghim cửa sổ."""
        try:
            self.is_pinned = not self.is_pinned
            if self.is_pinned:
                self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
                self.pin_button.setText("📍")
                self.pin_button.setStyleSheet("""
                    background-color: #4CAF50; 
                    color: white; 
                    border-radius: 5px; 
                    padding: 3px;
                    border: 1px solid #388E3C;
                """)
            else:
                self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowSystemMenuHint)
                self.pin_button.setText("📌")
                self.pin_button.setStyleSheet("""
                    background-color: transparent; 
                    color: white; 
                    border-radius: 5px; 
                    padding: 3px;
                    border: none;
                """)
            self.show()
            self.raise_()
            self.activateWindow()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể ghim cửa sổ: {str(e)}")

    def adjust_window_height(self):
        """Điều chỉnh chiều cao cửa sổ dựa trên nội dung, nhưng giữ mặc định 300px."""
        try:
            total_height = 300
            for i in range(self.layout().count()):
                widget = self.layout().itemAt(i).widget()
                layout = self.layout().itemAt(i).layout()
                if widget:
                    total_height += widget.sizeHint().height()
                elif layout:
                    total_height += layout.sizeHint().height()
            total_height = max(300, min(total_height, 568))
            self.setFixedHeight(total_height)
        except Exception:
            self.setFixedHeight(300)

    def load_menus(self):
        """Tải danh sách menu từ file JSON."""
        try:
            if os.path.exists(self.menu_file):
                with open(self.menu_file, 'r', encoding='utf-8') as f:
                    menus = json.load(f)
                return menus if isinstance(menus, list) else []
            return []
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải ghi chú: {str(e)}")
            return []

    def save_menus(self):
        """Lưu danh sách menu vào file JSON."""
        try:
            with open(self.menu_file, 'w', encoding='utf-8') as f:
                json.dump(self.menus, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu ghi chú: {str(e)}")

    def clean_content(self, content):
        """Chuyển thực thể HTML và trả về nội dung (không cần loại bỏ HTML vì đã là plain text)."""
        try:
            # Chuyển thực thể HTML (ví dụ: & thành &)
            content = html.unescape(content)
            return content
        except Exception:
            return content

    def highlight_search_term(self, content, search_text):
        """Highlight từ khóa tìm kiếm bằng màu đỏ và chuyển \n thành <br>."""
        if not search_text or not content:
            return content
        # Thoát các ký tự đặc biệt trong search_text
        escaped_search = re.escape(search_text)
        # Thay thế từ khóa bằng thẻ span, không phân biệt hoa thường
        highlighted = re.sub(
            f'({escaped_search})',
            r'<span style="background-color: yellow;color:red">\1</span>',
            content,
            flags=re.IGNORECASE
        )
        # Chuyển \n thành <br> để đảm bảo xuống dòng trong tooltip
        highlighted = highlighted.replace('\n', '<br>')
        return highlighted

    def format_tooltip(self, content):
        """Chuyển \n thành <br> và bọc nội dung trong thẻ HTML để đảm bảo tự động xuống dòng."""
        if not content:
            return content
        content = content.replace('\n', '<br>')
        return f"<div>{content}</div>"

    def populate_menu_lists(self):
        """Phân phối menu vào hai danh sách và thêm tooltip."""
        try:
            self.menu_list_1.clear()
            self.menu_list_2.clear()
            for i, menu in enumerate(self.menus):
                # Làm sạch tên menu: loại bỏ ký tự xuống dòng
                display_name = menu["name"].replace('\n', ' ')
                # Thêm STT vào trước tên menu
                display_name = f"{i + 1}. {display_name}"
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, i)
                # Tạo tooltip từ nội dung menu gốc
                tooltip_content = menu["content"]
                tooltip_content = tooltip_content[:1000] + ("..." if len(tooltip_content) > 1000 else "")
                # Chuyển thực thể HTML và định dạng tooltip
                tooltip_content = self.clean_content(tooltip_content)
                tooltip_content = self.format_tooltip(tooltip_content)
                item.setToolTip(tooltip_content)
                target_list = self.menu_list_1 if i % 2 == 0 else self.menu_list_2
                target_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể hiển thị ghi chú: {str(e)}")

    def select_menu(self, item):
        """Chọn một menu và bỏ chọn các menu khác."""
        try:
            # Lấy chỉ số menu từ item được chọn
            menu_index = item.data(Qt.ItemDataRole.UserRole)
            menu = self.menus[menu_index]
            
            # Bỏ chọn tất cả các item trong menu_list_1, menu_list_2 và search_results_list
            for menu_list in [self.menu_list_1, self.menu_list_2, self.search_results_list]:
                menu_list.clearSelection()
            
            # Đặt lại trạng thái chọn cho item hiện tại
            item.setSelected(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể chọn ghi chú: {str(e)}")

    def add_menu(self):
        """Thêm một menu mới."""
        try:
            dialog = EditMenuDialog(self, title="Thêm ghi chú mới")
            if dialog.exec():
                menu_name, menu_content = dialog.get_data()
                if menu_name and menu_content:
                    self.menus.append({"name": menu_name, "content": menu_content})
                    self.save_menus()
                    self.populate_menu_lists()
                    self.search_input.addItem(menu_name)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm ghi chú: {str(e)}")

    def edit_menu(self, item):
        """Chỉnh sửa menu đã chọn."""
        try:
            menu_index = item.data(Qt.ItemDataRole.UserRole)
            menu = self.menus[menu_index]
            dialog = EditMenuDialog(
                self,
                menu_name=menu["name"],
                menu_content=menu["content"],
                title=f"Chỉnh sửa Menu: {menu['name']}"
            )
            if dialog.exec():
                new_name, new_content = dialog.get_data()
                if new_name and new_content:
                    self.menus[menu_index] = {"name": new_name, "content": new_content}
                    self.save_menus()
                    self.populate_menu_lists()
                    self.update_search_items()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể chỉnh sửa ghi chú: {str(e)}")

    def edit_menu_from_search(self, item):
        """Chỉnh sửa menu từ kết quả tìm kiếm."""
        try:
            menu_name = item.text()
            menu_index = next((i for i, m in enumerate(self.menus) if m["name"] == menu_name), None)
            if menu_index is not None:
                menu = self.menus[menu_index]
                dialog = EditMenuDialog(
                    self,
                    menu_name=menu["name"],
                    menu_content=menu["content"],
                    title=f"Chỉnh sửa Menu: {menu['name']}"
                )
                if dialog.exec():
                    new_name, new_content = dialog.get_data()
                    if new_name and new_content:
                        self.menus[menu_index] = {"name": new_name, "content": new_content}
                    self.rearrange_menus()
                    self.save_menus()
                    self.populate_menu_lists()
                    self.update_search_items()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể chỉnh sửa ghi chú từ tìm kiếm: {str(e)}")

    def rearrange_menus(self):
        """Sắp xếp lại danh sách menu."""
        try:
            self.menus = sorted(self.menus, key=lambda x: x["name"].lower())
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể sắp xếp menu: {str(e)}")

    def delete_menu(self):
        """Xóa menu đã chọn."""
        try:
            selected_items = self.menu_list_1.selectedItems() + self.menu_list_2.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một ghi chú để xóa!")
                return
            item = selected_items[0]
            menu_index = item.data(Qt.ItemDataRole.UserRole)
            menu_name = self.menus[menu_index]["name"]
            reply = QMessageBox.question(
                self,
                "Xác nhận xóa",
                f"Bạn có chắc chắn muốn xóa ghi chú '{menu_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                del self.menus[menu_index]
                self.save_menus()
                self.populate_menu_lists()
                self.update_search_items()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa ghi chú: {str(e)}")

    def delete_all_menus(self):
        """Xóa toàn bộ menu."""
        try:
            if not self.menus:
                QMessageBox.warning(self, "Cảnh báo", "Không có ghi chú nào để xóa!")
                return
            reply = QMessageBox.question(
                self,
                "Xác nhận xóa tất cả",
                "Bạn có chắc chắn muốn xóa toàn bộ ghi chú? Hành động này không thể hoàn tác!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.menus = []
                self.save_menus()
                self.populate_menu_lists()
                self.update_search_items()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa tất cả ghi chú: {str(e)}")

    def copy_menu_content(self, pos):
        """Sao chép nội dung menu vào clipboard."""
        try:
            menu_list = self.sender()
            item = menu_list.itemAt(pos)
            if item:
                menu_index = item.data(Qt.ItemDataRole.UserRole)
                menu = self.menus[menu_index]
                content = self.clean_content(menu["content"])
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                QMessageBox.information(self, "Thành công", f"Nội dung của '{menu['name']}' đã được sao chép vào clipboard!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể sao chép nội dung: {str(e)}")

    def limit_search_input_text(self, text):
        """Giới hạn độ dài văn bản tìm kiếm."""
        try:
            if len(text) > 60:
                self.search_input.lineEdit().setText(text[:60])
        except Exception:
            pass

    def filter_menus(self):
        """Lọc menu dựa trên tìm kiếm và thêm tooltip cho kết quả."""
        try:
            search_text = self.search_input.currentText().strip().lower()
            search_scope = self.search_scope_combobox.currentText()
            self.search_results_list.clear()
            if not search_text:
                self.search_results_list.hide()
                self.populate_menu_lists()
                return

            filtered_menus = []
            for i, menu in enumerate(self.menus):
                menu_name = menu["name"].lower()
                menu_content = self.clean_content(menu["content"]).lower()
                if search_scope == "Tên" and search_text in menu_name:
                    filtered_menus.append((i, menu["name"]))
                elif search_scope == "Tất cả" and (search_text in menu_name or search_text in menu_content):
                    filtered_menus.append((i, menu["name"]))

            self.menu_list_1.clear()
            self.menu_list_2.clear()
            for i, (menu_index, menu_name) in enumerate(filtered_menus):
                # Làm sạch tên menu: loại bỏ ký tự xuống dòng
                display_name = menu_name.replace('\n', ' ')
                # Thêm STT vào trước tên menu
                display_name = f"{i + 1}. {display_name}"
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, menu_index)
                # Tạo tooltip từ nội dung menu gốc
                tooltip_content = self.menus[menu_index]["content"]
                tooltip_content = tooltip_content[:1000] + ("..." if len(tooltip_content) > 1000 else "")
                # Chuyển thực thể HTML và highlight từ khóa
                tooltip_content = self.clean_content(tooltip_content)
                tooltip_content = self.highlight_search_term(tooltip_content, search_text)
                item.setToolTip(tooltip_content)
                target_list = self.menu_list_1 if i % 2 == 0 else self.menu_list_2
                target_list.addItem(item)

            if filtered_menus:
                self.search_results_list.show()
                for _, menu_name in filtered_menus:
                    menu_index = next(i for i, m in enumerate(self.menus) if m["name"].lower() == menu_name.lower())
                    # Làm sạch tên menu: loại bỏ ký tự xuống dòng
                    display_name = menu_name.replace('\n', ' ')
                    # Thêm STT vào trước tên menu
                    display_name = f"{i + 1}. {display_name}"
                    item = QListWidgetItem(display_name)
                    item.setData(Qt.ItemDataRole.UserRole, menu_index)
                    # Tạo tooltip từ nội dung menu gốc
                    tooltip_content = self.menus[menu_index]["content"]
                    tooltip_content = tooltip_content[:1000] + ("..." if len(tooltip_content) > 1000 else "")
                    # Chuyển thực thể HTML và highlight từ khóa
                    tooltip_content = self.clean_content(tooltip_content)
                    tooltip_content = self.highlight_search_term(tooltip_content, search_text)
                    item.setToolTip(tooltip_content)
                    self.search_results_list.addItem(item)
            else:
                self.search_results_list.hide()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lọc menu: {str(e)}")

    def update_search_items(self):
        """Cập nhật danh sách tìm kiếm."""
        try:
            self.search_input.clear()
            for menu in self.menus:
                self.search_input.addItem(menu["name"])
        except Exception:
            pass

    def show_backup_restore_dialog(self):
        """Hiển thị dialog sao lưu/khôi phục."""
        try:
            dialog = BackupRestoreDialog(self)
            result = dialog.exec()
            if result == 1:
                self.backup_menus()
            elif result == 2:
                self.restore_menus()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở dialog sao lưu/khôi phục: {str(e)}")

    def backup_menus(self):
        """Sao lưu ghi chú vào file JSON."""
        try:
            from datetime import datetime
            # Tạo tên file mặc định theo định dạng Flight-Ticket-Calculator_YYYYMMDDHHMMSS.json
            current_time = datetime.now().strftime("%Y%m%d%H%M%S")
            default_file_name = f"Flight-Ticket-Calculator_{current_time}.json"
            default_path = os.path.join(os.path.expanduser("~/Documents"), default_file_name)

            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Sao lưu Ghi chú",
                default_path,
                "JSON Files (*.json)"
            )
            if file_name:
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(self.menus, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "Thành công", "Sao lưu ghi chú thành công!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể sao lưu ghi chú: {str(e)}")

    def restore_menus(self):
        """Khôi phục menu từ file JSON."""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Khôi phục ghi chú",
                os.path.expanduser("~/Documents"),
                "JSON Files (*.json)"
            )
            if file_name:
                with open(file_name, 'r', encoding='utf-8') as f:
                    restored_menus = json.load(f)
                if not isinstance(restored_menus, list):
                    raise ValueError("File sao lưu không hợp lệ!")
                self.menus = restored_menus
                self.save_menus()
                self.populate_menu_lists()
                self.update_search_items()
                QMessageBox.information(self, "Thành công", "Khôi phục ghi chú thành công!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể khôi phục ghi chú: {str(e)}")