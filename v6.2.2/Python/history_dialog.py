from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFontMetrics, QFont, QPixmap
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from datetime import datetime
import re
import json
import os

class HistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lịch sử nhập liệu")
        self.setWindowIcon(QIcon('images/icon.ico'))
        self.history = history
        self.selected_entry = None
        self.airlines_config = self.load_airlines_config()
        self.initUI()

    def load_airlines_config(self):
        try:
            with open('data/airlines_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {
                    airline['name']: {
                        'code': airline.get('code', ''),
                        'logo': airline.get('logo', '')
                    } for airline in config.get('airlines', [])
                }
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def initUI(self):
        layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "STT", "Thời gian", "Hãng", "Chuyến 1", "Khởi hành",
            "Hãng", "Chuyến 2", "Khởi hành", "Người lớn", "Trẻ em",
            "Sơ sinh", "Giá gốc", "Voucher", "Tổng cộng"
        ])
        self.table.horizontalHeader().setStyleSheet("background-color: #E8ECEF;")
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #CCCCCC; }
            QHeaderView::section { background-color: #E8ECEF; font-weight: bold; border: 1px solid #CCCCCC; }
        """)
        
        # Sort history by timestamp in descending order
        sorted_history = sorted(self.history, key=lambda x: x['timestamp'], reverse=True)
        self.table.setRowCount(len(sorted_history))
        
        self.table.verticalHeader().setVisible(False)
        
        for row, entry in enumerate(sorted_history):
            # Add STT (row number + 1)
            stt_item = QTableWidgetItem(str(row + 1))
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, stt_item)
            
            # Format timestamp into two lines: date and time
            timestamp = datetime.fromtimestamp(entry['timestamp'])
            date_str = timestamp.strftime('%Y-%m-%d')
            time_str = timestamp.strftime('%H:%M:%S')
            time_display = f"{date_str}\n{time_str}"
            self.table.setItem(row, 1, QTableWidgetItem(time_display))
            
            # Determine airlines for logo display
            airline1 = None
            airline2 = None
            flight_number1 = entry['flight_number1']
            flight_number2 = entry['flight_number2']
            detected_airlines = entry['detected_airlines']
            
            for airline, config in self.airlines_config.items():
                if flight_number1 and flight_number1.upper().startswith(config.get('code', '').upper()):
                    airline1 = airline
                if entry['is_round_trip'] and flight_number2 and flight_number2.upper().startswith(config.get('code', '').upper()):
                    airline2 = airline
            
            if not airline1 and detected_airlines:
                airline1 = detected_airlines[0]
            if entry['is_round_trip'] and not airline2 and len(detected_airlines) > 1:
                airline2 = detected_airlines[1]
            elif entry['is_round_trip'] and not airline2 and detected_airlines:
                airline2 = detected_airlines[0]
            
            # Add logo for flight 1
            logo1_item = QTableWidgetItem()
            logo1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if airline1 and self.airlines_config.get(airline1, {}).get('logo'):
                logo_path = self.airlines_config[airline1]['logo']
                if os.path.exists(logo_path):
                    logo1_item.setData(Qt.ItemDataRole.DecorationRole, QIcon(logo_path))
            self.table.setItem(row, 2, logo1_item)
            
            # Add flight 1
            flight1_display = entry['flight1'].replace('<span>', '').replace('</span>', '')
            flight1_display = re.sub(r'<img\s+src=["\']images/arrow\.png["\']\s+width=["\']11["\']\s*>', '→', flight1_display)
            self.table.setItem(row, 3, QTableWidgetItem(flight1_display))
            
            # Add time for flight 1
            time1_display = re.sub(r'<[^>]*>', '', entry['time1']) if entry['time1'] else ""
            time1_item = QTableWidgetItem()
            time1_item.setData(Qt.ItemDataRole.DisplayRole, time1_display)
            time1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, time1_item)
            
            # Add logo for flight 2
            logo2_item = QTableWidgetItem()
            logo2_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if entry['is_round_trip'] and airline2 and self.airlines_config.get(airline2, {}).get('logo'):
                logo_path = self.airlines_config[airline2]['logo']
                if os.path.exists(logo_path):
                    logo2_item.setData(Qt.ItemDataRole.DecorationRole, QIcon(logo_path))
            self.table.setItem(row, 5, logo2_item)
            
            # Add flight 2
            flight2_display = entry['flight2'].replace('<span>', '').replace('</span>', '') if entry['is_round_trip'] else ""
            if entry['is_round_trip']:
                flight2_display = re.sub(r'<img\s+src=["\']images/arrow\.png["\']\s+width=["\']11["\']\s*>', '→', flight2_display)
            self.table.setItem(row, 6, QTableWidgetItem(flight2_display))
            
            # Add time for flight 2
            time2_display = re.sub(r'<[^>]*>', '', entry['time2']) if entry['is_round_trip'] and entry['time2'] else ""
            time2_item = QTableWidgetItem()
            time2_item.setData(Qt.ItemDataRole.DisplayRole, time2_display)
            time2_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, time2_item)
            
            self.table.setItem(row, 8, QTableWidgetItem(entry['adult']))
            self.table.setItem(row, 9, QTableWidgetItem(entry['child']))
            self.table.setItem(row, 10, QTableWidgetItem(entry['infant']))
            
            # Add original price column
            self.table.setItem(row, 11, QTableWidgetItem(entry['price']))
            
            # Add voucher column with % suffix
            voucher_text = f"{entry['discount']}%" if entry['discount'] else "0%"
            self.table.setItem(row, 12, QTableWidgetItem(voucher_text))
            
            # Simplify total column, remove "VNĐ"
            total_text = entry['total'].replace("Tổng chi phí toàn hành trình: ", "").replace(" VNĐ", "")
            self.table.setItem(row, 13, QTableWidgetItem(total_text))
        
        # Auto-resize columns and rows to fit content
        self.table.resizeRowsToContents()
        
        # Calculate column widths and adjust logo sizes
        font = QFont("Arial", 9)
        metrics = QFontMetrics(font)
        padding = 10
        
        for col in range(self.table.columnCount()):
            max_width = 0
            # Calculate header width
            header_text = self.table.horizontalHeaderItem(col).text()
            header_width = metrics.boundingRect(header_text).width() + padding
            max_width = max(max_width, header_width)
            
            # Calculate content width for non-logo columns
            if col not in [2, 5]:  # Skip logo columns
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, col)
                    if item:
                        text = item.text()
                        # Handle HTML content by splitting into lines
                        lines = text.replace('<br>', '\n').split('\n')
                        for line in lines:
                            # Remove HTML tags for width calculation
                            clean_line = re.sub(r'<[^>]+>', '', line)
                            line_width = metrics.boundingRect(clean_line).width() + padding
                            max_width = max(max_width, line_width)
            
            self.table.setColumnWidth(col, max_width)
        
        # Adjust logo columns to be larger
        logo_column_width = 50  # Increased for larger logos
        self.table.setColumnWidth(2, logo_column_width)
        self.table.setColumnWidth(5, logo_column_width)
        
        # Adjust logo sizes to fit cell dimensions
        for row in range(self.table.rowCount()):
            row_height = self.table.rowHeight(row)
            for col in [2, 5]:  # Logo columns
                item = self.table.item(row, col)
                if item and item.data(Qt.ItemDataRole.DecorationRole):
                    icon = item.data(Qt.ItemDataRole.DecorationRole)
                    pixmap = icon.pixmap(1000)  # Get original pixmap
                    cell_size = min(row_height, logo_column_width) - 4  # Subtract padding
                    scaled_pixmap = pixmap.scaled(
                        cell_size, cell_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    item.setData(Qt.ItemDataRole.DecorationRole, QIcon(scaled_pixmap))
                    # Ensure the icon is centered and sized correctly
                    self.table.setIconSize(scaled_pixmap.size())
        
        # Calculate total table width
        total_width = sum(self.table.columnWidth(i) for i in range(self.table.columnCount()))
        total_width += self.table.verticalHeader().width() + 2
        
        # Calculate total table height
        total_height = self.table.horizontalHeader().height()
        total_height += sum(self.table.rowHeight(i) for i in range(self.table.rowCount()))
        total_height += 2
        
        # Disable scrollbars and set fixed table size
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setFixedSize(total_width, total_height)
        
        # Set window size to fit table
        self.setFixedSize(total_width + 20, total_height + 40)
        
        self.table.cellDoubleClicked.connect(self.accept_selection)
        
        layout.addWidget(self.table)
        self.setLayout(layout)

    def accept_selection(self):
        selected_rows = self.table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            # Map back to original history index
            sorted_history = sorted(self.history, key=lambda x: x['timestamp'], reverse=True)
            self.selected_entry = sorted_history[row]
            self.accept()