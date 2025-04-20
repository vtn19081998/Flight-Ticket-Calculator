import re
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QIcon, QTextCursor, QKeySequence
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QMessageBox, QApplication, QHBoxLayout
)
from utils import get_logger

logger = get_logger()

class SafeTextEdit(QTextEdit):
    """Custom QTextEdit để giới hạn kích thước văn bản."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_text_length = 10000  # Giới hạn độ dài văn bản

    def insertFromMimeData(self, source):
        """Xử lý dữ liệu từ clipboard (chỉ văn bản)."""
        try:
            if source.hasText():
                current_length = len(self.toPlainText())
                text_to_insert = source.text()[:self.max_text_length - current_length]
                if len(text_to_insert) < len(source.text()):
                    logger.warning(f"Văn bản dán bị cắt ngắn: từ {len(source.text())} xuống {len(text_to_insert)} ký tự")
                self.insertPlainText(text_to_insert)
                logger.debug(f"Đã dán văn bản: {text_to_insert[:80]}...")
            else:
                logger.warning("Dữ liệu dán không phải văn bản")
                QMessageBox.warning(self, "Cảnh báo", "Chỉ hỗ trợ dán văn bản!")
        except Exception as e:
            logger.error(f"Lỗi khi dán dữ liệu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", "Không thể dán dữ liệu: Định dạng không được hỗ trợ!")

    def keyPressEvent(self, event):
        """Giới hạn độ dài văn bản khi nhập từ bàn phím."""
        if len(self.toPlainText()) >= self.max_text_length and event.key() not in (
            Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Left, Qt.Key.Key_Right,
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Control
        ):
            logger.debug("Đã chặn nhập liệu do vượt giới hạn văn bản")
            return
        super().keyPressEvent(event)

class EditMenuDialog(QDialog):
    def __init__(self, parent=None, menu_name="", menu_content="", images=None, title="Chỉnh sửa Menu"):
        super().__init__(parent)
        logger.debug(f"Khởi tạo EditMenuDialog với menu_name: {menu_name}")
        self.setWindowTitle(title)
        parent_width = parent.width() if parent else 550
        self.setFixedSize(parent_width, 400)
        if parent:
            parent_rect = parent.geometry()
            self.move(
                parent_rect.x() + (parent_rect.width() - parent_width) // 2,
                parent_rect.y() + (parent_rect.height() - 400) // 2
            )
        try:
            self.setWindowIcon(QIcon('images/icon.ico'))
        except Exception as e:
            logger.error(f"Không thể tải icon: {str(e)}")
        self.initUI(menu_name, menu_content)

    def initUI(self, menu_name, menu_content):
        logger.debug("Khởi tạo giao diện EditMenuDialog")
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập tên menu (tối đa 60 ký tự)...")
        self.name_input.setText(menu_name)
        self.name_input.setMaxLength(60)  # Giới hạn độ dài tên menu
        self.name_input.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        layout.addWidget(QLabel("Tên menu:"))
        layout.addWidget(self.name_input)

        self.content_input = SafeTextEdit()
        self.content_input.setPlaceholderText("Nhập nội dung (chỉ văn bản)...")
        self.content_input.setAcceptRichText(True)
        self.content_input.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 5px; padding: 5px;")
        try:
            self.set_content(menu_content)
        except Exception as e:
            logger.error(f"Lỗi khi set nội dung QTextEdit: {str(e)}")
            self.content_input.setPlainText("Lỗi tải nội dung, vui lòng thử lại.")
        layout.addWidget(QLabel("Nội dung (văn bản):"))
        layout.addWidget(self.content_input)

        button_layout = QHBoxLayout()
        save_button = QPushButton("💾 Lưu")
        save_button.setStyleSheet("""
            background-color: #4CAF50; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #388E3C;
            font-weight: bold;
        """)
        save_button.setToolTip("Lưu menu (Ctrl+S)")
        save_button.clicked.connect(self.accept)
        save_button.setShortcut(QKeySequence("Ctrl+S"))  # Phím tắt Ctrl+S

        cancel_button = QPushButton("❌ Hủy")
        cancel_button.setStyleSheet("""
            background-color: #F44336; 
            color: white; 
            border-radius: 5px; 
            padding: 5px;
            border: 1px solid #D32F2F;
            font-weight: bold;
        """)
        cancel_button.setToolTip("Hủy (Esc)")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        logger.debug("Hoàn tất khởi tạo giao diện EditMenuDialog")

    def set_content(self, html_content):
        """Đặt nội dung HTML cho QTextEdit."""
        try:
            self.content_input.setHtml(html_content)
            logger.debug("Đã thiết lập nội dung văn bản")
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập nội dung: {str(e)}")
            raise

    def get_data(self):
        """Lấy dữ liệu từ dialog."""
        try:
            menu_name = self.name_input.text().strip()
            if not menu_name:
                QMessageBox.warning(self, "Cảnh báo", "Tên menu không được để trống!")
                logger.warning("Tên menu trống khi lưu")
                return "", ""
            if len(menu_name) > 60:
                QMessageBox.warning(self, "Cảnh báo", "Tên menu không được dài quá 60 ký tự!")
                logger.warning(f"Tên menu quá dài: {len(menu_name)} ký tự")
                return "", ""

            html_content = self.content_input.toHtml()
            if len(html_content) > self.content_input.max_text_length:
                html_content = html_content[:self.content_input.max_text_length]
                logger.warning("Nội dung HTML bị cắt do vượt giới hạn")
            logger.debug(f"Lấy dữ liệu: menu_name={menu_name}, len(html_content)={len(html_content)}")
            return menu_name, html_content
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu: {str(e)}")
            QMessageBox.critical(self, "Lỗi", "Không thể lưu dữ liệu: Dữ liệu không hợp lệ!")
            return "", ""