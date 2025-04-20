import json
import os
import re
import html
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFontMetrics
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QApplication, QFileDialog
)
from edit_menu_dialog import EditMenuDialog
from utils import get_logger

logger = get_logger()

class BackupRestoreDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sao lưu/Khôi phục")
        self.setModal(True)
        self.result = None
        self.initUI()

        self.adjustSize()
        parent_rect = parent.geometry()
        dialog_rect = self.geometry()
        dialog_x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
        dialog_y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
        self.move(dialog_x, dialog_y)

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Bạn muốn sao lưu hay khôi phục danh sách ghi chú?"))

        button_layout = QHBoxLayout()
        self.backup_btn = QPushButton("Sao lưu")
        self.backup_btn.setStyleSheet("""
            background-color: #FFB300; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #FF8F00;
        """)
        self.backup_btn.clicked.connect(lambda: self.done(1))
        
        self.restore_btn = QPushButton("Khôi phục")
        self.restore_btn.setStyleSheet("""
            background-color: #2196F3; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #1976D2;
        """)
        self.restore_btn.clicked.connect(lambda: self.done(2))
        
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.setStyleSheet("""
            background-color: #757575; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #616161;
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.backup_btn)
        button_layout.addWidget(self.restore_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

class SupportDialog(QDialog):
    _instance = None  # Biến class-level để theo dõi instance duy nhất

    def __init__(self, parent=None):
        super().__init__(parent)  # Gọi super().__init__() trước để tránh lỗi

        # Kiểm tra nếu đã có instance tồn tại
        if SupportDialog._instance is not None:
            SupportDialog._instance.raise_()  # Đưa cửa sổ hiện tại lên trên
            SupportDialog._instance.activateWindow()  # Focus vào cửa sổ
            self.deleteLater()  # Xóa instance mới vừa tạo
            return

        SupportDialog._instance = self  # Lưu instance vào biến class-level
        logger.debug("Khởi tạo SupportDialog")
        self.setWindowTitle("Ghi chú")
        self.setModal(False)
        self.is_pinned = False

        parent_width = 400
        if parent:
            parent_rect = parent.geometry()
            dialog_height = int(parent_rect.height() * 0.8)  # 80% chiều cao cửa sổ chính
            dialog_x = parent_rect.x() + parent_rect.width()  # Bên phải cửa sổ chính
            dialog_y = parent_rect.y()  # Căn trên cùng với cửa sổ chính
            self.move(dialog_x, dialog_y)
        else:
            dialog_height = 400  # Giá trị mặc định nếu không có parent

        self.setFixedWidth(parent_width)  # Chỉ cố định chiều rộng
        self.setMinimumHeight(300)  # Chiều cao tối thiểu
        self.setMaximumHeight(1000)  # Chiều cao tối đa
        self.resize(parent_width, dialog_height)  # Đặt kích thước ban đầu

        try:
            self.setWindowIcon(QIcon('images/icon.ico'))
        except Exception as e:
            logger.error(f"Không thể tải icon: {str(e)}")
        self.menu_file = "support_menu.json"
        self.menus = self.load_menus()
        self.initUI()

    def closeEvent(self, event):
        """Đặt _instance về None khi cửa sổ đóng."""
        SupportDialog._instance = None
        super().closeEvent(event)

    def initUI(self):
        logger.debug("Khởi tạo giao diện SupportDialog")
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
        self.search_input.setPlaceholderText("Tìm kiếm menu...")
        self.search_input.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        # Giới hạn độ dài văn bản trong QComboBox
        self.search_input.lineEdit().textChanged.connect(self.limit_search_input_text)
        self.search_input.lineEdit().textChanged.connect(self.filter_menus)
        
        self.search_scope_combobox = QComboBox()
        self.search_scope_combobox.addItems(["Menu", "Tất cả"])
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
                background-color: #4DD0E1; 
                color: #000000; 
            }
        """)
        self.search_results_list.setMaximumHeight(60)
        self.search_results_list.hide()
        self.search_results_list.itemClicked.connect(self.edit_menu_from_search)
        
        search_layout.addLayout(search_input_layout)
        search_layout.addWidget(self.search_results_list)
        layout.addLayout(search_layout)

        # 2 cột danh sách menu
        self.lists_layout = QHBoxLayout()
        self.menu_list_1 = QListWidget()
        self.menu_list_2 = QListWidget()

        for menu_list in [self.menu_list_1, self.menu_list_2]:
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
                    background-color: #4DD0E1; 
                    color: #000000; 
                }
            """)
            menu_list.setFixedWidth(200)
            menu_list.setTextElideMode(Qt.TextElideMode.ElideRight)
            menu_list.itemClicked.connect(self.select_menu)
            menu_list.itemDoubleClicked.connect(self.edit_menu)
            menu_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            menu_list.customContextMenuRequested.connect(self.copy_menu_content)
            self.lists_layout.addWidget(menu_list)

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
        self.add_button.setToolTip("Thêm menu mới (Ctrl+N)")
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
        self.delete_button.setToolTip("Xóa menu đã chọn (Ctrl+D)")
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
        self.delete_all_button.setToolTip("Xóa toàn bộ menu (Ctrl+Shift+D)")
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
        self.backup_restore_button.setToolTip("Sao lưu hoặc khôi phục danh sách ghi chú")
        self.backup_restore_button.clicked.connect(self.backup_restore)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.delete_all_button)
        button_layout.addWidget(self.backup_restore_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        logger.debug("Hoàn tất khởi tạo giao diện SupportDialog")

    def toggle_pin_window(self):
        """Chuyển đổi trạng thái ghim cửa sổ lên trên cùng."""
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self.pin_button.setStyleSheet("""
                background-color: #4CAF50; 
                color: white; 
                border-radius: 5px; 
                padding: 3px;
                border: 1px solid #388E3C;
            """)
            self.pin_button.setToolTip("Bỏ ghim cửa sổ")
            logger.debug("Đã ghim cửa sổ SupportDialog lên trên cùng")
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
            self.pin_button.setStyleSheet("""
                background-color: transparent; 
                color: white; 
                border-radius: 5px; 
                padding: 3px;
                border: none;
            """)
            self.pin_button.setToolTip("Ghim cửa sổ lên trên cùng")
            logger.debug("Đã bỏ ghim cửa sổ SupportDialog")
        self.show()

    def clean_content(self, content):
        """Loại bỏ thẻ HTML và CSS thừa từ nội dung, giữ các ký tự xuống dòng, giải mã HTML entities."""
        plain_content = re.sub(r'<[^>]+>', '', content)
        plain_content = re.sub(r'p,\s*li\s*{[^}]+}', '', plain_content)
        plain_content = re.sub(r'hr\s*{[^}]+}', '', plain_content)
        plain_content = re.sub(r'li\.unchecked::marker\s*{[^}]+}', '', plain_content)
        plain_content = re.sub(r'li\.checked::marker\s*{[^}]+}', '', plain_content)
        plain_content = html.unescape(plain_content)
        plain_content = re.sub(r'[ \t]+', ' ', plain_content).strip()
        return plain_content

    def highlight_keyword(self, text, keyword):
        """Làm nổi bật từ khóa trong văn bản bằng cách bọc trong thẻ <span> màu đỏ."""
        if not keyword:
            return text
        text = html.unescape(text)
        escaped_keyword = re.escape(keyword)
        pattern = f'({escaped_keyword})'
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        highlighted_text = ''
        for part in parts:
            if re.fullmatch(escaped_keyword, part, flags=re.IGNORECASE):
                highlighted_text += f'<span style="color: red;">{part}</span>'
            else:
                highlighted_text += html.escape(part)
        return highlighted_text

    def load_menus(self):
        """Tải danh sách menu từ file JSON."""
        try:
            if os.path.exists(self.menu_file):
                with open(self.menu_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Lỗi khi tải menu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể tải menu: {str(e)}")
            return []

    def save_menus(self):
        """Lưu danh sách menu vào file JSON."""
        try:
            with open(self.menu_file, 'w', encoding='utf-8') as f:
                json.dump(self.menus, f, ensure_ascii=False, indent=4)
            logger.debug("Đã lưu menu vào file")
        except Exception as e:
            logger.error(f"Lỗi khi lưu menu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu menu: {str(e)}")

    def filter_menus(self):
        """Hiển thị danh sách kết quả tìm kiếm trong danh sách xổ xuống."""
        filter_text = self.search_input.lineEdit().text().strip()
        self.search_results_list.clear()

        if not filter_text:
            self.search_results_list.hide()
            return

        search_scope = self.search_scope_combobox.currentText()
        search_in_content = search_scope == "Tất cả"

        filtered_menus = []
        for idx, menu in enumerate(self.menus):
            name = menu.get('name', '')
            content = menu.get('content', '') if search_in_content else ''
            plain_content = self.clean_content(content) if search_in_content else ''

            name_lower = name.lower()
            content_lower = plain_content.lower()
            filter_text_lower = filter_text.lower()

            if filter_text_lower in name_lower or (search_in_content and filter_text_lower in content_lower):
                display_text = f"{idx + 1}. {name}"
                # Cắt ngắn văn bản cho search_results_list
                truncated_text = self.truncate_text(display_text, self.search_results_list)
                highlighted_content = self.highlight_keyword(plain_content, filter_text) if search_in_content else ''
                cleaned_tooltip = self.clean_content(highlighted_content)  # Loại bỏ HTML
                tooltip = html.unescape(cleaned_tooltip[:300]) + ("..." if len(cleaned_tooltip) > 300 else "")
                item = QListWidgetItem(truncated_text)
                item.setToolTip(tooltip)
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.search_results_list.addItem(item)

        if self.search_results_list.count() > 0:
            self.search_results_list.show()
        else:
            self.search_results_list.hide()

    def edit_menu_from_search(self, item):
        """Mở cửa sổ chỉnh sửa khi nhấn vào một mục trong danh sách tìm kiếm."""
        try:
            menu_name = item.data(Qt.ItemDataRole.UserRole)
            logger.debug(f"Mở cửa sổ chỉnh sửa từ tìm kiếm cho menu: {menu_name}")
            for menu in self.menus:
                if menu['name'] == menu_name:
                    dialog = EditMenuDialog(
                        self,
                        menu_name=menu['name'],
                        menu_content=menu['content'],
                        title="Sửa Menu"
                    )
                    if dialog.exec():
                        new_name, content = dialog.get_data()
                        if not new_name:
                            QMessageBox.warning(self, "Cảnh báo", "Tên menu không được để trống!")
                            return
                        if new_name != menu_name and any(m['name'] == new_name for m in self.menus):
                            QMessageBox.warning(self, "Cảnh báo", "Tên menu đã tồn tại!")
                            return
                        menu['name'] = new_name
                        menu['content'] = content
                        self.save_menus()
                        self.populate_menu_lists()
                        logger.debug(f"Đã sửa menu: {menu_name} -> {new_name}")
                    break
        except Exception as e:
            logger.error(f"Lỗi khi sửa menu từ tìm kiếm: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể sửa menu: {str(e)}")

    def truncate_text(self, text, widget):
        """Cắt ngắn văn bản để vừa với chiều rộng của widget, thêm dấu ..."""
        metrics = QFontMetrics(widget.font())
        # Lấy chiều rộng khả dụng của widget, trừ đi padding và scrollbar
        available_width = widget.width() - 30  # 20px cho padding và scrollbar
        if metrics.horizontalAdvance(text) <= available_width:
            return text
        truncated = text
        while metrics.horizontalAdvance(truncated + "...") > available_width and len(truncated) > 1:
            truncated = truncated[:-1]
        return truncated + "..."

    def populate_menu_lists(self, filter_text=""):
        """Hiển thị danh sách menu trong 2 cột, sắp xếp theo hàng ngang (12, 34, ...)."""
        self.menu_list_1.clear()
        self.menu_list_2.clear()

        for i, (idx, menu) in enumerate(enumerate(self.menus)):
            name = menu.get('name', '')
            content = menu.get('content', '')
            plain_content = self.clean_content(content)

            col = i % 2
            display_text = f"{idx + 1}. {name}"
            # Sử dụng truncate_text với widget tương ứng
            menu_list = self.menu_list_1 if col == 0 else self.menu_list_2
            truncated_text = self.truncate_text(display_text, menu_list)
            item = QListWidgetItem(truncated_text)
            preview = plain_content[:300] + ("..." if len(plain_content) > 300 else "")
            item.setToolTip(preview)
            if col == 0:
                self.menu_list_1.addItem(item)
            else:
                self.menu_list_2.addItem(item)

        logger.debug(f"Đã hiển thị {len(self.menus)} menu trong 2 cột theo hàng ngang")

    def select_menu(self, item):
        """Chọn một menu trong danh sách, chỉ cho phép chọn 1 mục tại 1 thời điểm."""
        logger.debug(f"Đã chọn menu: {item.text()}")
        sender = self.sender()
        for menu_list in [self.menu_list_1, self.menu_list_2]:
            if menu_list != sender:
                menu_list.clearSelection()

    def copy_menu_content(self, position):
        """Sao chép nội dung menu khi nhấn chuột phải."""
        try:
            sender = self.sender()
            if not sender:
                return
            item = sender.itemAt(position)
            if not item:
                return
            menu_name = item.text().split(". ", 1)[1].rstrip("...")
            for menu in self.menus:
                if menu['name'].startswith(menu_name):
                    content = self.clean_content(menu['content'])
                    clipboard = QApplication.clipboard()
                    clipboard.setText(content)
                    QMessageBox.information(self, "Sao chép", f"Nội dung của '{menu['name']}' đã được sao chép vào clipboard.")
                    logger.debug(f"Đã sao chép nội dung menu: {menu['name']}")
                    break
        except Exception as e:
            logger.error(f"Lỗi khi sao chép nội dung menu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể sao chép nội dung: {str(e)}")

    def add_menu(self):
        """Thêm menu mới."""
        try:
            dialog = EditMenuDialog(self, title="Thêm Menu Mới")
            if dialog.exec():
                name, content = dialog.get_data()
                if not name:
                    QMessageBox.warning(self, "Cảnh báo", "Tên menu không được để trống!")
                    return
                if any(menu['name'] == name for menu in self.menus):
                    QMessageBox.warning(self, "Cảnh báo", "Tên menu đã tồn tại!")
                    return
                self.menus.append({"name": name, "content": content})
                self.save_menus()
                self.populate_menu_lists()
                logger.debug(f"Đã thêm menu: {name}")
        except Exception as e:
            logger.error(f"Lỗi khi thêm menu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm menu: {str(e)}")

    def edit_menu(self, item=None):
        """Sửa menu đã chọn (kích hoạt khi nhấp đúp)."""
        try:
            current_item = None
            if item is not None:
                sender = self.sender()
                if sender:
                    current_item = sender.currentItem()
            else:
                return

            if not current_item:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một menu để sửa!")
                return

            current_name = current_item.text().split(". ", 1)[1].rstrip("...")
            logger.debug(f"Mở cửa sổ chỉnh sửa cho menu: {current_name}")
            for menu in self.menus:
                if menu['name'].startswith(current_name):
                    dialog = EditMenuDialog(
                        self,
                        menu_name=menu['name'],
                        menu_content=menu['content'],
                        title="Sửa Menu"
                    )
                    if dialog.exec():
                        new_name, content = dialog.get_data()
                        if not new_name:
                            QMessageBox.warning(self, "Cảnh báo", "Tên menu không được để trống!")
                            return
                        if new_name != menu['name'] and any(m['name'] == new_name for m in self.menus):
                            QMessageBox.warning(self, "Cảnh báo", "Tên menu đã tồn tại!")
                            return
                        menu['name'] = new_name
                        menu['content'] = content
                        self.save_menus()
                        self.populate_menu_lists()
                        logger.debug(f"Đã sửa menu: {current_name} -> {new_name}")
                    break
        except Exception as e:
            logger.error(f"Lỗi khi sửa menu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể sửa menu: {str(e)}")

    def delete_menu(self):
        """Xóa menu đã chọn, với xác nhận."""
        try:
            current_item = None
            selected_list = None
            for lst in [self.menu_list_1, self.menu_list_2]:
                if lst.currentItem():
                    current_item = lst.currentItem()
                    selected_list = lst
                    break

            if not current_item:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một menu để xóa!")
                return

            current_name = current_item.text().split(". ", 1)[1].rstrip("...")
            logger.debug(f"Yêu cầu xóa menu: {current_name}")
            for menu in self.menus:
                if menu['name'].startswith(current_name):
                    current_name = menu['name']
                    break
            reply = QMessageBox.question(
                self, "Xác nhận xóa",
                f"Bạn có chắc muốn xóa menu '{current_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.menus = [menu for menu in self.menus if menu['name'] != current_name]
                self.save_menus()
                self.populate_menu_lists()
                logger.debug(f"Đã xóa menu: {current_name}")
                if selected_list:
                    selected_list.clearSelection()
        except Exception as e:
            logger.error(f"Lỗi khi xóa menu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa menu: {str(e)}")

    def delete_all_menus(self):
        """Xóa tất cả menu, với xác nhận."""
        try:
            if not self.menus:
                QMessageBox.information(self, "Thông báo", "Không có menu nào để xóa!")
                return
            reply = QMessageBox.question(
                self, "Xác nhận xóa tất cả",
                "Bạn có chắc muốn xóa toàn bộ menu? Hành động này không thể hoàn tác!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.menus = []
                self.save_menus()
                self.populate_menu_lists()
                logger.debug("Đã xóa toàn bộ menu")
                QMessageBox.information(self, "Thông báo", "Đã xóa toàn bộ menu!")
        except Exception as e:
            logger.error(f"Lỗi khi xóa tất cả menu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa tất cả menu: {str(e)}")
            
    def limit_search_input_text(self, text):
        """Giới hạn độ dài văn bản trong search_input để vừa với chiều rộng."""
        metrics = QFontMetrics(self.search_input.font())
        available_width = self.search_input.width() - 30  # 30px cho padding và các yếu tố khác
        if metrics.horizontalAdvance(text) > available_width:
            truncated = text
            while metrics.horizontalAdvance(truncated + "...") > available_width and len(truncated) > 1:
                truncated = truncated[:-1]
            self.search_input.lineEdit().setText(truncated + "...")
            
    def backup_restore(self):
        """Xử lý sao lưu và khôi phục danh sách menu."""
        try:
            dialog = BackupRestoreDialog(self)
            result = dialog.exec()

            if result == 1:
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Chọn nơi lưu file sao lưu",
                    "",
                    "JSON Files (*.json);;All Files (*)"
                )
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.menus, f, ensure_ascii=False, indent=4)
                    logger.debug(f"Đã sao lưu menu vào: {file_path}")
                    QMessageBox.information(self, "Thông báo", f"Đã sao lưu danh sách ghi chú vào:\n{file_path}")

            elif result == 2:
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Chọn file sao lưu để khôi phục",
                    "",
                    "JSON Files (*.json);;All Files (*)"
                )
                if file_path:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        restored_menus = json.load(f)
                    if not isinstance(restored_menus, list):
                        raise ValueError("File sao lưu không đúng định dạng!")
                    for menu in restored_menus:
                        if not all(key in menu for key in ['name', 'content']):
                            raise ValueError("File sao lưu không đúng định dạng!")
                    self.menus = restored_menus
                    self.save_menus()
                    self.populate_menu_lists()
                    logger.debug(f"Đã khôi phục menu từ: {file_path}")
                    QMessageBox.information(self, "Thông báo", f"Đã khôi phục danh sách ghi chú từ:\n{file_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Lỗi khi đọc file sao lưu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"File sao lưu không đúng định dạng JSON:\n{str(e)}")
        except ValueError as e:
            logger.error(f"Lỗi dữ liệu khi khôi phục: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Lỗi dữ liệu:\n{str(e)}")
        except Exception as e:
            logger.error(f"Lỗi khi sao lưu/khôi phục: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể sao lưu/khôi phục:\n{str(e)}")