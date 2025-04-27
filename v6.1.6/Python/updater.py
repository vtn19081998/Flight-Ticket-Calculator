import os
import sys
import requests
import subprocess
import tempfile
import shutil
import time
import hashlib
import urllib.parse
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeyEvent

# Stylesheet giao diện với căn giữa và bo tròn
DOWNLOAD_DIALOG_STYLE = """
    QDialog {
        background-color: #F9FAFB;
        border: 1px solid rgba(0, 0, 0, 0.1);
        border-radius: 12px;
        padding: 10px;
        min-width: 350px;
        max-width: 350px;
        min-height: 120px;
        max-height: 120px;
    }
    QLabel {
        color: #1F2937;
        font-family: Roboto;
        font-size: 13px;
        font-weight: 500;
        text-align: center;
        width: 100%;
    }
    QProgressBar {
        border: none;
        border-radius: 10px;
        background-color: #E5E7EB;
        text-align: center;
        font-family: Roboto;
        font-size: 11px;
        color: #1F2937;
        height: 16px;
        max-width: 300px;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34D399, stop:1 #10B981);
        border-radius: 10px;
    }
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34D399, stop:1 #10B981);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 5px 10px;
        font-family: Roboto;
        font-size: 12px;
        transition: background 0.3s ease;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #059669, stop:1 #047857);
    }
"""

class UpdateManager:
    VERSION_URL = "https://raw.githubusercontent.com/vtn19081998/Flight-Ticket-Calculator/main/version.json"
    VALID_DOMAIN = "github.com"

    @staticmethod
    def check_for_update(current_version):
        try:
            response = requests.get(UpdateManager.VERSION_URL, timeout=5)
            response.raise_for_status()
            version_info = response.json()

            if not all(key in version_info for key in ["version", "download_url", "release_notes"]):
                raise ValueError("Thông tin phiên bản không hợp lệ")

            latest_version = version_info["version"]
            download_url = version_info["download_url"]
            release_notes = version_info["release_notes"]
            expected_hash = version_info.get("sha256_hash", None)

            parsed_url = urllib.parse.urlparse(download_url)
            if parsed_url.netloc != UpdateManager.VALID_DOMAIN:
                raise ValueError("URL tải xuống không hợp lệ")

            if UpdateManager.compare_versions(current_version, latest_version) < 0:
                return True, {
                    "version": latest_version,
                    "download_url": download_url,
                    "release_notes": release_notes,
                    "sha256_hash": expected_hash
                }
            return False, None

        except (requests.RequestException, ValueError):
            return False, None

    @staticmethod
    def compare_versions(current, latest):
        try:
            current_parts = list(map(int, current.split('.')))
            latest_parts = list(map(int, latest.split('.')))
            for i in range(max(len(current_parts), len(latest_parts))):
                c = current_parts[i] if i < len(current_parts) else 0
                l = latest_parts[i] if i < len(latest_parts) else 0
                if c < l:
                    return -1
                elif c > l:
                    return 1
            return 0
        except ValueError:
            return -1

    @staticmethod
    def compute_file_hash(file_path):
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

