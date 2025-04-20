import logging
import os
from datetime import datetime
from PyQt6.QtCore import QtMsgType

def get_logger():
    """Khởi tạo và cấu hình logger."""
    logger = logging.getLogger("FlightTicketCalculator")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

def qt_message_handler(msg_type, context, msg):
    """Xử lý các thông báo từ Qt và ghi vào log."""
    logger = get_logger()
    log_levels = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL
    }
    log_level = log_levels.get(msg_type, logging.INFO)
    logger.log(log_level, f"Qt: {msg} (file: {context.file}, line: {context.line}, function: {context.function})")

def setup_logging():
    """Thiết lập logging ban đầu."""
    logger = get_logger()
    logger.info("Ứng dụng khởi động, thiết lập logging hoàn tất.")