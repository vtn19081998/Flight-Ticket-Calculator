from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import Qt

class SelectAirportDialog(QDialog):
    def __init__(self, cities, parent=None):
        super().__init__(parent)
        self.cities = cities
        self.setWindowTitle("Chọn sân bay")
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #F5F6FA; font-family: Arial; }
            QLabel { color: #333333; font-size: 12px; }
            QComboBox { border: 1px solid #CCCCCC; border-radius: 5px; padding: 3px; background-color: white; font-size: 12px; }
            QPushButton { background-color: #4CAF50; color: white; border-radius: 5px; padding: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #45A049; }
        """)

        layout = QVBoxLayout()

        # Airport selection
        airport_layout = QHBoxLayout()
        self.airport_label = QLabel("Chọn sân bay:")
        self.airport_combo = QComboBox()
        self.airport_combo.addItems([f"{city['name']} ({city['code']})" for city in cities])
        airport_layout.addWidget(self.airport_label)
        airport_layout.addWidget(self.airport_combo)
        layout.addLayout(airport_layout)

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

    @property
    def selected_city(self):
        selected_text = self.airport_combo.currentText()
        for city in self.cities:
            if f"{city['name']} ({city['code']})" == selected_text:
                return city
        return None