class DownloadThread(QThread):
    progress_updated = pyqtSignal(int, float, float)  # (progress_value, downloaded_size_mb, speed_mb_per_sec)
    download_completed = pyqtSignal(str, float)  # Thay downloaded_size thành MB
    download_failed = pyqtSignal(str)
    download_canceled = pyqtSignal()

    def __init__(self, download_url, temp_file, total_size):
        super().__init__()
        self.download_url = download_url
        self.temp_file = temp_file
        self.total_size = total_size
        self.canceled = False

    def run(self):
        try:
            response = requests.get(self.download_url, stream=True, timeout=10)
            response.raise_for_status()

            downloaded_size = 0
            chunk_size = 8192
            start_time = time.time()
            fake_progress = 0
            last_update_time = start_time

            with open(self.temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.canceled:
                        self.download_canceled.emit()
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        downloaded_size_mb = downloaded_size / 1048576
                        downloaded_size_mb = round(downloaded_size_mb, 2)

                        elapsed_time = time.time() - start_time
                        speed_bytes_per_sec = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                        speed_mb_per_sec = speed_bytes_per_sec / 1048576
                        speed_mb_per_sec = round(speed_mb_per_sec, 2)

                        if self.total_size > 0:
                            progress_value = min(int((downloaded_size / self.total_size) * 100), 100)
                        else:
                            fake_progress = min(99, int(50 * (1 - 1 / (1 + elapsed_time / 5))))
                            progress_value = fake_progress

                        current_time = time.time()
                        if current_time - last_update_time >= 0.1:  # Cập nhật giao diện mỗi 0.1 giây
                            self.progress_updated.emit(progress_value, downloaded_size_mb, speed_mb_per_sec)
                            last_update_time = current_time

            downloaded_size_mb = downloaded_size / 1048576
            downloaded_size_mb = round(downloaded_size_mb, 2)
            self.download_completed.emit(self.temp_file, downloaded_size_mb)
        except requests.RequestException as e:
            self.download_failed.emit(f"Không thể tải bản cập nhật: {str(e)}")
        except Exception as e:
            self.download_failed.emit(f"Đã xảy ra lỗi không mong muốn: {str(e)}")

    def cancel(self):
        self.canceled = True

class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tải bản cập nhật 📥")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setFixedSize(350, 120)
        self.setStyleSheet(DOWNLOAD_DIALOG_STYLE)

        # Layout để căn giữa
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        # Nhãn chính
        self.label = QLabel("Đang tải...", self)
        layout.addWidget(self.label)

        # Nhãn chi tiết
        self.detail_label = QLabel("💾 Đã tải: 0 MB | 🚀 Tốc độ: 0 MB/s", self)
        layout.addWidget(self.detail_label)

        # Thanh tiến trình
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()  # Bỏ qua phím Esc
        else:
            super().keyPressEvent(event)

    def set_label_text(self, text):
        self.label.setText(text)

    def set_detail_text(self, text):
        self.detail_label.setText(text)

    def set_progress_value(self, value):
        self.progress_bar.setValue(value)

class Updater:
    @staticmethod
    def prompt_for_update(version_info, parent):
        msg = (
            f"Đã tìm thấy bản cập nhật mới!\n\n"
            f"Phiên bản hiện tại: {parent.CURRENT_VERSION}\n"
            f"Phiên bản mới: {version_info['version']}\n\n"
            f"Thông tin cập nhật:\n{version_info['release_notes']}\n\n"
            f"Bạn có muốn tải và cài đặt bản cập nhật ngay bây giờ không?"
        )
        try:
            parent.show()
            parent.raise_()
            parent.activateWindow()

            msg_box = QMessageBox(parent)
            msg_box.setWindowTitle("Cập nhật ứng dụng")
            msg_box.setText(msg)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
            msg_box.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
            msg_box.show()
            reply = msg_box.exec()
            if reply == QMessageBox.StandardButton.Yes:
                Updater.download_update(version_info, parent)
        except Exception:
            pass

    @staticmethod
    def download_update(version_info, parent):
        def try_download():
            try:
                head_response = requests.head(version_info["download_url"], timeout=10)
                head_response.raise_for_status()
                total_size = int(head_response.headers.get('content-length', 0))
                total_size_mb = total_size / 1048576
                total_size_mb = round(total_size_mb, 2)

                dialog = DownloadDialog(parent)
                label_text = f"Đang tải ({total_size_mb} MB)..." if total_size > 0 else "Đang tải bản cập nhật..."
                dialog.set_label_text(label_text)
                dialog.show()
                QApplication.processEvents()

                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, "Flight_Ticket_Calculator_Update.exe")
                parent.download_thread = DownloadThread(version_info["download_url"], temp_file, total_size)

                def update_progress(progress_value, downloaded_size_mb, speed_mb_per_sec):
                    dialog.set_progress_value(progress_value)
                    dialog.set_detail_text(f"💾 Đã tải: {downloaded_size_mb} MB | 🚀 Tốc độ: {speed_mb_per_sec} MB/s")
                    QApplication.processEvents()

                def download_completed(temp_file_path, downloaded_size_mb):
                    documents_path = os.path.join(os.path.expanduser("~"), "Documents")
                    update_dir = os.path.join(documents_path, "Flight Ticket Calculator", "Update")
                    os.makedirs(update_dir, exist_ok=True)

                    final_file_path = os.path.join(update_dir, "Flight_Ticket_Calculator_Update.exe")
                    shutil.move(temp_file_path, final_file_path)

                    dialog.set_detail_text(f"🎉 Hoàn tất: {downloaded_size_mb} MB")
                    dialog.set_progress_value(100)

                    expected_hash = version_info.get("sha256_hash")
                    if expected_hash:
                        actual_hash = UpdateManager.compute_file_hash(final_file_path)
                        if actual_hash != expected_hash:
                            QMessageBox.critical(parent, "Lỗi", "File tải về không đúng, cập nhật bị hủy.")
                            os.remove(final_file_path)
                            dialog.close()
                            return

                    parent.download_thread.wait()
                    parent.download_thread = None

                    dialog.close()
                    QMessageBox.information(parent, "Thành công", "Bản cập nhật đã được tải về. Ứng dụng sẽ thoát và chạy bản cập nhật.")
                    Updater.install_update(final_file_path, parent)

                def download_failed(error_message):
                    parent.download_thread.wait()
                    parent.download_thread = None
                    dialog.close()

                    msg_box = QMessageBox(parent)
                    msg_box.setWindowTitle("Lỗi tải cập nhật")
                    msg_box.setText(error_message)
                    msg_box.setInformativeText("Bạn muốn thử lại hay hủy bỏ?")
                    msg_box.setIcon(QMessageBox.Icon.Critical)
                    retry_button = msg_box.addButton("Thử lại", QMessageBox.ButtonRole.AcceptRole)
                    cancel_button = msg_box.addButton("Hủy", QMessageBox.ButtonRole.RejectRole)
                    msg_box.setDefaultButton(retry_button)
                    msg_box.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
                    msg_box.exec()

                    if msg_box.clickedButton() == retry_button:
                        try_download()
                    else:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)

                def download_canceled():
                    dialog.close()
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    parent.download_thread.wait()
                    parent.download_thread = None

                parent.download_thread.progress_updated.connect(update_progress)
                parent.download_thread.download_completed.connect(download_completed)
                parent.download_thread.download_failed.connect(download_failed)
                parent.download_thread.download_canceled.connect(download_canceled)

                parent.download_thread.start()

            except requests.RequestException as e:
                dialog.close()
                QMessageBox.critical(parent, "Lỗi tải cập nhật", f"Không thể truy cập file cập nhật: {str(e)}")
            except Exception as e:
                dialog.close()
                QMessageBox.critical(parent, "Lỗi tải cập nhật", f"Đã xảy ra lỗi không mong muốn: {str(e)}")

        try_download()

    @staticmethod
    def install_update(new_exe_path, parent=None):
        try:
            batch_script = os.path.join(tempfile.gettempdir(), "update_flight_ticket_calculator.bat")
            with open(batch_script, 'w') as f:
                f.write(f"""
                @echo off
                timeout /t 2 /nobreak >nul
                start /wait "" "{new_exe_path}"
                del "{new_exe_path}"
                del "{batch_script}"
                """)

            subprocess.Popen([batch_script], shell=True)
            sys.exit(0)
        except PermissionError:
            QMessageBox.critical(parent, "Lỗi cài đặt cập nhật", "Không đủ quyền để cài đặt cập nhật. Vui lòng chạy ứng dụng với quyền admin.")
        except OSError as e:
            QMessageBox.critical(parent, "Lỗi cài đặt cập nhật", f"Lỗi hệ thống khi cài đặt cập nhật: {str(e)}")
        except Exception as e:
            QMessageBox.critical(parent, "Lỗi cài đặt cập nhật", f"Đã xảy ra lỗi không mong muốn: {str(e)}")