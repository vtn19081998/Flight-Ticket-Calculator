import os
import sys
import re
import psutil
import win32event
import win32api
import win32gui
import win32process
from PyQt6.QtCore import Qt, QTimer, QEvent, QMimeData, QBuffer, QIODevice, QtMsgType, qInstallMessageHandler, QUrl
from PyQt6.QtGui import QIcon, QFont, QIntValidator, QDoubleValidator, QPixmap, QKeySequence, QShortcut, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QGridLayout, QCheckBox, QComboBox
)
from support_dialog import SupportDialog
from utils import setup_logging, qt_message_handler

# Thiết lập logging
setup_logging()
qInstallMessageHandler(qt_message_handler)

class TicketCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.price_multiplied = False
        self.is_round_trip = False
        self.detected_airlines = []
        self.discount_amount = 0

        # Tạo mutex
        self.mutex_name = "Flight_Ticket_Calculator_Mutex"
        self.mutex = win32event.CreateMutex(None, True, self.mutex_name)

        if not self.check_running_instances():
            win32api.CloseHandle(self.mutex)
            sys.exit(0)
        self.initUI()

    def __del__(self):
        """Giải phóng mutex khi đối tượng bị hủy."""
        try:
            if hasattr(self, 'mutex'):
                win32api.CloseHandle(self.mutex)
        except Exception:
            pass

    def get_window_titles(self):
        """Lấy danh sách cửa sổ với PID và tiêu đề."""
        window_data = {}
        def callback(hwnd, data):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and "flight ticket calculator" in title.lower():
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    data[pid] = title
        try:
            win32gui.EnumWindows(callback, window_data)
        except Exception:
            pass
        return window_data

    def check_running_instances(self):
        """
        Kiểm tra và ngăn các phiên bản trùng lặp (v4.0.1, v5.0.3).
        Trả về True nếu không có trùng lặp hoặc đóng thành công, False nếu người dùng từ chối.
        """
        current_pid = os.getpid()
        current_exe = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__).lower()
        current_exe_basename = os.path.basename(current_exe).lower()

        # Cache danh sách cửa sổ
        window_titles = self.get_window_titles()

        running = []
        proc_info = []
        for proc in psutil.process_iter(['pid', 'exe', 'name', 'cmdline']):
            try:
                proc_pid = proc.info['pid']
                if proc_pid == current_pid:
                    continue

                proc_exe = proc.info['exe'].lower() if proc.info['exe'] else ""
                proc_exe_basename = os.path.basename(proc_exe).lower() if proc_exe else ""
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                proc_cmdline = " ".join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ""

                if (proc_exe == current_exe or
                    "flight ticket calculator" in proc_exe_basename or
                    "flight ticket calculator" in proc_name or
                    "flight ticket calculator" in proc_cmdline):
                    if not proc_exe:
                        continue

                    window_title = window_titles.get(proc_pid, "")
                    if not window_title:
                        continue

                    running.append(proc)
                    proc_info.append(f"+ {window_title}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not running:
            return True

        proc_info_str = "\n".join(proc_info)
        msg = (
            f"Phát hiện các phiên bản khác đang chạy:\n\n"
            f"{proc_info_str}\n\n"
            f"Để đạt hiệu suất tốt nhất, chúng tôi khuyến cáo chỉ nên mở 1 cửa sổ ứng dụng. Bạn có muốn đóng các phiên này để tiếp tục mở phiên mới không?"
        )

        msg_box = QMessageBox()
        msg_box.setWindowTitle("CẢNH BÁO")
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowIcon(QIcon("images/icon.ico"))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            for proc in running:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except (psutil.TimeoutExpired, psutil.NoSuchProcess, psutil.AccessDenied):
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            still_running = [proc for proc in running if proc.is_running()]
            if still_running:
                QMessageBox.critical(self, "Lỗi", "Không thể đóng một số phiên bản. Vui lòng đóng thủ công.")
                return False
            return True
        return False

    def initUI(self):
        self.setWindowTitle("Flight Ticket Calculator v6.0.0 | Tác giả: Batman")
        self.setFixedWidth(580)
        self.setWindowIcon(QIcon('images/icon.ico'))

        self.setStyleSheet("""
            QWidget { background-color: #F5F6FA; font-family: Arial; }
            QLineEdit { border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px; background-color: white; }
            QLineEdit[readOnly="true"] { background-color: #E8ECEF; }
            QPushButton { border-radius: 5px; padding: 5px; font-weight: bold; color: white; }
            QLabel { color: #333333; background: transparent; }
            QGroupBox { font-weight: bold; border: 1px solid #CCCCCC; border-radius: 5px; margin-top: 10px; background-color: #E8ECEF; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; font-size: 12px; }
            QCheckBox:disabled { color: #888888; }
            QComboBox { border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px; background-color: white; font-size: 12px; }
            QComboBox QAbstractItemView { border: 1px solid #CCCCCC; background-color: white; selection-background-color: #4CAF50; selection-color: white; }
            QMessageBox QPushButton { background-color: #4CAF50; color: white; border: 1px solid #388E3C; padding: 5px; min-width: 60px; font-weight: normal; }
            QMessageBox QPushButton:hover { background-color: #45A049; }
        """)

        self.label_title = QLabel("VÉ MÁY BAY NỘI ĐỊA VÀ QUỐC TẾ")
        self.label_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        flight1_group = QGroupBox("Chuyến bay 1")
        flight1_grid = QGridLayout()
        flight1_grid.setSpacing(5)

        self.label_flight_number1 = QLabel()
        self.label_flight_number1.setFixedSize(60, 60)
        self.label_flight_number1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.input_flight1 = QLabel()
        self.input_flight1.setToolTip("Chỉ tự động nhập từ clipboard")
        self.input_flight1.setStyleSheet("background-color: #f5f6fa; font-weight: bold; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        self.label_time1 = QLabel("")
        self.input_time1 = QLabel()
        self.input_time1.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        self.input_flight_number1 = QLineEdit()
        self.input_flight_number1.setReadOnly(True)
        self.input_flight_number1.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        self.label_plane_type1 = QLabel("")
        self.input_plane_type1 = QLineEdit()
        self.input_plane_type1.setReadOnly(True)
        self.input_plane_type1.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        flight1_grid.addWidget(self.label_flight_number1, 0, 0, 2, 1)
        flight1_grid.addWidget(self.input_flight1, 0, 1)
        flight1_grid.addWidget(self.label_time1, 0, 2)
        flight1_grid.addWidget(self.input_time1, 0, 3)
        flight1_grid.addWidget(self.input_flight_number1, 1, 1)
        flight1_grid.addWidget(self.label_plane_type1, 1, 2)
        flight1_grid.addWidget(self.input_plane_type1, 1, 3)
        flight1_group.setLayout(flight1_grid)

        self.flight2_group = QGroupBox("Chuyến bay 2 (khứ hồi)")
        flight2_grid = QGridLayout()
        flight2_grid.setSpacing(5)

        self.label_flight_number2 = QLabel()
        self.label_flight_number2.setFixedSize(60, 60)
        self.label_flight_number2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.input_flight2 = QLabel()
        self.input_flight2.setToolTip("Chỉ tự động nhập từ clipboard")
        self.input_flight2.setStyleSheet("background-color: #f5f6fa; font-weight: bold; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        self.label_time2 = QLabel("")
        self.input_time2 = QLabel()
        self.input_time2.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        self.input_flight_number2 = QLineEdit()
        self.input_flight_number2.setReadOnly(True)
        self.input_flight_number2.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        self.label_plane_type2 = QLabel("")
        self.input_plane_type2 = QLineEdit()
        self.input_plane_type2.setReadOnly(True)
        self.input_plane_type2.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")

        flight2_grid.addWidget(self.label_flight_number2, 0, 0, 2, 1)
        flight2_grid.addWidget(self.input_flight2, 0, 1)
        flight2_grid.addWidget(self.label_time2, 0, 2)
        flight2_grid.addWidget(self.input_time2, 0, 3)
        flight2_grid.addWidget(self.input_flight_number2, 1, 1)
        flight2_grid.addWidget(self.label_plane_type2, 1, 2)
        flight2_grid.addWidget(self.input_plane_type2, 1, 3)
        self.flight2_group.setLayout(flight2_grid)
        self.flight2_group.setVisible(False)

        self.round_trip_checkbox = QCheckBox("Chuyến bay khứ hồi")
        self.round_trip_checkbox.setEnabled(False)
        self.round_trip_checkbox.stateChanged.connect(self.toggle_round_trip)

        passenger_group = QGroupBox("Hành khách và giá vé gốc")
        input_grid = QGridLayout()
        input_grid.setSpacing(5)

        self.label_price = QLabel("💰 Giá vé gốc (VNĐ):")
        self.input_price = QLineEdit()
        self.input_price.setValidator(QDoubleValidator(0.99, 99999999.99, 2))
        self.input_price.setToolTip("Nhập giá vé gốc, đơn vị 000 VNĐ")
        self.input_price.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.input_price.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        self.input_price.setReadOnly(True)
        self.input_price.textChanged.connect(self.format_price)
        self.input_price.returnPressed.connect(lambda: self.apply_multiplier(trigger_calculate=True))
        self.input_price.editingFinished.connect(lambda: self.apply_multiplier(trigger_calculate=False))

        self.label_discount = QLabel("🎟️ Voucher (%):")
        self.input_discount = QLineEdit()
        self.input_discount.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.input_discount.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        self.input_discount.setReadOnly(True)

        self.label_adult = QLabel("👨‍👩‍👧‍👦 Người lớn:")
        self.input_adult = QLineEdit()
        self.input_adult.setValidator(QIntValidator(0, 100))
        self.input_adult.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        self.input_adult.setReadOnly(True)

        self.label_child = QLabel("👶 Trẻ 2-11 tuổi:")
        self.input_child = QLineEdit()
        self.input_child.setValidator(QIntValidator(0, 100))
        self.input_child.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        self.input_child.setReadOnly(True)

        self.label_infant = QLabel("👶 Dưới 2 tuổi:")
        self.input_infant = QLineEdit()
        self.input_infant.setValidator(QIntValidator(0, 100))
        self.input_infant.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        self.input_infant.setReadOnly(True)

        self.label_export_format = QLabel("📄 Định dạng:")
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["Văn bản chi tiết", "Văn bản ngắn gọn", "Văn bản hành trình"])
        self.export_format_combo.setCurrentText("Văn bản chi tiết")
        self.export_format_combo.setToolTip("Chọn định dạng Xuất dữ liệu")
        self.export_format_combo.setStyleSheet("background-color: #f5f6fa; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px; font-size: 12px;")

        input_grid.addWidget(self.label_price, 0, 0)
        input_grid.addWidget(self.input_price, 0, 1)
        input_grid.addWidget(self.label_discount, 0, 2)
        input_grid.addWidget(self.input_discount, 0, 3)
        input_grid.addWidget(self.label_adult, 1, 0)
        input_grid.addWidget(self.input_adult, 1, 1)
        input_grid.addWidget(self.label_child, 1, 2)
        input_grid.addWidget(self.input_child, 1, 3)
        input_grid.addWidget(self.label_infant, 2, 0)
        input_grid.addWidget(self.input_infant, 2, 1)
        input_grid.addWidget(self.label_export_format, 2, 2)
        input_grid.addWidget(self.export_format_combo, 2, 3)
        passenger_group.setLayout(input_grid)

        self.button_container = QWidget()
        self.button_layout = QHBoxLayout()
        self.button_clear = QPushButton("🔄 Xóa trắng")
        self.button_clear.setStyleSheet("background-color: #4CAF50;")
        self.button_clear.clicked.connect(self.clear_fields)
        self.button_clear.setShortcut("F1")
        self.button_clear.setToolTip("Xóa tất cả dữ liệu (F1)")
        self.button_ocr = QPushButton("📋 Nhập liệu")
        self.button_ocr.setStyleSheet("background-color: #FF5722;")
        self.button_ocr.clicked.connect(self.extract_from_clipboard)
        self.button_ocr.setShortcut("F2")
        self.button_ocr.setToolTip("Nhập dữ liệu từ clipboard (F2)")
        self.button_calculate = QPushButton("📸 Chụp hình")
        self.button_calculate.setStyleSheet("background-color: #2196F3;")
        self.button_calculate.clicked.connect(self.calculate_total_and_capture)
        self.button_calculate.setShortcut("F3")
        self.button_calculate.setToolTip("Chụp ảnh màn hình (F3)")
        self.button_screenshot = QPushButton("📊 Xuất chữ")
        self.button_screenshot.setStyleSheet("background-color: #FF9800;")
        self.button_screenshot.clicked.connect(self.calculate_total_and_copy)
        self.button_screenshot.setShortcut("F4")
        self.button_screenshot.setToolTip("Xuất dữ liệu ra clipboard (F4)")
        self.button_payment = QPushButton("💳 Hóa đơn")
        self.button_payment.setStyleSheet("background-color: #E91E63;")
        self.button_payment.clicked.connect(self.open_payment_page)
        self.button_payment.setShortcut("F5")
        self.button_payment.setToolTip("Mở hóa đơn đặt vé (F5)")
        self.button_support = QPushButton("💬 Ghi chú")
        self.button_support.setStyleSheet("background-color: #673AB7;")
        self.button_support.clicked.connect(self.show_support_dialog)
        self.button_support.setShortcut("F6")
        self.button_support.setToolTip("Mở cửa sổ Ghi chú (F6)")

        self.button_layout.addWidget(self.button_clear)
        self.button_layout.addWidget(self.button_ocr)
        self.button_layout.addWidget(self.button_calculate)
        self.button_layout.addWidget(self.button_screenshot)
        self.button_layout.addWidget(self.button_payment)
        self.button_layout.addWidget(self.button_support)
        self.button_layout.setSpacing(10)
        self.button_container.setLayout(self.button_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["STT", "LOẠI VÉ", "SỐ LƯỢNG", "TIỀN 1 VÉ", "THÀNH TIỀN"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStyleSheet("background-color: #E8ECEF;")
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #CCCCCC; }
            QHeaderView::section { background-color: #E8ECEF; font-weight: bold; border: 1px solid #CCCCCC; }
        """)
        self.table.setRowCount(3)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 80)
        self.table.horizontalHeader().setMinimumHeight(30)
        self.table.horizontalHeader().setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.adjust_table_height()

        total_group = QGroupBox("Giá vé sau khuyến mãi")
        total_layout = QVBoxLayout()
        total_layout.setSpacing(5)
        total_layout.addWidget(self.table)
        total_group.setLayout(total_layout)

        self.result_label = QLineEdit()
        self.result_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("color: red; border-radius: 5px;")
        self.result_label.setReadOnly(True)
        self.result_label.setFixedHeight(40)

        note_group = QGroupBox("📝 Ghi chú")
        note_group.setStyleSheet("QGroupBox::title { color: red; }")
        note_layout = QVBoxLayout()
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet("font-family: Arial; font-size: 12px;")
        self.update_note_label([])

        note_layout.addWidget(self.note_label)
        note_group.setLayout(note_layout)

        self.copyright_label = QLabel("Kính chúc quý khách có 1 chuyến bay an toàn!")
        self.copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copyright_label.setFont(QFont("Times New Roman", 8, QFont.Weight.Bold))
        self.copyright_label.setStyleSheet("color: #3f3f3f;")

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.label_title)
        self.main_layout.addWidget(flight1_group)
        self.main_layout.addWidget(self.flight2_group)
        self.main_layout.addWidget(passenger_group)
        self.main_layout.addWidget(self.button_container)
        self.main_layout.addWidget(total_group)
        self.main_layout.addWidget(self.result_label)
        self.main_layout.addWidget(note_group)
        self.main_layout.addWidget(self.copyright_label)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.setLayout(self.main_layout)

        self.input_discount.setText("20")
        self.input_adult.setText("1")
        self.input_child.setText("0")
        self.input_infant.setText("0")

        self.input_price.installEventFilter(self)
        self.input_discount.installEventFilter(self)
        self.input_adult.installEventFilter(self)
        self.input_child.installEventFilter(self)
        self.input_infant.installEventFilter(self)

        self.shortcut_f6 = QShortcut(QKeySequence("F6"), self)
        self.shortcut_f6.activated.connect(self.edit_price)

        QTimer.singleShot(0, self.adjust_window_height)

    def open_payment_page(self):
        """Mở trang hóa đơn đặt vé trong trình duyệt mặc định."""
        if QApplication.activeModalWidget():
            return
        try:
            url = QUrl("https://vtn19081998.github.io/Flight-Ticket-Paygate")
            QDesktopServices.openUrl(url)
            QMessageBox.information(self, "Thành công", "Đã mở trang hóa đơn đặt vé trong trình duyệt!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở trang hóa đơn: {str(e)}")

    def show_support_dialog(self):
        """Hiển thị cửa sổ Hỗ trợ trả lời."""
        if QApplication.activeModalWidget():
            return
        try:
            dialog = SupportDialog(self)
            dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở cửa sổ hỗ trợ: {str(e)}")

    def eventFilter(self, obj, event):
        if QApplication.activeModalWidget():  # Bỏ qua nếu có dialog đang mở
            return super().eventFilter(obj, event)
        try:
            if event.type() == QEvent.Type.FocusIn and isinstance(obj, QLineEdit):
                obj.setReadOnly(False)
                if obj == self.input_price:
                    obj.clear()
                    self.price_multiplied = False
                return True
            elif event.type() == QEvent.Type.FocusOut and isinstance(obj, QLineEdit):
                obj.setReadOnly(True)
                if obj == self.input_price:
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def toggle_round_trip(self, state):
        self.is_round_trip = state == Qt.CheckState.Checked.value
        self.flight2_group.setVisible(self.is_round_trip)
        self.adjust_window_height()

    def adjust_table_height(self):
        self.table.resizeRowsToContents()
        header_height = self.table.horizontalHeader().height()
        total_height = header_height + sum(self.table.rowHeight(row) for row in range(self.table.rowCount())) + 2
        self.table.setFixedHeight(total_height)

    def adjust_window_height(self):
        self.adjustSize()

    def calculate_total_and_capture(self):
        if QApplication.activeModalWidget():
            return
        self.apply_multiplier(trigger_calculate=False)
        self.calculate_total()
        self.take_screenshot()

    def calculate_total_and_copy(self):
        if QApplication.activeModalWidget():
            return
        self.apply_multiplier(trigger_calculate=False)
        self.calculate_total()
        export_format = self.export_format_combo.currentText()
        self.copy_text(export_format)

    def take_screenshot(self):
        required_inputs = [
            self.input_price.text().strip(),
            self.input_discount.text().strip(),
            self.input_adult.text().strip(),
            self.input_child.text().strip(),
            self.input_infant.text().strip()
        ]
        if not all(required_inputs):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ tất cả các trường trước khi chụp ảnh màn hình.")
            return

        try:
            self.label_export_format.setVisible(False)
            self.export_format_combo.setVisible(False)
            self.button_container.setVisible(False)

            original_focus_policy = self.table.focusPolicy()
            self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.table.clearSelection()
            self.table.clearFocus()

            QApplication.processEvents()
            self.adjustSize()

            pixmap = QPixmap(self.size())
            self.render(pixmap)

            self.label_export_format.setVisible(True)
            self.export_format_combo.setVisible(True)
            self.button_container.setVisible(True)
            self.table.setFocusPolicy(original_focus_policy)

            QApplication.processEvents()
            self.adjustSize()

            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            QMessageBox.information(self, "Chụp ảnh màn hình", "Ảnh màn hình đã được sao chép vào clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể chụp ảnh màn hình: {str(e)}")
            self.label_export_format.setVisible(True)
            self.export_format_combo.setVisible(True)
            self.button_container.setVisible(True)
            self.table.setFocusPolicy(original_focus_policy)
            self.adjustSize()

    def copy_text(self, export_format="Văn bản chi tiết"):
        required_inputs = [
            self.input_price.text().strip(),
            self.input_discount.text().strip(),
            self.input_adult.text().strip(),
            self.input_child.text().strip(),
            self.input_infant.text().strip()
        ]
        if not all(required_inputs):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ tất cả các trường trước khi Xuất dữ liệu.")
            return

        try:
            # Lấy giá trị từ input
            voucher_value = int(self.input_discount.text().strip() or "0")
            base_fare_value = int(self.input_price.text().strip().replace(',', '')) if self.input_price.text().strip().replace(',', '').isdigit() else 0
            adult_count = int(self.input_adult.text())
            child_count = int(self.input_child.text())
            infant_count = int(self.input_infant.text())
            total_guests = adult_count + child_count + infant_count
            discount = voucher_value / 100
            adult_price = base_fare_value * (1 - discount)
            child_price = (base_fare_value * 0.7) * (1 - discount)

            # Xác định hãng bay
            possible_airlines = ["Vietjet Air", "Bamboo Airways", "Vietnam Airlines", "Vietravel Airlines", "Pacific Airlines"]
            airlines = []
            flight1_text = self.input_flight_number1.text().strip().upper()
            flight2_text = self.input_flight_number2.text().strip().upper()

            airline1 = next((airline for airline in possible_airlines if airline.upper() in flight1_text), "Không xác định")
            airlines.append(airline1)
            if self.is_round_trip and flight2_text:
                airline2 = next((airline for airline in possible_airlines if airline.upper() in flight2_text), "Không xác định")
                airlines.append(airline2)
            airline_name = airlines[0] if len(airlines) == 1 or airlines[0] == airlines[1] else ", ".join(airlines[:2])

            # Hàm tạo nội dung note chung
            def get_note_content(airlines):
                luggage_notes = {
                    "Vietjet Air": "được mang 7kg xách tay và 1 kiện 20kg hành lý ký gửi",
                    "Bamboo Airways": "được mang 7kg xách tay và 1 kiện 20kg hành lý ký gửi",
                    "Vietnam Airlines": "được mang 10kg xách tay và 1 kiện 23kg hành lý ký gửi",
                    "Vietravel Airlines": "được mang 7kg xách tay và 1 kiện 15kg hành lý ký gửi",
                    "Pacific Airlines": "được mang 7kg xách tay và 1 kiện 23kg hành lý ký gửi"
                }
                base_text = "Tổng giá vé đã bao gồm toàn bộ thuế phí"
                if "Vietnam Airlines" in airlines:
                    base_text += ", suất ăn"
                luggage1 = luggage_notes.get(airlines[0], "không có thông tin hành lý")
                luggage2 = luggage_notes.get(airlines[1] if len(airlines) > 1 else airlines[0], "không có thông tin hành lý")
                if len(airlines) == 1 or luggage1 == luggage2:
                    return f"{base_text}, {luggage1}"
                return f"{base_text}\n● Chuyến 1: Với mỗi vé, {luggage1}\n● Chuyến 2: Với mỗi vé, {luggage2}"

            # Xử lý định dạng văn bản
            trip_type = "khứ hồi" if self.is_round_trip else "1 chiều"
            note_content = get_note_content(airlines)

            if export_format == "Văn bản ngắn gọn":
                suffix = " khứ hồi" if self.is_round_trip else ""
                clipboard_content = (
                    f"Em gửi Anh/chị chuyến này của hãng {airline_name} và mã voucher giảm giá {voucher_value}% "
                    f"cho các chuyến bay Nội địa - Quốc tế\n\n"
                    f"● Giá vé sau khi áp mã voucher còn: {adult_price:,.0f} VNĐ/vé người lớn{suffix}\n"
                    f"● Vé trẻ em 2-11 tuổi: {child_price:,.0f} VNĐ\n"
                    f"\n{note_content}"
                )

            elif export_format == "Văn bản hành trình":
                def format_route(route_text):
                    clean_text = re.sub(r'<[^>]+>', '', route_text).strip()
                    clean_text = re.sub(r'\s*[-→]\s*|\s{2,}', ' > ', clean_text)
                    parts = clean_text.split(' > ')
                    return f"{parts[0].strip()} > {parts[1].strip()}" if len(parts) >= 2 else "Không xác định"

                def extract_time_and_date(time_text):
                    time_text = re.sub(r'<[^>]+>', '', time_text)
                    parts = time_text.split('|')
                    if len(parts) >= 3:
                        time_range = parts[2].strip()
                        date = parts[1].strip()
                        start_time = time_range.split('-')[0].strip() if '-' in time_range else "Không xác định"
                        return start_time, date
                    return "Không xác định", "Không xác định"

                flight1_text = format_route(self.input_flight1.text())
                flight2_text = format_route(self.input_flight2.text()) if self.is_round_trip else ""
                time1, date1 = extract_time_and_date(self.input_time1.text())
                time2, date2 = extract_time_and_date(self.input_time2.text()) if self.is_round_trip else ("", "")

                clipboard_content = (
                    f"Chuyến bay: {flight1_text} ({airline1})\n"
                    f"● Khởi hành: {time1} ngày {date1}\n"
                )
                if self.is_round_trip:
                    clipboard_content += (
                        f"Chuyến 2: {flight2_text} ({airlines[1] if len(airlines) > 1 else airline1})\n"
                        f"● Khởi hành: {time2} ngày {date2}\n"
                    )
                clipboard_content += (
                    f"\nGiá vé sau khi áp mã voucher giảm {voucher_value}%:\n"
                    f"● {adult_price:,.0f} VNĐ/người lớn\n● {child_price:,.0f} VNĐ/trẻ em 2-11 tuổi\n"
                    f"\n{note_content}"
                )

            else:  # Văn bản chi tiết
                intro_text = "Em gửi anh/chị bảng tính toán chi phí chuyến bay:\n\n"
                trip_text = f"● Đây là chuyến bay {trip_type}.\n"
                airline_text = f"● Hãng bay: {airline_name}.\n"
                base_fare_text = f"● Giá gốc: {base_fare_value:,.0f} VNĐ/vé\n"
                voucher_text = f"● Mã voucher khuyến mãi: {voucher_value}%\n"
                guest_text = f"● Tổng số khách: {total_guests}\n"
                after_voucher = "Chi phí sau khuyến mãi:\n"

                table_data = ""
                for row in range(self.table.rowCount()):
                    item_quantity = self.table.item(row, 2)
                    if item_quantity and item_quantity.text().isdigit() and int(item_quantity.text()) > 0:
                        item_name = self.table.item(row, 1).text().strip()
                        quantity = int(item_quantity.text())
                        price = float(self.table.item(row, 3).text().replace(" VNĐ", "").replace(",", "").strip()) if "Miễn phí" not in self.table.item(row, 3).text() else 0
                        total = float(self.table.item(row, 4).text().replace(" VNĐ", "").replace(",", "").strip())
                        formatted_line = f"● {item_name}: {quantity} x {price:,.0f} = {total:,.0f} VNĐ\n" if price > 0 else f"● {item_name}: {quantity} x Miễn phí = 0 VNĐ\n"
                        table_data += formatted_line

                total_cost = self.result_label.text().strip()
                discount_text = f"● Số tiền tiết kiệm được trong chuyến bay này là: {self.discount_amount:,.0f} VNĐ.\n"
                clipboard_content = f"{intro_text}{trip_text}{airline_text}{guest_text}{voucher_text}\n{after_voucher}{table_data}{total_cost}\n\n{note_content}"

            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_content)
            QMessageBox.information(self, "Sao chép nội dung", f"Nội dung định dạng '{export_format}' đã được sao chép vào clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra: {str(e)}")

    def calculate_total(self):
        try:
            price_text = self.input_price.text().replace(",", "").strip()
            if not price_text or float(price_text) <= 0:
                raise ValueError("Giá vé gốc phải lớn hơn 0.")
            price = float(price_text)
            discount_text = self.input_discount.text().strip()
            discount = float(discount_text) / 100 if discount_text else 0
            adult_text = self.input_adult.text().strip()
            adult_count = int(adult_text) if adult_text else 0
            child_text = self.input_child.text().strip()
            child_count = int(child_text) if child_text else 0
            infant_text = self.input_infant.text().strip()
            infant_count = int(infant_text) if infant_text else 0

            adult_original_price = price * adult_count
            child_original_price = (price * 0.7) * child_count
            original_price = adult_original_price + child_original_price

            adult_price = price * (1 - discount)
            child_price = (price * 0.7) * (1 - discount)
            total_adult = adult_price * adult_count
            total_child = child_price * child_count
            total_infant = 0
            total = total_adult + total_child + total_infant

            self.discount_amount = original_price - total
            self.result_label.setText(f"Tổng chi phí toàn hành trình: {total:,.0f} VNĐ")

            item_1 = QTableWidgetItem("1")
            item_1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(0, 0, item_1)
            self.table.setItem(0, 1, QTableWidgetItem("Người lớn"))
            item_2 = QTableWidgetItem(str(adult_count))
            item_2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(0, 2, item_2)
            self.table.setItem(0, 3, QTableWidgetItem(f"{adult_price:,.0f} VNĐ"))
            self.table.setItem(0, 4, QTableWidgetItem(f"{total_adult:,.0f} VNĐ"))

            item_4 = QTableWidgetItem("2")
            item_4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(1, 0, item_4)
            self.table.setItem(1, 1, QTableWidgetItem("Trẻ em 2-11 tuổi"))
            item_5 = QTableWidgetItem(str(child_count))
            item_5.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(1, 2, item_5)
            self.table.setItem(1, 3, QTableWidgetItem(f"{child_price:,.0f} VNĐ"))
            self.table.setItem(1, 4, QTableWidgetItem(f"{total_child:,.0f} VNĐ"))

            item_7 = QTableWidgetItem("3")
            item_7.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(2, 0, item_7)
            self.table.setItem(2, 1, QTableWidgetItem("Trẻ em dưới 2 tuổi"))
            item_8 = QTableWidgetItem(str(infant_count))
            item_8.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(2, 2, item_8)
            self.table.setItem(2, 3, QTableWidgetItem("Miễn phí"))
            self.table.setItem(2, 4, QTableWidgetItem("0 VNĐ"))

            self.update_note_label(self.detected_airlines)
            self.adjust_table_height()
        except ValueError as e:
            QMessageBox.warning(self, "Lỗi nhập liệu", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tính toán: {str(e)}")

    def clear_fields(self):
        if QApplication.activeModalWidget():
            return
        try:
            self.input_price.clear()
            self.input_discount.clear()
            self.input_adult.clear()
            self.input_child.clear()
            self.input_infant.clear()
            self.input_flight1.setText("")
            self.input_time1.setText("")
            self.label_flight_number1.clear()
            self.input_flight_number1.clear()
            self.input_plane_type1.clear()
            self.input_flight2.setText("")
            self.input_time2.setText("")
            self.label_flight_number2.clear()
            self.input_flight_number2.clear()
            self.input_plane_type2.clear()
            self.table.clearContents()
            self.result_label.clear()
            self.discount_amount = 0

            self.input_discount.setText("20")
            self.input_adult.setText("1")
            self.input_child.setText("0")
            self.input_infant.setText("0")

            self.update_note_label(self.detected_airlines)
            self.adjust_table_height()
            self.adjust_window_height()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi xóa dữ liệu: {str(e)}")

    def format_price(self):
        if QApplication.activeModalWidget():
            return
        price_text = self.input_price.text().replace(",", "").strip()
        try:
            if price_text:
                price = float(price_text)
                formatted_price = "{:,.0f}".format(price)
                self.input_price.setText(formatted_price)
                self.input_price.setCursorPosition(len(formatted_price))
        except ValueError:
            pass

    def apply_multiplier(self, trigger_calculate=True):
        if QApplication.activeModalWidget():
            return
        price_text = self.input_price.text().replace(",", "").strip()
        try:
            if price_text:
                price = float(price_text)
                if not self.price_multiplied:
                    price *= 1000
                    self.price_multiplied = True
                formatted_price = "{:,.0f}".format(price)
                self.input_price.setText(formatted_price)
                if trigger_calculate:
                    self.calculate_total()
        except ValueError:
            pass

    def update_note_label(self, detected_airlines):
        notes = {
            "Vietjet Air": "● Với mỗi vé Vietjet Air, được mang theo 7kg hành lý xách tay và 1 kiện 20kg hành lý ký gửi",
            "Bamboo Airways": "● Với mỗi vé Bamboo Airways, được mang theo 7kg hành lý xách tay và 1 kiện 20kg hành lý ký gửi",
            "Vietnam Airlines": "● Với mỗi vé Vietnam Airlines, được mang theo 10kg hành lý xách tay và 1 kiện 23kg hành lý ký gửi",
            "Vietravel Airlines": "● Với mỗi của Vietravel Airlines, được mang theo 7kg hành lý xách tay và 1 kiện 15kg hành lý ký gửi",
            "Pacific Airlines": "● Với mỗi vé Pacific Airlines, được mang theo 7kg hành lý xách tay và 1 kiện 23kg hành lý ký gửi"
        }

        discount_text = f"<span style='color:red'>Số tiền tiết kiệm được trong chuyến bay này là: {self.discount_amount:,.0f} VNĐ.</span><br>"
        base_text = "Tổng giá vé đã bao gồm toàn bộ thuế, phí" + (", suất ăn" if "Vietnam Airlines" in detected_airlines else "") + ".<br>"

        note_text = discount_text + base_text
        for airline in detected_airlines:
            if airline in notes:
                note_text += notes[airline] + "<br>"
        self.note_label.setText(note_text.rstrip("<br>"))

    def extract_from_clipboard(self):
        if QApplication.activeModalWidget():
            return
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if not text:
                QMessageBox.warning(self, "Lỗi", "Clipboard không chứa văn bản!")
                return

            text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
            normalized_text = " ".join(text.split()).lower()

            price_pattern = r'\d{1,3}(?:[.,]\d{3})*(?:\.\d{2})?'
            prices = re.findall(price_pattern, text)
            if prices:
                max_price = max(float(p.replace(',', '').replace('.', '')) for p in prices)
                self.input_price.setText("{:,.0f}".format(max_price))
                self.price_multiplied = True

            airlines = ["Vietjet Air", "Bamboo Airways", "Vietnam Airlines", "Vietravel Airlines", "Pacific Airlines"]
            self.detected_airlines = [airline for airline in airlines if " ".join(airline.split()).lower() in normalized_text]
            self.update_note_label(self.detected_airlines)

            logo_paths = {
                "Vietjet Air": "images/vietjet.png",
                "Bamboo Airways": "images/bamboo.png",
                "Vietnam Airlines": "images/vna.png",
                "Vietravel Airlines": "images/vietravel.png",
                "Pacific Airlines": "images/pacific.png"
            }

            # Cập nhật route_pattern để bỏ qua (T\d)
            route_pattern = r'(hà nội|tp hồ chí minh|đà nẵng|nha trang|hải phòng|phú quốc|đà lạt|cần thơ|quy nhơn|thanh hóa|thanh hoá|vinh|tp vinh|huế|điện biên|quảng ninh|buôn mê thuột|pleiku|tuy hòa|tuy hoà|côn đảo|rạch giá|đồng hới|tam kỳ|cà mau)(?:\s*\(t\d\))?\s+(hà nội|tp hồ chí minh|đà nẵng|nha trang|hải phòng|phú quốc|đà lạt|cần thơ|quy nhơn|thanh hóa|thanh hoá|vinh|tp vinh|huế|điện biên|quảng ninh|buôn mê thuột|pleiku|tuy hòa|tuy hoà|côn đảo|rạch giá|đồng hới|tam kỳ|cà mau)(?:\s*\(t\d\))?'
            routes = re.findall(route_pattern, normalized_text)

            flight_pattern = r'(vietjet air|bamboo airways|vietnam airlines|vietravel airlines|pacific airlines)\s+(vj|vn|qh|vu|bl)\s*(\d{2,4})'
            flight_matches = re.findall(flight_pattern, text, re.IGNORECASE)

            self.is_round_trip = len(routes) >= 2 or len(flight_matches) >= 2
            self.round_trip_checkbox.setChecked(self.is_round_trip)
            self.flight2_group.setVisible(self.is_round_trip)

            # Hàm loại bỏ (T\d) khỏi tên thành phố
            def clean_city_name(city):
                return re.sub(r'\s*\(t\d\)', '', city).strip()

            if routes:
                # Làm sạch tên thành phố trước khi hiển thị
                departure_city1 = clean_city_name(routes[0][0])
                arrival_city1 = clean_city_name(routes[0][1])
                self.input_flight1.setText(
                    f"<span>{departure_city1.upper()}</span> <img src='images/arrow.png' width='11'> <span>{arrival_city1.upper()}</span>"
                )
                if len(routes) > 1 and self.is_round_trip:
                    departure_city2 = clean_city_name(routes[1][0])
                    arrival_city2 = clean_city_name(routes[1][1])
                    self.input_flight2.setText(
                        f"<span>{departure_city2.upper()}</span> <img src='images/arrow.png' width='11'> <span>{arrival_city2.upper()}</span>"
                    )

            day_map = {
                'thứ hai': 'THỨ HAI', 'thứ ba': 'THỨ BA', 'thứ tư': 'THỨ TƯ', 'thứ năm': 'THỨ NĂM',
                'thứ sáu': 'THỨ SÁU', 'thứ bảy': 'THỨ BẢY', 'chủ nhật': 'CHỦ NHẬT'
            }
            day_pattern = r'(thứ\s*(?:hai|ba|tư|năm|sáu|bảy)|chủ nhật)'
            date_pattern = r'(\d{1,2}/\d{1,2})'
            time_range_pattern = r'(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})'
            days = [day_map.get(d.strip(), d.strip().upper()) for d in re.findall(day_pattern, text.lower())]
            dates = re.findall(date_pattern, text)
            time_ranges = re.findall(time_range_pattern, text)

            if days:
                date1 = dates[0].upper() if dates else ''
                time_range1 = time_ranges[0].upper() if time_ranges else ''
                time_start1 = time_range1.split('-')[0].strip() if time_range1 else ''
                time_end1 = time_range1.split('-')[1].strip() if time_range1 and '-' in time_range1 else ''
                formatted_time1 = f"{days[0]} | <b>{date1}</b> | <b>{time_start1}</b> - {time_end1}"
                self.input_time1.setText(formatted_time1)

                if self.is_round_trip and len(days) > 1:
                    date2 = dates[1].upper() if len(dates) > 1 else ''
                    time_range2 = time_ranges[1].upper() if len(time_ranges) > 1 else ''
                    time_start2 = time_range2.split('-')[0].strip() if time_range2 else ''
                    time_end2 = time_range2.split('-')[1].strip() if time_range2 and '-' in time_range2 else ''
                    formatted_time2 = f"{days[1]} | <b>{date2}</b> | <b>{time_start2}</b> - {time_end2}"
                    self.input_time2.setText(formatted_time2)

            if flight_matches:
                if len(flight_matches) >= 1:
                    airline1 = flight_matches[0][0].title()
                    flight_num1 = f"{flight_matches[0][1]}{flight_matches[0][2]}"
                    self.input_flight_number1.setText(f"{airline1.upper()} | {flight_num1.upper()}")
                    for airline, logo_path in logo_paths.items():
                        if airline.upper() in self.input_flight_number1.text():
                            pixmap1 = QPixmap(logo_path)
                            if not pixmap1.isNull():
                                self.label_flight_number1.setPixmap(pixmap1.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio))
                            else:
                                self.label_flight_number1.setText("❓")
                            break
                    else:
                        self.label_flight_number1.setText("❓")

                if len(flight_matches) >= 2 and self.is_round_trip:
                    airline2 = flight_matches[1][0].title()
                    flight_num2 = f"{flight_matches[1][1]}{flight_matches[1][2]}"
                    self.input_flight_number2.setText(f"{airline2.upper()} | {flight_num2.upper()}")
                    for airline, logo_path in logo_paths.items():
                        if airline.upper() in self.input_flight_number2.text():
                            pixmap2 = QPixmap(logo_path)
                            if not pixmap2.isNull():
                                self.label_flight_number2.setPixmap(pixmap2.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio))
                            else:
                                self.label_flight_number2.setText("❓")
                            break
                    else:
                        self.label_flight_number2.setText("❓")

            plane_type_pattern = r'(a\d{2,3}|boeing\s*\d{3}|airbus\s*a\d{2,3})'
            plane_types = re.findall(plane_type_pattern, normalized_text)
            if plane_types:
                plane_type1 = plane_types[0].upper()
                if "airbus" in normalized_text and "AIRBUS" not in plane_type1:
                    plane_type1 = f"AIRBUS {plane_type1}"
                self.input_plane_type1.setText(plane_type1)
                if len(plane_types) > 1 and self.is_round_trip:
                    plane_type2 = plane_types[1].upper()
                    if "airbus" in normalized_text and "AIRBUS" not in plane_type2:
                        plane_type2 = f"AIRBUS {plane_type2}"
                    self.input_plane_type2.setText(plane_type2)

            self.calculate_total()
            QMessageBox.information(self, "Thành công", "Đã nhận dạng và điền dữ liệu từ văn bản!")
            self.adjust_window_height()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể nhận dạng: {str(e)}")

    def edit_price(self):
        if QApplication.activeModalWidget():
            return
        try:
            self.input_price.setReadOnly(False)
            self.input_price.clear()
            self.input_price.setFocus()
            self.price_multiplied = False
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi chỉnh sửa giá: {str(e)}")

if __name__ == "__main__":
    app = QApplication([])
    window = TicketCalculator()
    window.show()
    app.exec()
