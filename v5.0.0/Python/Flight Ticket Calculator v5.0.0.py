import os, re
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, \
    QTableWidgetItem, QSpacerItem, QSizePolicy, QHeaderView, QMessageBox, QGroupBox, QGridLayout, QCheckBox, QComboBox, QTextEdit, QDialog
from PyQt6.QtGui import QIcon, QFont, QIntValidator, QDoubleValidator, QPixmap, QClipboard, QColor
from PyQt6.QtCore import Qt, QTimer
import time

class CustomFormatWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nhập mẫu tùy chỉnh")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QWidget { background-color: #F5F6FA; font-family: Arial; }
            QTextEdit { border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px; background-color: white; }
            QPushButton { border-radius: 5px; padding: 5px; font-weight: bold; color: white; }
            QLabel { color: #333333; }
        """)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        guide_label = QLabel("Sử dụng các placeholder sau trong mẫu của bạn:\n"
                            "{trip_type}, {airline}, {base_fare}, {voucher}, {total_guests}, "
                            "{table_data}, {total_cost}, {note}, {flight1_details}, {flight2_details}")
        guide_label.setWordWrap(True)
        layout.addWidget(guide_label)

        self.format_text = QTextEdit()
        self.format_text.setPlaceholderText("Nhập định dạng tùy chỉnh, ví dụ:\nChuyến bay {trip_type} - {airline}\nTổng: {total_cost}")
        layout.addWidget(self.format_text)

        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("Xác nhận")
        self.confirm_button.setStyleSheet("background-color: #4CAF50;")
        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.setStyleSheet("background-color: #FF5722;")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_format(self):
        return self.format_text.toPlainText()

class TicketCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.price_multiplied = False
        self.is_round_trip = False
        self.detected_airlines = []
        self.discount_amount = 0
        self.custom_format = ""

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Flight Ticket Calculator v5.0.0 | Tác giả: Batman")
        self.setFixedWidth(580)
        try:
            self.setWindowIcon(QIcon('images/icon.ico'))
        except:
            print("Icon không tìm thấy hoặc không hợp lệ.")

        self.setStyleSheet("""
            QWidget {
                background-color: #F5F6FA;
                font-family: Arial;
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 3px;
                background-color: white;
            }
            QLineEdit[readOnly="true"] {
                background-color: #E8ECEF;
            }
            QPushButton {
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
                color: white;
            }
            QLabel {
                color: #333333;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                font-size: 12px;
            }
            QCheckBox:disabled {
                color: #888888;
            }
            QComboBox {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 3px;
                background-color: white;
            }
            QMessageBox QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #388E3C;
                padding: 5px;
                min-width: 60px;
                font-weight: normal;
            }
            QMessageBox QPushButton:hover {
                background-color: #45A049;
            }
        """)

        self.label_title = QLabel("VÉ MÁY BAY NỘI ĐỊA VÀ QUỐC TẾ")
        self.label_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        flight1_group = QGroupBox("Thông tin chuyến bay 1")
        flight1_grid = QGridLayout()
        flight1_grid.setSpacing(5)
        
        self.label_flight_number1 = QLabel()
        self.label_flight_number1.setFixedSize(50, 60)
        self.label_flight_number1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.input_flight1 = QLabel()
        self.input_flight1.setToolTip("Chỉ tự động nhập từ clipboard")
        self.input_flight1.setStyleSheet("background-color: #E8ECEF; font-weight: bold; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        
        self.label_time1 = QLabel("")
        self.input_time1 = QLineEdit()
        self.input_time1.setReadOnly(True)
        
        self.input_flight_number1 = QLineEdit()
        self.input_flight_number1.setReadOnly(True)
        
        self.label_plane_type1 = QLabel("")
        self.input_plane_type1 = QLineEdit()
        self.input_plane_type1.setReadOnly(True)

        flight1_grid.addWidget(self.label_flight_number1, 0, 0, 2, 1)
        flight1_grid.addWidget(self.input_flight1, 0, 1)
        flight1_grid.addWidget(self.label_time1, 0, 2)
        flight1_grid.addWidget(self.input_time1, 0, 3)
        flight1_grid.addWidget(self.input_flight_number1, 1, 1)
        flight1_grid.addWidget(self.label_plane_type1, 1, 2)
        flight1_grid.addWidget(self.input_plane_type1, 1, 3)
        flight1_group.setLayout(flight1_grid)

        self.flight2_group = QGroupBox("Thông tin chuyến bay 2 (khứ hồi)")
        flight2_grid = QGridLayout()
        flight2_grid.setSpacing(5)
        
        self.label_flight_number2 = QLabel()
        self.label_flight_number2.setFixedSize(50, 60)
        self.label_flight_number2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.input_flight2 = QLabel()
        self.input_flight2.setToolTip("Chỉ tự động nhập từ clipboard")
        self.input_flight2.setStyleSheet("background-color: #E8ECEF; font-weight: bold; border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px;")
        
        self.label_time2 = QLabel("")
        self.input_time2 = QLineEdit()
        self.input_time2.setReadOnly(True)
        
        self.input_flight_number2 = QLineEdit()
        self.input_flight_number2.setReadOnly(True)
        
        self.label_plane_type2 = QLabel("")
        self.input_plane_type2 = QLineEdit()
        self.input_plane_type2.setReadOnly(True)

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

        passenger_group = QGroupBox("Thông tin hành khách và giá vé")
        input_grid = QGridLayout()
        input_grid.setSpacing(5)

        self.label_price = QLabel("💰 Giá vé gốc (VNĐ):")
        self.input_price = QLineEdit()
        self.input_price.setValidator(QDoubleValidator(0.99, 99999999.99, 2))
        self.input_price.setToolTip("Nhập giá vé gốc, tự động nhân 1000 nếu cần")
        self.input_price.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.input_price.textChanged.connect(self.format_price)
        self.input_price.returnPressed.connect(lambda: self.apply_multiplier(trigger_calculate=True))
        self.input_price.editingFinished.connect(lambda: self.apply_multiplier(trigger_calculate=False))
        self.input_price.focusOutEvent = self.apply_multiplier_on_focus_out
        self.input_price.focusInEvent = self.clear_on_focus

        self.label_discount = QLabel("🎟️ Voucher (%):")
        self.input_discount = QLineEdit()
        self.input_discount.setValidator(QDoubleValidator(0.0, 100.0, 2))

        self.label_adult = QLabel("👨‍👩‍👧‍👦 Người lớn:")
        self.input_adult = QLineEdit()
        self.input_adult.setValidator(QIntValidator(0, 100))

        self.label_child = QLabel("👶 Trẻ 2-11 tuổi:")
        self.input_child = QLineEdit()
        self.input_child.setValidator(QIntValidator(0, 100))

        self.label_infant = QLabel("👶 Dưới 2 tuổi:")
        self.input_infant = QLineEdit()
        self.input_infant.setValidator(QIntValidator(0, 100))

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
        passenger_group.setLayout(input_grid)

        self.format_layout = QHBoxLayout()
        self.label_format = QLabel("Mẫu xuất dữ liệu:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Mẫu chuẩn", "Mẫu ngắn gọn", "Mẫu chi tiết", "Mẫu tùy chỉnh"])
        self.format_combo.setToolTip("Chọn định dạng nội dung khi xuất dữ liệu")
        self.format_layout.addWidget(self.label_format)
        self.format_layout.addWidget(self.format_combo)
        self.format_layout.addStretch()

        self.button_layout = QHBoxLayout()
        self.button_calculate = QPushButton("📊 Tính toán")
        self.button_calculate.setStyleSheet("background-color: #4CAF50;")
        self.button_calculate.clicked.connect(self.calculate_total_and_capture)
        self.button_clear = QPushButton("🔄 Xóa dữ liệu")
        self.button_clear.setStyleSheet("background-color: #FF5722;")
        self.button_clear.clicked.connect(self.clear_fields)
        self.button_screenshot = QPushButton("📸 Xuất dữ liệu")
        self.button_screenshot.setStyleSheet("background-color: #2196F3;")
        self.button_screenshot.clicked.connect(self.calculate_total_and_copy)
        self.button_ocr = QPushButton("📋 Nhập dữ liệu")
        self.button_ocr.setStyleSheet("background-color: #FF9800;")
        self.button_ocr.clicked.connect(self.extract_from_clipboard)

        self.button_layout.addWidget(self.button_calculate)
        self.button_layout.addWidget(self.button_clear)
        self.button_layout.addWidget(self.button_screenshot)
        self.button_layout.addWidget(self.button_ocr)
        self.button_layout.setSpacing(10)

        self.table_group = QGroupBox("Giá vé sau khuyến mãi")
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["STT", "LOẠI VÉ", "SỐ LƯỢNG", "TIỀN 1 VÉ", "THÀNH TIỀN"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStyleSheet("background-color: #D3D3D3;")
        self.table.setStyleSheet("border: 1px solid #CCCCCC; font-size: 12px;")
        self.table.setRowCount(3)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 80)
        self.table.horizontalHeader().setMinimumHeight(30)
        self.table.horizontalHeader().setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.adjust_table_height()
        table_layout.addWidget(self.table)
        self.table_group.setLayout(table_layout)

        self.result_label = QLineEdit()
        self.result_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("color: red; background-color: #FFFFCC; border-radius: 5px;")
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
        self.main_layout.addLayout(self.format_layout)
        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addWidget(self.table_group)
        self.main_layout.addWidget(self.result_label)
        self.main_layout.addWidget(note_group)
        self.main_layout.addWidget(self.copyright_label)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.setLayout(self.main_layout)

        self.input_discount.setText("20")
        self.input_adult.setText("1")
        self.input_child.setText("0")
        self.input_infant.setText("0")

        QTimer.singleShot(0, self.adjust_window_height)

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

    def clear_on_focus(self, event):
        self.input_price.clear()
        self.price_multiplied = False
        super().focusInEvent(event)

    def calculate_total_and_capture(self):
        self.calculate_total()
        self.take_screenshot()

    def calculate_total_and_copy(self):
        self.calculate_total()
        self.copy_text()

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
            # Ẩn format_layout và button_layout
            format_label = self.format_layout.itemAt(0).widget() if self.format_layout.count() > 0 else None
            format_combo = self.format_layout.itemAt(1).widget() if self.format_layout.count() > 1 else None
            button_calculate = self.button_layout.itemAt(0).widget() if self.button_layout.count() > 0 else None
            button_clear = self.button_layout.itemAt(1).widget() if self.button_layout.count() > 1 else None
            button_screenshot = self.button_layout.itemAt(2).widget() if self.button_layout.count() > 2 else None
            button_ocr = self.button_layout.itemAt(3).widget() if self.button_layout.count() > 3 else None

            if format_label:
                format_label.setVisible(False)
            if format_combo:
                format_combo.setVisible(False)
            if button_calculate:
                button_calculate.setVisible(False)
            if button_clear:
                button_clear.setVisible(False)
            if button_screenshot:
                button_screenshot.setVisible(False)
            if button_ocr:
                button_ocr.setVisible(False)

            # Cập nhật bố cục và đợi giao diện vẽ hoàn tất
            QApplication.processEvents()
            time.sleep(0.05)  # Độ trễ nhỏ để đảm bảo giao diện ổn định

            # Chụp màn hình với render()
            pixmap = QPixmap(self.size())
            self.render(pixmap, renderFlags=QWidget.RenderFlag.DrawWindowBackground | QWidget.RenderFlag.DrawChildren)

            # Kiểm tra pixmap
            if pixmap.isNull():
                raise Exception("Ảnh chụp màn hình rỗng hoặc không hợp lệ")

            # Xóa clipboard trước khi sao chép
            clipboard = QApplication.clipboard()
            clipboard.clear()

            # Sao chép vào clipboard
            clipboard.setPixmap(pixmap)

            # Kiểm tra xem clipboard có chứa ảnh không
            if not clipboard.pixmap():
                # Lưu ảnh tạm thời như phương án dự phòng
                temp_file = "screenshot_temp.png"
                pixmap.save(temp_file, "PNG")
                raise Exception(f"Không thể sao chép vào clipboard. Ảnh đã được lưu tại {temp_file}")

            # Khôi phục các thành phần
            if format_label:
                format_label.setVisible(True)
            if format_combo:
                format_combo.setVisible(True)
            if button_calculate:
                button_calculate.setVisible(True)
            if button_clear:
                button_clear.setVisible(True)
            if button_screenshot:
                button_screenshot.setVisible(True)
            if button_ocr:
                button_ocr.setVisible(True)

            QMessageBox.information(self, "Chụp ảnh màn hình", "Ảnh màn hình đã được sao chép vào clipboard.")
        except Exception as e:
            # Khôi phục các thành phần nếu có lỗi
            format_label = self.format_layout.itemAt(0).widget() if self.format_layout.count() > 0 else None
            format_combo = self.format_layout.itemAt(1).widget() if self.format_layout.count() > 1 else None
            button_calculate = self.button_layout.itemAt(0).widget() if self.button_layout.count() > 0 else None
            button_clear = self.button_layout.itemAt(1).widget() if self.button_layout.count() > 1 else None
            button_screenshot = self.button_layout.itemAt(2).widget() if self.button_layout.count() > 2 else None
            button_ocr = self.button_layout.itemAt(3).widget() if self.button_layout.count() > 3 else None

            if format_label:
                format_label.setVisible(True)
            if format_combo:
                format_combo.setVisible(True)
            if button_calculate:
                button_calculate.setVisible(True)
            if button_clear:
                button_clear.setVisible(True)
            if button_screenshot:
                button_screenshot.setVisible(True)
            if button_ocr:
                button_ocr.setVisible(True)

            QMessageBox.critical(self, "Lỗi chụp ảnh màn hình", f"Chi tiết lỗi: {str(e)}")

    def copy_text(self):
        required_inputs = [
            self.input_price.text().strip(),
            self.input_discount.text().strip(),
            self.input_adult.text().strip(),
            self.input_child.text().strip(),
            self.input_infant.text().strip()
        ]
        if not all(required_inputs):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ tất cả các trường trước khi xuất dữ liệu.")
            return
        try:
            voucher_input = self.input_discount.text().strip()
            voucher_value = voucher_input if voucher_input.isdigit() else "0"
            base_fare_input = self.input_price.text().strip()
            base_fare_value = int(base_fare_input.replace(',', '')) if base_fare_input.replace(',', '').isdigit() else 0
            adult_count = int(self.input_adult.text())
            child_count = int(self.input_child.text())
            infant_count = int(self.input_infant.text())
            total_guests = adult_count + child_count + infant_count

            airline_name = ", ".join(self.detected_airlines[:2]) if self.detected_airlines else "Không xác định"
            note_text = self.note_label.text().strip()
            trip_type = "khứ hồi" if self.is_round_trip else "1 chiều"

            selected_format = self.format_combo.currentText()

            table_data = ""
            for row in range(self.table.rowCount()):
                item_quantity = self.table.item(row, 2)
                if item_quantity and item_quantity.text().isdigit() and int(item_quantity.text()) > 0:
                    item_name = self.table.item(row, 1).text().strip()
                    quantity = int(item_quantity.text())
                    price = float(self.table.item(row, 3).text().replace(" VNĐ", "").replace(",", "").strip()) if "Miễn phí" not in self.table.item(row, 3).text() else 0
                    total = float(self.table.item(row, 4).text().replace(" VNĐ", "").replace(",", "").strip())
                    formatted_line = f"{item_name}: {quantity} x {price:,.0f} = {total:,.0f} VNĐ\n" if price > 0 else f"{item_name}: {quantity} x Miễn phí = 0 VNĐ\n"
                    table_data += formatted_line

            total_cost = self.result_label.text().strip()
            note_text_cleaned = re.sub(r'<br>', '\n', note_text)
            note_text_cleaned = re.sub(r'<[^>]+>', '', note_text_cleaned)

            flight1_details = (
                f"Chuyến bay 1:\n"
                f"  - Lộ trình: {self.input_flight1.text()}\n"
                f"  - Thời gian: {self.input_time1.text()}\n"
                f"  - Số hiệu: {self.input_flight_number1.text()}\n"
                f"  - Loại máy bay: {self.input_plane_type1.text()}\n"
            )
            flight2_details = (
                f"Chuyến bay 2:\n"
                f"  - Lộ trình: {self.input_flight2.text()}\n"
                f"  - Thời gian: {self.input_time2.text()}\n"
                f"  - Số hiệu: {self.input_flight_number2.text()}\n"
                f"  - Loại máy bay: {self.input_plane_type2.text()}\n"
            ) if self.is_round_trip else ""

            if selected_format == "Mẫu tùy chỉnh":
                custom_window = CustomFormatWindow(self)
                if custom_window.exec() == QDialog.DialogCode.Accepted:
                    self.custom_format = custom_window.get_format()
                else:
                    QMessageBox.information(self, "Hủy", "Đã hủy nhập mẫu tùy chỉnh.")
                    return

                if not self.custom_format.strip():
                    QMessageBox.warning(self, "Lỗi", "Mẫu tùy chỉnh không được để trống!")
                    return

                clipboard_content = self.custom_format.format(
                    trip_type=trip_type,
                    airline=airline_name,
                    base_fare=f"{base_fare_value:,.0f} VNĐ",
                    voucher=f"{voucher_value}%",
                    total_guests=str(total_guests),
                    table_data=table_data,
                    total_cost=total_cost,
                    note=note_text_cleaned,
                    flight1_details=flight1_details,
                    flight2_details=flight2_details
                )
            elif selected_format == "Mẫu chuẩn":
                clipboard_content = (
                    "✈️ EM GỬI ANH/CHỊ THÔNG TIN CHUYẾN BAY:\n\n"
                    f"Đây là chuyến bay {trip_type}.\n"
                    f"♦️ Hãng bay: {airline_name}.\n"
                    f"♦️ Giá vé gốc: {base_fare_value:,.0f} VNĐ/vé\n"
                    f"♦️ Tổng số khách: {total_guests}\n"
                    f"♦️ Mã voucher khuyến mãi: {voucher_value}%\n\n"
                    "💰 CHI PHÍ SAU KHUYẾN MÃI:\n\n"
                    f"{table_data}\n"
                    f"💵 {total_cost}\n\n"
                    f"🎒 {note_text_cleaned}"
                )
            elif selected_format == "Mẫu ngắn gọn":
                clipboard_content = (
                    f"✈️ CHUYẾN BAY {trip_type.upper()} - {airline_name}\n"
                    f"Giá vé gốc: {base_fare_value:,.0f} VNĐ\n"
                    f"Voucher: {voucher_value}%\n"
                    f"Tổng chi phí: {total_cost}\n"
                    f"Số khách: {total_guests}"
                )
            elif selected_format == "Mẫu chi tiết":
                clipboard_content = (
                    "✈️ THÔNG TIN CHUYẾN BAY:\n\n"
                    f"Loại chuyến: {trip_type.upper()}\n"
                    f"Hãng bay: {airline_name}\n"
                    f"{flight1_details}"
                    f"{flight2_details}\n"
                    f"Giá vé gốc: {base_fare_value:,.0f} VNĐ/vé\n"
                    f"Voucher: {voucher_value}%\n"
                    f"Số khách: {total_guests} (Người lớn: {adult_count}, Trẻ 2-11: {child_count}, Dưới 2 tuổi: {infant_count})\n\n"
                    "💰 CHI PHÍ:\n"
                    f"{table_data}\n"
                    f"💵 {total_cost}\n\n"
                    f"📝 Ghi chú: {note_text_cleaned}"
                )

            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_content)
            QMessageBox.information(self, "Sao chép nội dung", f"Nội dung đã được sao chép vào clipboard theo {selected_format}.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra: {str(e)}")

    def calculate_total(self):
        try:
            price = float(self.input_price.text().replace(",", ""))
            if price <= 0:
                raise ValueError("Giá vé gốc phải lớn hơn 0.")
            discount = float(self.input_discount.text()) / 100
            adult_count = int(self.input_adult.text())
            child_count = int(self.input_child.text())
            infant_count = int(self.input_infant.text())

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
            self.result_label.setText(f"TỔNG CHI PHÍ TOÀN HÀNH TRÌNH: {total:,.0f} VNĐ")

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
        except ValueError:
            QMessageBox.warning(self, "Lỗi nhập liệu", "Vui lòng nhập đầy đủ thông tin hợp lệ.")

    def clear_fields(self):
        self.input_price.clear()
        self.input_discount.clear()
        self.input_adult.clear()
        self.input_child.clear()
        self.input_infant.clear()
        self.input_flight1.setText("")
        self.input_time1.clear()
        self.label_flight_number1.clear()
        self.input_flight_number1.clear()
        self.input_plane_type1.clear()
        self.input_flight2.setText("")
        self.input_time2.clear()
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

    def format_price(self):
        price_text = self.input_price.text().replace(",", "")
        try:
            if price_text:
                price = float(price_text)
                formatted_price = "{:,.0f}".format(price)
                self.input_price.setText(formatted_price)
                self.input_price.setCursorPosition(len(formatted_price))
        except ValueError:
            pass

    def apply_multiplier(self, trigger_calculate=True):
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

    def apply_multiplier_on_focus_out(self, event):
        self.apply_multiplier()
        super(QLineEdit, self.input_price).focusOutEvent(event)

    def update_note_label(self, detected_airlines):
        notes = {
            "Vietjet Air": "+ Với mỗi vé Vietjet Air, được mang theo 7kg hành lý xách tay và 1 kiện 20kg hành lý ký gửi",
            "Bamboo Airways": "+ Với mỗi vé Bamboo Airways, được mang theo 7kg hành lý xách tay và 1 kiện 20kg hành lý ký gửi",
            "Vietnam Airlines": "+ Với mỗi vé Vietnam Airlines, được mang theo 10kg hành lý xách tay và 1 kiện 23kg hành lý ký gửi",
            "Vietravel Airlines": "+ Với mỗi của Vietravel Airlines, được mang theo 7kg hành lý xách tay và 1 kiện 15kg hành lý ký gửi",
            "Pacific Airlines": "+ Với mỗi vé Pacific Airlines, được mang theo 7kg hành lý xách tay và 1 kiện 23kg hành lý ký gửi"
        }
        discount_text = f"<span style='color:green'>Số tiền được giảm trong chuyến bay này là: {self.discount_amount:,.0f} VNĐ.</span><br>"
        base_text = "Tổng giá vé đã bao gồm toàn bộ thuế, phí" + (", suất ăn" if "Vietnam Airlines" in detected_airlines else "") + ".<br>"
        if not detected_airlines:
            self.note_label.setText(discount_text + base_text)
        elif len(detected_airlines) == 1:
            self.note_label.setText(discount_text + base_text + notes[detected_airlines[0]])
        else:
            self.note_label.setText(discount_text + base_text + notes[detected_airlines[0]] + "<br>" + notes[detected_airlines[1]])

    def extract_from_clipboard(self):
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
                "Vietjet Air": "images/vietjet_air.gif",
                "Bamboo Airways": "images/bamboo_airways.gif",
                "Vietnam Airlines": "images/vietnam_airlines.gif",
                "Vietravel Airlines": "images/vietravel_airlines.gif",
                "Pacific Airlines": "images/pacific_airlines.gif"
            }

            route_pattern = r'(hà nội|tp hồ chí minh|đà nẵng|nha trang|hải phòng|phú quốc|đà lạt|cần thơ|quy nhơn|thanh hóa|thanh hoá|vinh|tp vinh|huế|điện biên|quảng ninh|buôn mê thuột|pleiku|tuy hòa|tuy hoà|côn đảo|rạch giá|đồng hới|tam kỳ|cà mau)\s+(hà nội|tp hồ chí minh|đà nẵng|nha trang|hải phòng|phú quốc|đà lạt|cần thơ|quy nhơn|thanh hóa|thanh hoá|vinh|tp vinh|huế|điện biên|quảng ninh|buôn mê thuột|pleiku|tuy hòa|tuy hoà|côn đảo|rạch giá|đồng hới|tam kỳ|cà mau)'
            routes = re.findall(route_pattern, normalized_text)

            flight_pattern = r'(vietjet air|bamboo airways|vietnam airlines|vietravel airlines|pacific airlines)\s+(vj|vn|qh|vu|bl)\s*(\d{2,4})'
            flight_matches = re.findall(flight_pattern, text, re.IGNORECASE)
            
            self.is_round_trip = len(routes) >= 2 or len(flight_matches) >= 2
            self.round_trip_checkbox.setChecked(self.is_round_trip)
            self.flight2_group.setVisible(self.is_round_trip)

            if routes:
                self.input_flight1.setText(
                    f"<span>{routes[0][0].upper()}</span> <img src='images/arrow.png' width='11'> <span>{routes[0][1].upper()}</span>"
                )
                if len(routes) > 1 and self.is_round_trip:
                    self.input_flight2.setText(
                        f"<span>{routes[1][0].upper()}</span> <img src='images/arrow.png' width='11'> <span>{routes[1][1].upper()}</span>"
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
                self.input_time1.setText(f"{days[0]} | {dates[0].upper() if dates else ''} | {time_ranges[0].upper() if time_ranges else ''}")
                if self.is_round_trip and len(days) > 1:
                    self.input_time2.setText(f"{days[1]} | {dates[1].upper() if len(dates) > 1 else ''} | {time_ranges[1].upper() if len(time_ranges) > 1 else ''}")

            if flight_matches:
                if len(flight_matches) >= 1:
                    airline1 = flight_matches[0][0].title()
                    flight_num1 = f"{flight_matches[0][1]}{flight_matches[0][2]}"
                    self.input_flight_number1.setText(f"{airline1.upper()} | {flight_num1.upper()}")
                    for airline, logo_path in logo_paths.items():
                        if airline.upper() in self.input_flight_number1.text():
                            pixmap1 = QPixmap(logo_path)
                            if not pixmap1.isNull():
                                self.label_flight_number1.setPixmap(pixmap1.scaled(50, 60, Qt.AspectRatioMode.KeepAspectRatio))
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
                                self.label_flight_number2.setPixmap(pixmap2.scaled(50, 60, Qt.AspectRatioMode.KeepAspectRatio))
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

if __name__ == "__main__":
    app = QApplication([])
    window = TicketCalculator()
    window.show()
    app.exec()
