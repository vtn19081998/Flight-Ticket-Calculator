from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import Qt

class EditFlightDialog(QDialog):
    def __init__(self, cities, departure, arrival, parent=None):
        super().__init__(parent)
        self.cities = cities
        self.setWindowTitle("Chỉnh sửa tuyến bay")
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #F5F6FA; font-family: Arial; }
            QLabel { color: #333333; font-size: 12px; }
            QComboBox { border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px; background-color: white; font-size: 12px; }
            QPushButton { background-color: #4CAF50; color: white; border-radius: 5px; padding: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #45A049; }
        """)

        layout = QVBoxLayout()

        # Departure city
        departure_layout = QHBoxLayout()
        self.departure_label = QLabel("Thành phố khởi hành:")
        self.departure_combo = QComboBox()
        self.departure_combo.addItems([f"{city['name']} ({city['code']})" for city in cities])
        self.departure_combo.setCurrentText(departure if departure else "")
        departure_layout.addWidget(self.departure_label)
        departure_layout.addWidget(self.departure_combo)
        layout.addLayout(departure_layout)

        # Arrival city
        arrival_layout = QHBoxLayout()
        self.arrival_label = QLabel("Thành phố đến:")
        self.arrival_combo = QComboBox()
        self.arrival_combo.addItems([f"{city['name']} ({city['code']})" for city in cities])
        self.arrival_combo.setCurrentText(arrival if arrival else "")
        arrival_layout.addWidget(self.arrival_label)
        arrival_layout.addWidget(self.arrival_combo)
        layout.addLayout(arrival_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Xác nhận")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_route(self):
        departure = self.departure_combo.currentText()
        arrival = self.arrival_combo.currentText()
        return departure, arrival