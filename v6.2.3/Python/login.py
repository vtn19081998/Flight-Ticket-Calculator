import uuid
import pyrebase
import requests
from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QMessageBox, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QTimer

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

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đăng nhập - Flight Ticket Calculator")
        self.setFixedSize(400, 350)
        self.setWindowIcon(QIcon('images/icon.ico'))

        self.current_user = None
        self.current_user_id = None
        self.id_token = None
        self.refresh_token = None
        self.device_id = str(uuid.uuid4())  # Tạo device_id duy nhất

        self.setStyleSheet("""
            QDialog {
                background-color: #F5F6FA;
                font-family: Arial, sans-serif;
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
            QPushButton {
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
                color: white;
                border: none;
            }
            QPushButton#loginButton {
                background-color: #4CAF50;
            }
            QPushButton#loginButton:hover {
                background-color: #45A049;
            }
            QPushButton#registerButton {
                background-color: #2196F3;
            }
            QPushButton#registerButton:hover {
                background-color: #1E88E5;
            }
            QLabel {
                color: #333333;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2196F3;
            }
            QLabel#footerLabel {
                font-size: 12px;
                color: #666666;
            }
            QMessageBox QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                min-width: 60px;
                font-weight: bold;
            }
            QMessageBox QPushButton:hover {
                background-color: #45A049;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        logo_label = QLabel()
        pixmap = QPixmap('images/icon.png')
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(logo_label)
        else:
            title_label = QLabel("Flight Ticket Calculator")
            title_label.setObjectName("titleLabel")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nhập Email")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Nhập mật khẩu")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form_layout.addRow(self.username_input)
        form_layout.addRow(self.password_input)

        main_layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.login_button = QPushButton("Đăng nhập")
        self.login_button.setObjectName("loginButton")
        self.login_button.clicked.connect(self.attempt_login)

        self.register_button = QPushButton("Đăng ký")
        self.register_button.setObjectName("registerButton")
        self.register_button.clicked.connect(self.show_register_message)

        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.register_button)

        main_layout.addLayout(button_layout)

        main_layout.addStretch()

        footer_label = QLabel("Flight Ticket Calculator © 2025 by Batman")
        footer_label.setObjectName("footerLabel")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer_label)

        self.setLayout(main_layout)

    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ email và mật khẩu.")
            return

        self.login_button.setEnabled(False)
        self.login_button.setText("Đang kiểm tra...")

        QTimer.singleShot(100, lambda: self.process_login(username, password))

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
        QMessageBox.critical(self, "Lỗi", "Không thể làm mới token. Vui lòng đăng nhập lại.")
        return None

    def check_online_status(self, user_id, id_token, retries=3, delay=1000):
        """Kiểm tra trạng thái online với cơ chế thử lại."""
        for attempt in range(retries):
            try:
                # Kiểm tra kết nối mạng
                try:
                    requests.get("https://google.com", timeout=2)
                except:
                    print(f"Không có kết nối mạng, bỏ qua kiểm tra trạng thái online (thử {attempt + 1}/{retries}).")
                    return None

                status = db.child("online_users").child(user_id).get(id_token).val()
                return status
            except Exception as e:
                print(f"Lỗi kiểm tra trạng thái online (thử {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    QTimer.singleShot(delay, lambda: None)  # Đợi trước khi thử lại
                continue
        print("Không thể kiểm tra trạng thái online sau nhiều lần thử.")
        return None

    def process_login(self, username, password):
        try:
            # Kiểm tra kết nối mạng
            try:
                requests.get("https://google.com", timeout=5)
                online = True
            except:
                online = False

            if username.lower() == "admin" and password == "Abc13579@":
                self.current_user = username
                self.current_user_id = "admin"
                self.id_token = None
                self.refresh_token = None
                self.device_id = None  # Không cần device_id cho admin
                QMessageBox.information(self, "Đăng nhập thành công", "Chào mừng Quản trị viên!")
                self.accept()
                return

            if not online:
                QMessageBox.warning(self, "Lỗi", "Không có kết nối Internet. Vui lòng kiểm tra kết nối và thử lại.")
                return

            # Đăng nhập vào Firebase
            user = auth.sign_in_with_email_and_password(username, password)
            self.id_token = user['idToken']
            self.refresh_token = user['refreshToken']
            self.current_user_id = user['localId']

            # Kiểm tra trạng thái online với cơ chế thử lại
            status = self.check_online_status(self.current_user_id, self.id_token)
            if status and status.get("online"):
                reply = QMessageBox.question(
                    self,
                    "Phiên đăng nhập trùng lặp",
                    "Tài khoản này đang được sử dụng ở một thiết bị khác. Bạn có muốn đăng xuất thiết bị kia và đăng nhập tại đây không?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    self.reject()
                    return
                # Thử xóa trạng thái online của phiên cũ
                retries = 3
                for attempt in range(retries):
                    try:
                        # Kiểm tra kết nối mạng
                        try:
                            requests.get("https://google.com", timeout=2)
                        except:
                            print(f"Không có kết nối mạng, không thể xóa phiên cũ (thử {attempt + 1}/{retries}).")
                            QMessageBox.critical(self, "Lỗi", "Không có kết nối Internet. Vui lòng kiểm tra và thử lại.")
                            self.reject()
                            return

                        db.child("online_users").child(self.current_user_id).remove(self.id_token)
                        break
                    except Exception as e:
                        print(f"Lỗi khi xóa phiên cũ (thử {attempt + 1}/{retries}): {e}")
                        if attempt < retries - 1:
                            QTimer.singleShot(1000, lambda: None)
                        continue
                else:
                    QMessageBox.critical(self, "Lỗi", "Không thể đăng xuất phiên cũ. Vui lòng thử lại sau.")
                    self.reject()
                    return

                # Kiểm tra lại trạng thái online để đảm bảo phiên cũ đã bị xóa
                status = self.check_online_status(self.current_user_id, self.id_token)
                if status and status.get("online"):
                    QMessageBox.critical(self, "Lỗi", "Không thể đăng xuất phiên cũ. Vui lòng thử lại sau.")
                    self.reject()
                    return

            # Đặt trạng thái online cho phiên mới với device_id
            retries = 3
            for attempt in range(retries):
                try:
                    # Kiểm tra kết nối mạng
                    try:
                        requests.get("https://google.com", timeout=2)
                    except:
                        print(f"Không có kết nối mạng, không thể đặt trạng thái online (thử {attempt + 1}/{retries}).")
                        QMessageBox.critical(self, "Lỗi", "Không có kết nối Internet. Vui lòng kiểm tra và thử lại.")
                        self.reject()
                        return

                    db.child("online_users").child(self.current_user_id).set(
                        {"online": True, "device_id": self.device_id}, self.id_token
                    )
                    break
                except Exception as e:
                    print(f"Lỗi khi đặt trạng thái online (thử {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        QTimer.singleShot(1000, lambda: None)
                    continue
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể thiết lập trạng thái online. Vui lòng thử lại.")
                self.reject()
                return

            self.current_user = username
            QMessageBox.information(self, "Đăng nhập thành công", f"Chào mừng {username}!")
            self.accept()

        except Exception as e:
            print(f"Lỗi đăng nhập: {e}")
            QMessageBox.warning(self, "Lỗi", "Email hoặc mật khẩu không đúng.")
        finally:
            self.login_button.setEnabled(True)
            self.login_button.setText("Đăng nhập")

    def show_register_message(self):
        QMessageBox.information(self, "Thông báo", "Để đăng ký sử dụng, liên hệ tác giả Batman.")

    def closeEvent(self, event):
        if self.current_user and self.current_user != "admin":
            try:
                if not self.id_token:
                    self.id_token = self.refresh_id_token()
                if self.id_token:
                    # Kiểm tra kết nối mạng
                    try:
                        requests.get("https://google.com", timeout=2)
                    except:
                        print("Không có kết nối mạng, không thể đăng xuất khỏi Realtime Database.")
                        event.accept()
                        return

                    # Chỉ xóa trạng thái online nếu device_id khớp
                    status = db.child("online_users").child(self.current_user_id).get(self.id_token).val()
                    if status and status.get("device_id") == self.device_id:
                        db.child("online_users").child(self.current_user_id).remove(self.id_token)
            except Exception as e:
                print(f"Lỗi khi đăng xuất khỏi Realtime Database: {e}")
        event.accept()