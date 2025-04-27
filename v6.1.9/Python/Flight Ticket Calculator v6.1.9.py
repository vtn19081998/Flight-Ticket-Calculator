import os
import sys
import json
import portalocker
from PyQt6.QtCore import Qt, QTimer, QEvent, QMimeData, QBuffer, QIODevice, QUrl
from PyQt6.QtGui import QIcon, QFont, QIntValidator, QDoubleValidator, QPixmap, QKeySequence, QShortcut, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QGridLayout, QCheckBox, QComboBox
)
from support_dialog import SupportDialog
from updater import Updater, UpdateManager
from input_processor import InputProcessor
from text_exporter import TextExporter

class TicketCalculator(QWidget):
    CURRENT_VERSION = "6.1.9"

    def __init__(self):
        super().__init__()
        self.price_multiplied = False
        self.is_round_trip = False
        self.detected_airlines = []
        self.discount_amount = 0
        self.child_price_ratio = 0.7

        self.load_config()

        documents_path = os.path.join(os.path.expanduser("~"), "Documents", "Flight Ticket Calculator")
        os.makedirs(documents_path, exist_ok=True)

        self.lock_file = os.path.join(documents_path, "flight_ticket_calculator.lock")
        self.lock = open(self.lock_file, 'a')
        try:
            portalocker.lock(self.lock, portalocker.LOCK_EX | portalocker.LOCK_NB)
        except portalocker.LockException:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("LỖI")
            msg_box.setText("Một phiên bản của Flight Ticket Calculator đang chạy.\nVui lòng đóng phiên bản hiện tại trước khi mở phiên bản mới.")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowIcon(QIcon("images/icon.ico"))
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
            msg_box.exec()
            self.lock.close()
            sys.exit(1)

        self.input_processor = InputProcessor(self.airlines_config)
        self.text_exporter = TextExporter(self.airlines_config)
        self.initUI()

        self.show()
        self.raise_()
        self.activateWindow()

        QTimer.singleShot(0, self.check_for_update)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_for_update)
        self.update_timer.start(600000)

    def __del__(self):
        try:
            if hasattr(self, 'lock'):
                portalocker.unlock(self.lock)
                self.lock.close()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            if hasattr(self, 'lock'):
                portalocker.unlock(self.lock)
                self.lock.close()
        except Exception:
            pass
        event.accept()

    def load_config(self):
        try:
            with open('data/airlines_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.airlines_config = {
                    airline['name']: {
                        'code': airline.get('code', ''),
                        'logo': airline.get('logo', ''),
                        'luggage': airline.get('luggage', 'không có thông tin hành lý'),
                        'meal': airline.get('meal', False)
                    } for airline in config.get('airlines', [])
                }
                self.child_price_ratio = config.get('child_price_ratio', 0.7)
        except FileNotFoundError:
            QMessageBox.critical(self, "Lỗi", "Không tìm thấy file airlines_config.json")
            sys.exit(1)
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Lỗi", "File airlines_config.json không hợp lệ")
            sys.exit(1)

    def check_for_update(self):
        if QApplication.activeModalWidget():
            return
        try:
            has_update, version_info = UpdateManager.check_for_update(self.CURRENT_VERSION)
            if has_update:
                Updater.prompt_for_update(version_info, self)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Lỗi kiểm tra cập nhật: {str(e)}")

    def initUI(self):
        self.setWindowTitle(f"Flight Ticket Calculator v{self.CURRENT_VERSION} | Tác giả: Batman")
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
        if QApplication.activeModalWidget():
            return
        try:
            url = QUrl("https://vtn19081998.github.io/Flight-Ticket-Paygate")
            QDesktopServices.openUrl(url)
            QMessageBox.information(self, "Thành công", "Đã mở trang hóa đơn đặt vé trong trình duyệt!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở trang hóa đơn: {str(e)}")

    def show_support_dialog(self):
        try:
            if QApplication.activeModalWidget():
                return
            if SupportDialog._instance is not None:
                try:
                    if not SupportDialog._instance.isVisible():
                        SupportDialog._instance.show()
                        SupportDialog._instance.raise_()
                        SupportDialog._instance.activateWindow()
                    else:
                        SupportDialog._instance.raise_()
                        SupportDialog._instance.activateWindow()
                except RuntimeError:
                    SupportDialog._instance = None
            if SupportDialog._instance is None:
                dialog = SupportDialog(self)
                dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở cửa sổ Ghi chú: {str(e)}")

    def eventFilter(self, obj, event):
        if QApplication.activeModalWidget():
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
        self.text_exporter.copy_text(
            export_format, self.input_price.text(), self.input_discount.text(),
            self.input_adult.text(), self.input_child.text(), self.input_infant.text(),
            self.input_flight1.text(), self.input_time1.text(),
            self.input_flight_number1.text(), self.input_flight2.text(),
            self.input_time2.text(), self.input_flight_number2.text(),
            self.is_round_trip, self.table, self.result_label.text(),
            self.discount_amount, self.detected_airlines
        )

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
            child_original_price = (price * self.child_price_ratio) * child_count
            original_price = adult_original_price + child_original_price

            adult_price = price * (1 - discount)
            child_price = (price * self.child_price_ratio) * (1 - discount)
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
        discount_text = f"<span style='color:red'>Số tiền tiết kiệm được trong chuyến bay này là: {self.discount_amount:,.0f} VNĐ.</span><br>"
        
        flight_number1 = self.input_flight_number1.text().strip()
        flight_number2 = self.input_flight_number2.text().strip()
        has_flight_data = bool(flight_number1) or bool(flight_number2)

        if not has_flight_data:
            base_text = "Tổng giá vé đã bao gồm toàn bộ thuế, phí.<br>"
            note_text = discount_text + base_text
            self.note_label.setText(note_text.rstrip("<br>"))
            return

        airline1 = None
        airline2 = None
        for airline, config in self.airlines_config.items():
            if flight_number1.upper().startswith(config.get('code', '').upper()):
                airline1 = airline
            if self.is_round_trip and flight_number2.upper().startswith(config.get('code', '').upper()):
                airline2 = airline

        if not airline1 and detected_airlines:
            airline1 = detected_airlines[0] if detected_airlines else None
        if self.is_round_trip and not airline2 and len(detected_airlines) > 1:
            airline2 = detected_airlines[1] if len(detected_airlines) > 1 else None

        has_meal = False
        if airline1 and self.airlines_config.get(airline1, {}).get('meal', False):
            has_meal = True
        if airline2 and self.airlines_config.get(airline2, {}).get('meal', False):
            has_meal = True

        if has_meal:
            base_text = "Tổng giá vé đã bao gồm toàn bộ thuế, phí, suất ăn.<br>"
        else:
            base_text = "Tổng giá vé đã bao gồm toàn bộ thuế, phí.<br>"

        note_text = discount_text + base_text

        luggage1 = self.airlines_config.get(airline1, {}).get('luggage', 'không có thông tin hành lý') if airline1 else 'không có thông tin hành lý'
        luggage2 = self.airlines_config.get(airline2, {}).get('luggage', 'không có thông tin hành lý') if airline2 else 'không có thông tin hành lý'

        if not self.is_round_trip:
            if airline1:
                display_name1 = self.input_processor.display_airline_name(airline1)
                note_text += f"● Với mỗi vé {display_name1}, được mang {luggage1}<br>"
        else:
            if airline1 == airline2 and luggage1 == luggage2:
                if airline1:
                    display_name1 = self.input_processor.display_airline_name(airline1)
                    note_text += f"● Với mỗi vé {display_name1}, được mang {luggage1}<br>"
            else:
                if airline1:
                    display_name1 = self.input_processor.display_airline_name(airline1)
                    note_text += f"● Với mỗi vé {display_name1}, được mang {luggage1}<br>"
                if airline2:
                    display_name2 = self.input_processor.display_airline_name(airline2)
                    note_text += f"● Với mỗi vé {display_name2}, được mang {luggage2}<br>"

        self.note_label.setText(note_text.rstrip("<br>"))
    
    def extract_from_clipboard(self):
        if QApplication.activeModalWidget():
            return
        try:
            self.input_processor.extract_from_clipboard(
                self, self.input_price, self.input_flight1, self.input_time1,
                self.label_flight_number1, self.input_flight_number1, self.input_plane_type1,
                self.input_flight2, self.input_time2, self.label_flight_number2,
                self.input_flight_number2, self.input_plane_type2,
                self.round_trip_checkbox
            )
            self.detected_airlines = self.input_processor.detected_airlines
            self.is_round_trip = self.input_processor.is_round_trip
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
