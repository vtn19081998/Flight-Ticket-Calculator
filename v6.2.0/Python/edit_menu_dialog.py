import os
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QLineEdit, QMessageBox, QApplication, QHBoxLayout
)

class SafeTextEdit(QPlainTextEdit):
    """Custom QTextEdit để giới hạn kích thước văn bản."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_text_length = 10000  # Giới hạn độ dài văn bản
        self.setMinimumHeight(300)  # Đặt chiều cao tối thiểu 300px cho ô nhập nội dung
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Tắt thanh cuộn ngang
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # Hiển thị thanh cuộn dọc khi cần

    def insertFromMimeData(self, source):
        """Xử lý dữ liệu từ clipboard (chỉ văn bản)."""
        try:
            if source.hasText():
                current_length = len(self.toPlainText())
                text_to_insert = source.text()[:self.max_text_length - current_length]
                if len(text_to_insert) < len(source.text()):
                    QMessageBox.warning(self, "Cảnh báo", "Nội dung dán đã bị cắt ngắn do vượt quá giới hạn 10,000 ký tự!")
                self.insertPlainText(text_to_insert)
            else:
                QMessageBox.warning(self, "Cảnh báo", "Chỉ hỗ trợ dán văn bản!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", "Không thể dán dữ liệu: Định dạng không được hỗ trợ!")

    def keyPressEvent(self, event):
        """Giới hạn độ dài văn bản khi nhập từ bàn phím."""
        if len(self.toPlainText()) >= self.max_text_length and event.key() not in (
            Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Left, Qt.Key.Key_Right,
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Control
        ):
            return
        super().keyPressEvent(event)
        # Cập nhật chiều cao cửa sổ khi nhập liệu
        if self.parent():
            self.parent().adjust_window_height()

class EditMenuDialog(QDialog):
    def __init__(self, parent=None, menu_name="", menu_content="", images=None, title="Chỉnh sửa ghi chú"):
        super().__init__(parent)
        self.setWindowTitle(title)
        parent_width = parent.width() if parent else 550
        self.setMinimumWidth(parent_width)
        self.min_height = 300
        self.max_height = 800
        self.initUI(menu_name, menu_content)
        # Trì hoãn việc điều chỉnh chiều cao và vị trí để đảm bảo giao diện đã render
        QTimer.singleShot(0, lambda: self.position_dialog(parent))
        QTimer.singleShot(0, self.adjust_window_height)

    def position_dialog(self, parent):
        """Đặt vị trí của dialog: căn giữa theo chiều ngang, căn trên theo chiều dọc so với parent."""
        try:
            if parent:
                parent_rect = parent.geometry()
                dialog_rect = self.geometry()
                # Căn giữa theo chiều ngang
                dialog_x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
                # Căn trên theo chiều dọc, cộng thêm offset 30px
                dialog_y = parent_rect.y() + 30
                self.move(dialog_x, dialog_y)
        except Exception:
            pass  # Bỏ qua nếu có lỗi

    def initUI(self, menu_name, menu_content):
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập tên ghi chú (tối đa 60 ký tự)...")
        self.name_input.setText(menu_name)
        self.name_input.setMaxLength(60)  # Giới hạn độ dài tên menu
        self.name_input.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        self.name_input.textChanged.connect(self.adjust_window_height)  # Cập nhật chiều cao khi nhập tên
        layout.addWidget(QLabel("Tên ghi chú:"))
        layout.addWidget(self.name_input)
        layout.addSpacing(10)  # Thêm khoảng cách

        self.content_input = SafeTextEdit(self)  # Truyền self làm parent để gọi adjust_window_height
        self.content_input.setPlaceholderText("Nhập nội dung (hỗ trợ ký tự Unicode và xuống dòng)...")
        self.content_input.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #CCCCCC; 
                border-radius: 5px; 
                padding: 5px;
            }
            QPlainTextEdit QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 10px;
                margin: 0px 0px 0px 0px;
                border-radius: 5px;
            }
            QPlainTextEdit QScrollBar::handle:vertical {
                background: #4CAF50;
                min-height: 20px;
                border-radius: 5px;
            }
            QPlainTextEdit QScrollBar::handle:vertical:hover {
                background: #66BB6A;
            }
            QPlainTextEdit QScrollBar::handle:vertical:pressed {
                background: #388E3C;
            }
            QPlainTextEdit QScrollBar::add-line:vertical {
                height: 0px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QPlainTextEdit QScrollBar::sub-line:vertical {
                height: 0px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            QPlainTextEdit QScrollBar::add-page:vertical, QPlainTextEdit QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        try:
            self.set_content(menu_content)
        except Exception:
            self.content_input.setPlainText("Lỗi tải nội dung, vui lòng thử lại.")
        layout.addWidget(QLabel("Nội dung (văn bản):"))
        layout.addWidget(self.content_input)
        layout.addSpacing(10)  # Thêm khoảng cách

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
        save_button.setToolTip("Lưu ghi chú (Ctrl+S)")
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

    def set_content(self, content):
        """Đặt nội dung plain text cho QPlainTextEdit."""
        try:
            self.content_input.setPlainText(content)
            QTimer.singleShot(0, self.adjust_window_height)
        except Exception:
            raise

    def adjust_window_height(self):
        """Điều chỉnh chiều cao cửa sổ dựa trên nội dung."""
        try:
            # Tính chiều cao các thành phần
            name_height = self.name_input.sizeHint().height() + 30  # Chừa khoảng trống cho label và margin

            # Tính chiều cao nội dung dựa trên số dòng và kích thước font
            content_doc = self.content_input.document()
            font_metrics = self.content_input.fontMetrics()
            line_count = content_doc.lineCount()
            line_height = font_metrics.lineSpacing()
            content_height = line_count * line_height + 20  # Thêm padding nhỏ

            button_height = 60  # Ước tính chiều cao nút và layout
            spacing = 40  # Tổng khoảng cách giữa các thành phần (bao gồm các addSpacing)

            # Đảm bảo content_height phù hợp để total_height đạt tối thiểu 300px
            min_content_height = self.min_height - (name_height + button_height + spacing)
            content_height = max(content_height, min_content_height)

            # Tính tổng chiều cao
            total_height = name_height + content_height + button_height + spacing
            total_height = max(self.min_height, min(total_height, self.max_height))

            # Nếu nội dung dài hơn max_height, giới hạn chiều cao của QTextEdit và hiển thị thanh cuộn
            max_content_height = self.max_height - (name_height + button_height + spacing)
            self.content_input.setFixedHeight(min(content_height, max_content_height))

            self.setFixedHeight(total_height)
        except Exception:
            self.setFixedHeight(self.min_height)  # Mặc định về chiều cao tối thiểu nếu có lỗi
    def get_data(self):
        """Lấy dữ liệu từ dialog."""
        try:
            menu_name = self.name_input.text().strip()
            if not menu_name:
                QMessageBox.warning(self, "Cảnh báo", "Tên ghi chú không được để trống!")
                return "", ""
            if len(menu_name) > 60:
                QMessageBox.warning(self, "Cảnh báo", "Tên ghi chú không được dài quá 60 ký tự!")
                return "", ""

            content = self.content_input.toPlainText().strip()
            if not content:
                QMessageBox.warning(self, "Cảnh báo", "Nội dung ghi chú không được để trống!")
                return "", ""
            if len(content) > self.content_input.max_text_length:
                content = content[:self.content_input.max_text_length]
            return menu_name, content
        except Exception:
            QMessageBox.critical(self, "Lỗi", "Không thể lưu dữ liệu: Dữ liệu không hợp lệ!")
            return "", ""