import os
import sys
import json
import portalocker
import requests
from PyQt6.QtCore import Qt, QTimer, QEvent, QMimeData, QBuffer, QIODevice, QUrl, QMetaObject, pyqtSlot
from PyQt6.QtGui import QIcon, QFont, QIntValidator, QDoubleValidator, QPixmap, QKeySequence, QShortcut, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QGridLayout, QCheckBox, QComboBox, QDialog
)
from support_dialog import SupportDialog
from updater import Updater, UpdateManager
from input_processor import InputProcessor
from text_exporter import TextExporter
from history_dialog import HistoryDialog
from login import LoginDialog
import pyrebase

# Firebase configuration
firebase_config = {
    "apiKey": "AIzaSyCU2lHfJmlQZ1mfDZlrNC7ejIetVv4uQTE",
    "authDomain": "flight-ticket-calculator-68881.firebaseapp.com",
    "databaseURL": "https://flight-ticket-calculator-68881-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "flight-ticket-calculator-68881",
    "storageBucket": "flight-ticket-calculator-68881.appspot.com",
    "messagingSenderId": "344355928134",
    "appId": "1:344355928134:web:700d9d1b92d3ce2effb247",
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

class TicketCalculator(QWidget):
    CURRENT_VERSION = "6.2.3"

    def __init__(self, current_user, current_user_id=None, id_token=None, refresh_token=None, device_id=None):
        super().__init__()
        self.current_user = current_user
        self.current_user_id = current_user_id
        self.id_token = id_token
        self.refresh_token = refresh_token
        self.device_id = device_id  # Lưu device_id từ LoginDialog
        self.price_multiplied = False
        self.is_round_trip = False
        self.detected_airlines = []
        self.discount_amount = 0
        self.child_price_ratio = 0.7
        self.history = []
        self.stream = None  # Lưu trữ stream Firebase
        self.is_closing = False  # Cờ theo dõi trạng thái đóng ứng dụng

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
        self.text_exporter = TextExporter(self.airlines_config, parent=self)
        self.initUI()

        # Thêm lắng nghe sự kiện Firebase và kiểm tra trạng thái định kỳ (chỉ cho người dùng không phải admin)
        if self.current_user != "admin" and self.current_user_id and self.id_token and self.device_id:
            self.setup_online_status_listener()
            self.setup_online_status_checker()

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

    def setup_online_status_listener(self):
        """Lắng nghe thay đổi trạng thái online trong Firebase Realtime Database."""
        try:
            # Kiểm tra kết nối mạng
            try:
                requests.get("https://google.com", timeout=2)
            except:
                print("Không có kết nối mạng, không thể thiết lập lắng nghe trạng thái online.")
                return

            def stream_handler(message):
                # Kiểm tra trạng thái online và device_id, chỉ hiển thị thông báo nếu không đang đóng ứng dụng
                if not self.is_closing and (message["data"] is None or (isinstance(message["data"], dict) and message["data"].get("device_id") != self.device_id)):
                    QTimer.singleShot(0, self.show_session_terminated_message)
            
            # Lắng nghe thay đổi trong online_users/<user_id> và lưu stream
            self.stream = db.child("online_users").child(self.current_user_id).stream(stream_handler, self.id_token)
        except Exception as e:
            print(f"Lỗi khi thiết lập lắng nghe trạng thái online: {e}")

    def setup_online_status_checker(self):
        """Kiểm tra định kỳ trạng thái online để xử lý trường hợp mất kết nối."""
        def check_online_status():
            retries = 3
            for attempt in range(retries):
                try:
                    # Kiểm tra kết nối mạng
                    try:
                        requests.get("https://google.com", timeout=2)
                    except:
                        print(f"Không có kết nối mạng, bỏ qua kiểm tra trạng thái online (thử {attempt + 1}/{retries}).")
                        return

                    if not self.id_token:
                        self.id_token = self.refresh_id_token()
                    if not self.id_token:
                        print(f"Không có id_token, bỏ qua kiểm tra trạng thái online (thử {attempt + 1}/{retries}).")
                        return

                    # Kiểm tra trạng thái online và device_id
                    status = db.child("online_users").child(self.current_user_id).get(self.id_token).val()
                    if not self.is_closing and (not status or status.get("device_id") != self.device_id):
                        QTimer.singleShot(0, self.show_session_terminated_message)
                    return
                except Exception as e:
                    print(f"Lỗi khi kiểm tra trạng thái online (thử {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        QTimer.singleShot(1000, lambda: None)  # Đợi 1 giây trước khi thử lại
                    continue
            print("Không thể kiểm tra trạng thái online sau nhiều lần thử.")

        # Kiểm tra mỗi 10 giây
        self.online_status_timer = QTimer(self)
        self.online_status_timer.timeout.connect(check_online_status)
        self.online_status_timer.start(10000)

    @pyqtSlot()
    def show_session_terminated_message(self):
        """Hiển thị thông báo phiên bị hủy và thoát ứng dụng trong luồng chính."""
        if self.is_closing:
            return  # Không hiển thị thông báo nếu ứng dụng đang đóng
        QMessageBox.critical(
            self,
            "Phiên đăng nhập bị hủy",
            "Tài khoản đã được đăng nhập ở nơi khác. Ứng dụng sẽ thoát.",
            QMessageBox.StandardButton.Ok
        )
        # Đóng stream trước khi thoát
        if self.stream:
            try:
                self.stream.close()
                self.stream = None
            except Exception as e:
                print(f"Lỗi khi đóng stream: {e}")
        # Thoát ứng dụng
        QTimer.singleShot(0, QApplication.quit)

    def refresh_id_token(self):
        """Làm mới idToken sử dụng Firebase REST API với cơ chế thử lại."""
        retries = 3
        for attempt in range(retries):
            try:
                # Kiểm tra kết nối mạng
                try:
                    requests.get("https://google.com", timeout=2)
                except:
                    print(f"Không có kết nối mạng, không thể làm mới token (thử {attempt + 1}/{retries}).")
                    return None

                if not self.refresh_token:
                    raise Exception("Không có refreshToken để làm mới")
                response = requests.post(
                    "https://securetoken.googleapis.com/v1/token",
                    params={"key": firebase_config["apiKey"]},
                    data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()
                self.id_token = data['id_token']
                self.refresh_token = data['refresh_token']
                print(f"Đã làm mới idToken: {self.id_token[:10]}...")
                return self.id_token
            except Exception as e:
                print(f"Lỗi làm mới token (thử {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    QTimer.singleShot(1000, lambda: None)  # Đợi 1 giây trước khi thử lại
                continue
        print("Không thể làm mới token sau nhiều lần thử.")
        return None

    def closeEvent(self, event):
        self.is_closing = True  # Đặt cờ trước khi đóng
        try:
            if hasattr(self, 'lock'):
                portalocker.unlock(self.lock)
                self.lock.close()
            if self.current_user and self.current_user != "admin" and self.current_user_id and self.device_id:
                try:
                    # Kiểm tra kết nối mạng
                    try:
                        requests.get("https://google.com", timeout=2)
                    except:
                        print("Không có kết nối mạng, không thể đăng xuất khỏi Firebase.")
                        event.accept()
                        return

                    if not self.id_token:
                        self.id_token = self.refresh_id_token()
                    if self.id_token:
                        # Đóng stream trước khi xóa trạng thái online
                        if self.stream:
                            try:
                                self.stream.close()
                                self.stream = None
                            except Exception as e:
                                print(f"Lỗi khi đóng stream: {e}")
                        # Chỉ xóa trạng thái online nếu device_id khớp
                        status = db.child("online_users").child(self.current_user_id).get(self.id_token).val()
                        if status and status.get("device_id") == self.device_id:
                            print(f"Đang đăng xuất user_id: {self.current_user_id}, device_id: {self.device_id}")
                            db.child("online_users").child(self.current_user_id).remove(self.id_token)
                        else:
                            print(f"Không xóa trạng thái online vì device_id không khớp: {status.get('device_id') if status else None}")
                    else:
                        print("Không thể đăng xuất do token không hợp lệ")
                except Exception as e:
                    print(f"Lỗi khi đăng xuất khỏi Firebase: {e}")
        except Exception as e:
            print(f"Lỗi chung trong closeEvent: {e}")
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
        self.setWindowTitle(f"Flight Ticket Calculator v{self.CURRENT_VERSION} | Tác giả: Batman | Người dùng: {self.current_user}")
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
        self.button_clear = QPushButton("🔄 Xóa hết")
        self.button_clear.setStyleSheet("background-color: #4CAF50;")
        self.button_clear.clicked.connect(self.clear_fields)
        self.button_clear.setShortcut("F1")
        self.button_clear.setToolTip("Xóa tất cả dữ liệu (F1)")
        self.button_ocr = QPushButton("📋 Nhập liệu")
        self.button_ocr.setStyleSheet("background-color: #FF5722;")
        self.button_ocr.clicked.connect(self.extract_from_clipboard)
        self.button_ocr.setShortcut("F2")
        self.button_ocr.setToolTip("Nhập dữ liệu từ clipboard (F2)")
        self.button_calculate = QPushButton("📸 Chụp ảnh")
        self.button_calculate.setStyleSheet("background-color: #2196F3;")
        self.button_calculate.clicked.connect(self.calculate_total_and_capture)
        self.button_calculate.setShortcut("F3")
        self.button_calculate.setToolTip("Chụp ảnh màn hình (F3)")
        self.button_screenshot = QPushButton("📊 Xuất chữ")
        self.button_screenshot.setStyleSheet("background-color: #FF9800;")
        self.button_screenshot.clicked.connect(self.calculate_total_and_copy)
        self.button_screenshot.setShortcut("F4")
        self.button_screenshot.setToolTip("Xuất dữ liệu ra clipboard (F4)")
        self.button_history = QPushButton("📜 Lịch sử")
        self.button_history.setStyleSheet("background-color: #009688;")
        self.button_history.clicked.connect(self.show_history_dialog)
        self.button_history.setShortcut("F5")
        self.button_history.setToolTip("Xem lịch sử nhập liệu (F5)")
        self.button_payment = QPushButton("💳 Hóa đơn")
        self.button_payment.setStyleSheet("background-color: #E91E63;")
        self.button_payment.clicked.connect(self.open_payment_page)
        self.button_payment.setShortcut("F6")
        self.button_payment.setToolTip("Mở hóa đơn đặt vé (F6)")
        self.button_support = QPushButton("💬 Ghi chú")
        self.button_support.setStyleSheet("background-color: #673AB7;")
        self.button_support.clicked.connect(self.show_support_dialog)
        self.button_support.setShortcut("F7")
        self.button_support.setToolTip("Mở cửa sổ Ghi chú (F7)")

        self.button_layout.addWidget(self.button_clear)
        self.button_layout.addWidget(self.button_ocr)
        self.button_layout.addWidget(self.button_calculate)
        self.button_layout.addWidget(self.button_screenshot)
        self.button_layout.addWidget(self.button_history)
        self.button_layout.addWidget(self.button_payment)
        self.button_layout.addWidget(self.button_support)
        self.button_layout.setSpacing(2)
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

        self.copyright_label = QLabel("Kính chúc quý khách có những hành trình bay an toàn!")
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

        # Thêm QTimer để làm mới token định kỳ (chỉ cho người dùng không phải admin)
        if self.current_user != "admin":
            self.token_refresh_timer = QTimer(self)
            self.token_refresh_timer.timeout.connect(self.refresh_id_token)
            self.token_refresh_timer.start(50 * 60 * 1000)  # 50 phút

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

        QTimer.singleShot(0, self.adjust_window_height)

    def show_history_dialog(self):
        if QApplication.activeModalWidget():
            return
        if not self.history:
            QMessageBox.information(self, "Lịch sử", "Chưa có dữ liệu lịch sử nào.")
            return
        try:
            dialog = HistoryDialog(self.history, self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_entry:
                self.restore_history_entry(dialog.selected_entry)
                QMessageBox.information(self, "Khôi phục", "Dữ liệu đã được khôi phục từ lịch sử.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở lịch sử: {str(e)}")

    def restore_history_entry(self, entry):
        self.input_price.setText(entry['price'])
        self.input_discount.setText(entry['discount'])
        self.input_adult.setText(entry['adult'])
        self.input_child.setText(entry['child'])
        self.input_infant.setText(entry['infant'])
        self.input_flight1.setText(entry['flight1'])
        self.input_time1.setText(entry['time1'])
        self.input_flight_number1.setText(entry['flight_number1'])
        self.input_plane_type1.setText(entry['plane_type1'])
        self.input_flight2.setText(entry['flight2'])
        self.input_time2.setText(entry['time2'])
        self.input_flight_number2.setText(entry['flight_number2'])
        self.input_plane_type2.setText(entry['plane_type2'])
        self.is_round_trip = entry['is_round_trip']
        self.round_trip_checkbox.setChecked(self.is_round_trip)
        self.flight2_group.setVisible(self.is_round_trip)
        self.detected_airlines = entry['detected_airlines']
        
        self.table.clearContents()
        for row, row_data in enumerate(entry['table_data']):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                if col in [0, 2]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
        
        self.result_label.setText(entry['total'])
        self.discount_amount = entry['discount_amount']
        self.update_note_label(self.detected_airlines)
        self.adjust_table_height()
        self.adjust_window_height()
        self.load_logo_from_history(entry)

    def load_logo_from_history(self, entry):
        airline1 = None
        airline2 = None
        flight_number1 = entry['flight_number1']
        flight_number2 = entry['flight_number2']
        detected_airlines = entry['detected_airlines']
        
        for airline, config in self.airlines_config.items():
            if flight_number1 and flight_number1.upper().startswith(config.get('code', '').upper()):
                airline1 = airline
            if self.is_round_trip and flight_number2 and flight_number2.upper().startswith(config.get('code', '').upper()):
                airline2 = airline
        
        if not airline1 and detected_airlines:
            airline1 = detected_airlines[0]
        if self.is_round_trip and not airline2 and len(detected_airlines) > 1:
            airline2 = detected_airlines[1]
        elif self.is_round_trip and not airline2 and detected_airlines:
            airline2 = detected_airlines[0]
        
        self.input_processor.load_logo(self.label_flight_number1, airline1, self)
        if self.is_round_trip:
            self.input_processor.load_logo(self.label_flight_number2, airline2, self)

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

            from time import time
            table_data = []
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                table_data.append(row_data)
            
            history_entry = {
                'timestamp': time(),
                'price': self.input_price.text(),
                'discount': self.input_discount.text(),
                'adult': self.input_adult.text(),
                'child': self.input_child.text(),
                'infant': self.input_infant.text(),
                'flight1': self.input_flight1.text(),
                'time1': self.input_time1.text(),
                'flight_number1': self.input_flight_number1.text(),
                'flight2': self.input_flight2.text(),
                'time2': self.input_time2.text(),
                'flight_number2': self.input_flight_number2.text(),
                'plane_type2': self.input_plane_type2.text(),
                'is_round_trip': self.is_round_trip,
                'table_data': table_data,
                'total': self.result_label.text(),
                'discount_amount': self.discount_amount,
                'detected_airlines': self.detected_airlines[:]
            }
            
            if self.history:
                last_entry = self.history[-1]
                is_duplicate = True
                for key in history_entry:
                    if key == 'timestamp':
                        continue
                    if history_entry[key] != last_entry[key]:
                        is_duplicate = False
                        break
                if not is_duplicate:
                    self.history.append(history_entry)
            else:
                self.history.append(history_entry)
            
            if len(self.history) > 10:
                self.history.pop(0)

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
    app = QApplication(sys.argv)
    
    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        window = TicketCalculator(
            login_dialog.current_user,
            login_dialog.current_user_id,
            login_dialog.id_token,
            login_dialog.refresh_token,
            login_dialog.device_id
        )
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)