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
        self.setFixedSize(400, 400)
        self.setWindowIcon(QIcon('images/icon.ico'))

        self.current_user = None
        self.current_user_id = None
        self.id_token = None
        self.refresh_token = None

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

    def process_login(self, username, password):
        try:
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
                QMessageBox.information(self, "Đăng nhập thành công", "Chào mừng Quản trị viên!")
                self.accept()
                return

            if not online:
                QMessageBox.warning(self, "Lỗi", "Không có kết nối Internet.")
                return

            user = auth.sign_in_with_email_and_password(username, password)
            self.id_token = user['idToken']
            self.refresh_token = user['refreshToken']

            status = db.child("online_users").child(user['localId']).get(self.id_token)
            if status.val() == "online":
                QMessageBox.warning(self, "Lỗi", "Tài khoản này đang được sử dụng ở một thiết bị khác.")
                return

            db.child("online_users").child(user['localId']).set("online", self.id_token)

            self.current_user = username
            self.current_user_id = user['localId']
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
                    db.child("online_users").child(self.current_user_id).remove(self.id_token)
            except Exception as e:
                print(f"Lỗi khi đăng xuất khỏi Realtime Database: {e}")
        event.accept()