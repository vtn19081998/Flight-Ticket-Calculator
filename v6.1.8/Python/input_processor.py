import re
import json
import os
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QTimer
from trie import Trie
from edit_flight_dialog import EditFlightDialog
from select_airport_dialog import SelectAirportDialog

class InputProcessor:
    # Danh sách model hợp lệ cho từng nhà sản xuất
    VALID_AIRCRAFT_TYPES = {
        "Boeing": ["737", "737 MAX", "737-800", "737-900", "747", "747-400", "747-8", "777", "77W", "777-300ER", "787", "787-8", "787-9", "Dreamliner", "77L", "7M8", "73H", "738", "781", "788"],
        "Airbus": ["A320", "A320neo", "A318", "A319", "A321", "A321neo", "A330", "A330-200", "A330-300", "A330-900", "A350", "A350-900", "A350-900ULR", "A380", "A359" "A32Q", "A32N", "A333"],
        "Embraer": ["E175", "E190-E2", "E195-E2", "E90"],
        "Bombardier": ["CRJ-200", "CRJ-900", "Q400", "Dash 8-100", "Dash 8-200", "Dash 8-300"],
        "ATR": ["ATR 72", "ATR 72-600", ""],
        "McDonnell Douglas": ["MD-80", "DC-3"],
        "": ["73E", "ATR"]
    }

    _route_pattern = None
    _alt_route_pattern = None
    _vn_city_pattern = None
    _intl_city_pattern = None
    _price_pattern = re.compile(r'\d{1,3}(?:[.,]\d{3})*(?:\.\d{2})?')

    def __init__(self, airlines_config, cities_file='data/cities.json'):
        self.airlines_config = airlines_config
        self.detected_airlines = []
        self.is_round_trip = False
        self.clipboard_cache = {}
        self.cache_timer = QTimer()
        self.cache_timer.timeout.connect(self.clear_cache)
        self.cache_timer.start(300000)  # Clear cache after 5 minutes

        # Compile airline codes pattern
        airline_codes = [details['code'] for details in airlines_config.values() if details.get('code')]
        codes_pattern = '|'.join(re.escape(code) for code in airline_codes)
        self._flight_pattern = re.compile(
            rf'(?:\s*({codes_pattern})[-|\s]*(\d{{3,4}})(?=\s|$|[^\d]))',
            re.IGNORECASE
        )
        self._note_flight_pattern = re.compile(
            rf'({codes_pattern})(\d{{3,4}})\s*:\s*([a-zA-Z\s]+(?:\s*\([^)]+\))?)',
            re.IGNORECASE
        )

        # Date, time, plane type, and duration patterns
        self._day_date_pattern = re.compile(
            r'(thứ\s*(?:hai|ba|tư|năm|sáu|bảy)|chủ nhật|c\.nhật|t\.\w+)\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
            re.IGNORECASE
        )
        self._standalone_date_pattern = re.compile(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)')
        self._time_range_pattern = re.compile(
            r'(\d{1,2}:\d{2})\s*(?:-|→)\s*(\d{1,2}:\d{2})',
            re.IGNORECASE
        )
        self._plane_type_pattern = re.compile(
            r'(?:(?:máy bay\s*:\s*|\()|(?:^|\s))((Boeing|Airbus|Embraer|Bombardier|ATR|McDonnell\s*Douglas)(?:\s+([^\s)]+))?)(?=\s|$|\))',
            re.IGNORECASE
        )
        self._duration_pattern = re.compile(r'(\d+)\s*giờ(?:\+(\d+)p)?', re.IGNORECASE)

        # Load cities and compile regex patterns
        self.cities, self.city_trie = self._load_cities_and_compile_regex(cities_file)
        self.error_messages = []

    @classmethod
    def _load_cities_and_compile_regex(cls, cities_file):
        try:
            with open(cities_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cities_data = data.get('cities', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Không thể đọc file thành phố {cities_file}: {e}")

        seen = set()
        unique_cities = []
        for city in cities_data:
            city_name = city.get('city_name', city.get('name', '')).strip().lower()
            city_code = city.get('code', '').strip().upper()
            display_name = city.get('name', '').strip()
            aliases = city.get('aliases', [])
            if city_name and (city_name, city_code) not in seen and city_code:
                seen.add((city_name, city_code))
                unique_cities.append({
                    'name': display_name,
                    'city_name': city_name,
                    'code': city_code,
                    'aliases': aliases,
                    'country': city.get('country', '')
                })

        if not unique_cities:
            raise ValueError("Danh sách thành phố trống sau khi loại bỏ trùng lặp.")

        trie = Trie()
        for city in unique_cities:
            trie.insert(city['city_name'].lower())
            for alias in city['aliases']:
                trie.insert(alias.lower())

        vn_cities = [city for city in unique_cities if city['country'].lower() == 'vietnam']
        intl_cities = [city for city in unique_cities if city['country'].lower() != 'vietnam']

        vn_city_pattern = '|'.join(
            f"(?:(?:tp\\s*)?{re.escape(city['city_name'].lower().replace('tp ', ''))}(?:\\s*\\({re.escape(city['code'])}\\)(?:\\s*\\(t[1-4]\\))?|\\s*\\(t[1-4]\\))?|(?:tp\\s*)?{re.escape(city['city_name'].lower().replace('tp ', ''))}|{'|'.join(re.escape(alias) for alias in city['aliases'])})"
            for city in vn_cities
        )
        intl_city_pattern = '|'.join(
            f"({re.escape(city['city_name'].lower().replace('tp ', ''))}(?:\\s*\\({re.escape(city['code'])}\\)(?:\\s*\\(t[1-4]\\))?|\\s*\\(t[1-4]\\))?|{re.escape(city['city_name'].lower().replace('tp ', ''))}|{'|'.join(re.escape(alias) for alias in city['aliases'])})"
            for city in intl_cities
        )

        cls._vn_city_pattern = re.compile(vn_city_pattern, re.IGNORECASE) if vn_city_pattern else None
        cls._intl_city_pattern = re.compile(intl_city_pattern, re.IGNORECASE) if intl_city_pattern else None

        cities_pattern = '|'.join(
            f"(?:(?:tp\\s*)?{re.escape(city['city_name'].lower().replace('tp ', ''))}(?:\\s*\\({re.escape(city['code'])}\\)(?:\\s*\\(t[1-4]\\))?|\\s*\\(t[1-4]\\))?|(?:tp\\s*)?{re.escape(city['city_name'].lower().replace('tp ', ''))}|{'|'.join(re.escape(alias) for alias in city['aliases'])})"
            for city in unique_cities
        )

        cls._route_pattern = re.compile(
            rf'({cities_pattern})\s*(?:[-→]|\s+|\t)+({cities_pattern})\s*(?:thứ\s*(?:hai|ba|tư|năm|sáu|bảy)|chủ nhật|c\.nhật|t\.\w+|\d{{1,2}}/\d{{1,2}})',
            re.IGNORECASE
        )

        cls._alt_route_pattern = re.compile(
            rf'([a-zA-Z\s]+?)(?:\s*(?:to|→|-)\s*|\s+)([a-zA-Z\s]+?)(?:thứ\s*(?:hai|ba|tư|năm|sáu|bảy)|chủ nhật|c\.nhật|t\.\w+|\d{{1,2}}/\d{{1,2}})|([A-Z]{{3}})\s*-\s*([A-Z]{{3}})',
            re.IGNORECASE
        )

        return unique_cities, trie

    def clear_cache(self):
        self.clipboard_cache.clear()

    def normalize_airline_name(self, name):
        if not name or not isinstance(name, str):
            return None
        normalized_input = ' '.join(name.strip().lower().split())
        for airline_name, details in self.airlines_config.items():
            airline_name_lower = airline_name.lower()
            airline_code = details.get('code', '').lower()
            if normalized_input == airline_name_lower or normalized_input == airline_code:
                return airline_name
            if normalized_input.replace(' ', '') == airline_name_lower.replace(' ', ''):
                return airline_name
        return None

    def display_airline_name(self, normalized_name):
        if not normalized_name or not isinstance(normalized_name, str):
            return "Invalid airline name"
        if normalized_name in self.airlines_config:
            return normalized_name
        return f"Airline '{normalized_name}' not found in configuration"

    def get_airline_key(self, airline_name):
        normalized_name = self.normalize_airline_name(airline_name)
        if normalized_name in self.airlines_config:
            return normalized_name
        return None

    def load_logo(self, label, airline_name, parent):
        if not airline_name:
            label.setText("❓")
            self.error_messages.append("Không có tên hãng bay để tải logo.")
            return
        airline_key = self.get_airline_key(airline_name)
        if not airline_key:
            label.setText("❓")
            self.error_messages.append(f"Không tìm thấy hãng bay {airline_name} trong cấu hình.")
            return
        logo_path = self.airlines_config[airline_key]['logo']
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                label.setPixmap(pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio))
                label.setText("")
            else:
                label.setText("❓")
                self.error_messages.append(f"Không thể tải logo: {logo_path}")
        else:
            label.setText("❓")
            self.error_messages.append(f"File logo không tồn tại: {logo_path}")

    def select_airport(self, city_name, parent):
        matched_cities = [city for city in self.cities if city['city_name'].lower() == city_name.lower()]
        if len(matched_cities) > 1:
            dialog = SelectAirportDialog(matched_cities, parent)
            if dialog.exec() == QDialog.Accepted:
                return dialog.selected_city
        return matched_cities[0] if matched_cities else None

    def validate_aircraft_type(self, manufacturer, model=None):
        """Kiểm tra tính hợp lệ của loại máy bay dựa trên NSX và model."""
        if not manufacturer or not isinstance(manufacturer, str):
            return None
        manufacturer = manufacturer.strip().title()
        if manufacturer not in self.VALID_AIRCRAFT_TYPES:
            return None
        if model:
            model = model.strip().lower()
            if model in [m.lower() for m in self.VALID_AIRCRAFT_TYPES[manufacturer]]:
                return f"{manufacturer} {model.title()}"
        return manufacturer

    def extract_from_clipboard(self, parent, input_price, input_flight1, input_time1,
                              label_flight_number1, input_flight_number1, input_plane_type1,
                              input_flight2, input_time2, label_flight_number2,
                              input_flight_number2, input_plane_type2, round_trip_checkbox):
        self.error_messages = []
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text:
            self.error_messages.append("Clipboard không chứa văn bản!")
            self.show_errors(parent)
            return

        cache_key = hash(text)
        if cache_key in self.clipboard_cache:
            self.apply_cached_data(parent, self.clipboard_cache[cache_key], input_price, input_flight1, input_time1,
                                  label_flight_number1, input_flight_number1, input_plane_type1,
                                  input_flight2, input_time2, label_flight_number2,
                                  input_flight_number2, input_plane_type2, round_trip_checkbox)
            return

        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        normalized_text = " ".join(text.split()).lower()

        # Process price
        prices = self._price_pattern.findall(text)
        if prices:
            max_price = max(float(p.replace(',', '').replace('.', '')) for p in prices)
            input_price.setText("{:,.0f}".format(max_price))
            parent.price_multiplied = True
        else:
            self.error_messages.append("Không tìm thấy giá vé trong văn bản.")

        # Process airline
        self.detected_airlines = []
        for airline in self.airlines_config:
            airline_name_lower = airline.lower()
            airline_code = self.airlines_config[airline].get('code', '').lower()
            if airline_name_lower in normalized_text or airline_code in normalized_text:
                self.detected_airlines.append(airline)
        if not self.detected_airlines:
            self.error_messages.append("Không nhận diện được hãng bay từ văn bản.")

        # Process routes
        routes = []
        if self._route_pattern:
            routes = self._route_pattern.findall(normalized_text)
        if not routes and self._alt_route_pattern:
            alt_routes = self._alt_route_pattern.findall(normalized_text)
            for dep, arr, code1, code2 in alt_routes:
                if dep and arr:
                    routes.append((dep, arr))
                elif code1 and code2:
                    dep_city = next((c['city_name'] for c in self.cities if c['code'].lower() == code1.lower()), code1)
                    arr_city = next((c['city_name'] for c in self.cities if c['code'].lower() == code2.lower()), code2)
                    routes.append((dep_city, arr_city))

        self.is_round_trip = len(routes) >= 2
        round_trip_checkbox.setChecked(self.is_round_trip)
        parent.flight2_group.setVisible(self.is_round_trip)

        if routes:
            departure_city1 = self.clean_city_name(routes[0][0], parent)
            arrival_city1 = self.clean_city_name(routes[0][1], parent)
            if not (departure_city1 and arrival_city1):
                dialog = EditFlightDialog(self.cities, departure_city1 or routes[0][0], arrival_city1 or routes[0][1], parent)
                if dialog.exec() == QDialog.Accepted:
                    departure_city1, arrival_city1 = dialog.get_route()
            input_flight1.setText(
                f"<span>{departure_city1.upper()}</span> <img src='images/arrow.png' width='11'> <span>{arrival_city1.upper()}</span>"
            )
            if len(routes) > 1 and self.is_round_trip:
                departure_city2 = self.clean_city_name(routes[1][0], parent)
                arrival_city2 = self.clean_city_name(routes[1][1], parent)
                if not (departure_city2 and arrival_city2):
                    dialog = EditFlightDialog(self.cities, departure_city2 or routes[1][0], arrival_city2 or routes[1][1], parent)
                    if dialog.exec() == QDialog.Accepted:
                        departure_city2, arrival_city2 = dialog.get_route()
                input_flight2.setText(
                    f"<span>{departure_city2.upper()}</span> <img src='images/arrow.png' width='11'> <span>{arrival_city2.upper()}</span>"
                )

        # Process date and time
        day_map = {
            'thứ hai': 'THỨ HAI', 'thứ ba': 'THỨ BA', 'thứ tư': 'THỨ TƯ', 'thứ năm': 'THỨ NĂM',
            'thứ sáu': 'THỨ SÁU', 'thứ bảy': 'THỨ BẢY', 'chủ nhật': 'CHỦ NHẬT',
            't.hai': 'THỨ HAI', 't.ba': 'THỨ BA', 't.tư': 'THỨ TƯ', 't.năm': 'THỨ NĂM',
            't.sáu': 'THỨ SÁU', 't.bảy': 'THỨ BẢY', 'c.nhật': 'CHỦ NHẬT'
        }
        day_date_matches = self._day_date_pattern.findall(text.lower())
        standalone_dates = self._standalone_date_pattern.findall(text)
        time_ranges = self._time_range_pattern.findall(text)

        days = []
        dates = []
        for day, date in day_date_matches:
            days.append(day_map.get(day.strip().lower(), day.strip().upper()))
            dates.append(date.upper())
        if not day_date_matches:
            for date in standalone_dates:
                dates.append(date.upper())
            if not dates:
                dates = ['??/??', '??/??'] if self.is_round_trip else ['??/??']
            days = ['??', '??'] if self.is_round_trip else ['??']

        if days:
            if time_ranges:
                time_start1, time_end1 = time_ranges[0]
                formatted_time1 = f"{days[0]} | <b>{dates[0]}</b> | <b>{time_start1.upper()}</b> - {time_end1.upper()}"
            else:
                formatted_time1 = f"{days[0]} | <b>{dates[0]}</b> | <b>??:??</b> - ??:??"
                self.error_messages.append("Không tìm thấy thời gian bay cho chuyến bay 1.")
            input_time1.setText(formatted_time1)
            if self.is_round_trip and len(days) > 1 and len(dates) > 1:
                if len(time_ranges) > 1:
                    time_start2, time_end2 = time_ranges[1]
                    formatted_time2 = f"{days[1]} | <b>{dates[1]}</b> | <b>{time_start2.upper()}</b> - {time_end2.upper()}"
                else:
                    formatted_time2 = f"{days[1]} | <b>{dates[1]}</b> | <b>??:??</b> - ??:??"
                    self.error_messages.append("Không tìm thấy thời gian bay cho chuyến bay 2.")
                input_time2.setText(formatted_time2)

        # Extract and assign plane types
        plane_types = self._plane_type_pattern.findall(normalized_text)

        # Initialize plane type assignments
        plane_type1 = None
        plane_type2 = None

        if not self.is_round_trip:
            # One-way flight
            if plane_types and len(plane_types[0]) >= 2:
                manufacturer = plane_types[0][1]
                model = plane_types[0][2] if len(plane_types[0]) > 2 and plane_types[0][2] else None
                plane_type1 = self.validate_aircraft_type(manufacturer, model)
                if plane_type1:
                    input_plane_type1.setText(plane_type1.upper())
                    if model and not self.validate_aircraft_type(manufacturer, model):
                        self.error_messages.append(f"Model máy bay '{model}' của '{manufacturer}' không hợp lệ.")
                else:
                    input_plane_type1.setText("Đang cập nhật")
                    self.error_messages.append(f"Nhà sản xuất '{manufacturer}' không hợp lệ.")
            else:
                input_plane_type1.setText("Đang cập nhật")
                self.error_messages.append("Không tìm thấy loại máy bay cho chuyến bay 1.")
        else:
            # Round-trip flight
            if len(plane_types) >= 2 and len(plane_types[0]) >= 2 and len(plane_types[1]) >= 2:
                # Two plane types found
                manufacturer1 = plane_types[0][1]
                model1 = plane_types[0][2] if len(plane_types[0]) > 2 and plane_types[0][2] else None
                manufacturer2 = plane_types[1][1]
                model2 = plane_types[1][2] if len(plane_types[1]) > 2 and plane_types[1][2] else None
                plane_type1 = self.validate_aircraft_type(manufacturer1, model1)
                plane_type2 = self.validate_aircraft_type(manufacturer2, model2)
                
                if plane_type1:
                    input_plane_type1.setText(plane_type1.upper())
                    if model1 and not self.validate_aircraft_type(manufacturer1, model1):
                        self.error_messages.append(f"Model máy bay '{model1}' của '{manufacturer1}' cho chuyến bay 1 không hợp lệ.")
                else:
                    input_plane_type1.setText("Đang cập nhật")
                    self.error_messages.append(f"Nhà sản xuất '{manufacturer1}' cho chuyến bay 1 không hợp lệ.")
                
                if plane_type2:
                    input_plane_type2.setText(plane_type2.upper())
                    if model2 and not self.validate_aircraft_type(manufacturer2, model2):
                        self.error_messages.append(f"Model máy bay '{model2}' của '{manufacturer2}' cho chuyến bay 2 không hợp lệ.")
                else:
                    input_plane_type2.setText("Đang cập nhật")
                    self.error_messages.append(f"Nhà sản xuất '{manufacturer2}' cho chuyến bay 2 không hợp lệ.")
            elif len(plane_types) == 1 and len(plane_types[0]) >= 2:
                # One plane type found, determine which flight it belongs to
                flight_codes = [match.group(0) for match in self._flight_pattern.finditer(normalized_text)]
                manufacturer = plane_types[0][1]
                model = plane_types[0][2] if len(plane_types[0]) > 2 and plane_types[0][2] else None
                plane_type = self.validate_aircraft_type(manufacturer, model)
                plane_type_pos = normalized_text.find(manufacturer.lower())
                assigned = False

                if len(flight_codes) >= 2:
                    flight1_code_pos = normalized_text.find(flight_codes[0].lower())
                    flight2_code_pos = normalized_text.find(flight_codes[1].lower())
                    if plane_type_pos < flight2_code_pos:
                        # Plane type appears before second flight code, assign to flight 1
                        plane_type1 = plane_type
                        input_plane_type1.setText(plane_type1.upper() if plane_type1 else "Đang cập nhật")
                        input_plane_type2.setText("Đang cập nhật")
                        if plane_type1 and model and not self.validate_aircraft_type(manufacturer, model):
                            self.error_messages.append(f"Model máy bay '{model}' của '{manufacturer}' cho chuyến bay 1 không hợp lệ.")
                        if not plane_type1:
                            self.error_messages.append(f"Nhà sản xuất '{manufacturer}' cho chuyến bay 1 không hợp lệ.")
                        self.error_messages.append("Không tìm thấy loại máy bay cho chuyến bay 2.")
                        assigned = True
                    else:
                        # Plane type appears after second flight code, assign to flight 2
                        plane_type2 = plane_type
                        input_plane_type1.setText("Đang cập nhật")
                        input_plane_type2.setText(plane_type2.upper() if plane_type2 else "Đang cập nhật")
                        if plane_type2 and model and not self.validate_aircraft_type(manufacturer, model):
                            self.error_messages.append(f"Model máy bay '{model}' của '{manufacturer}' cho chuyến bay 2 không hợp lệ.")
                        if not plane_type2:
                            self.error_messages.append(f"Nhà sản xuất '{manufacturer}' cho chuyến bay 2 không hợp lệ.")
                        self.error_messages.append("Không tìm thấy loại máy bay cho chuyến bay 1.")
                        assigned = True

                if not assigned:
                    # Fallback: assign to flight 1 if context unclear
                    plane_type1 = plane_type
                    input_plane_type1.setText(plane_type1.upper() if plane_type1 else "Đang cập nhật")
                    input_plane_type2.setText("Đang cập nhật")
                    if plane_type1 and model and not self.validate_aircraft_type(manufacturer, model):
                        self.error_messages.append(f"Model máy bay '{model}' của '{manufacturer}' cho chuyến bay 1 không hợp lệ.")
                    if not plane_type1:
                        self.error_messages.append(f"Nhà sản xuất '{manufacturer}' cho chuyến bay 1 không hợp lệ.")
                    self.error_messages.append("Không tìm thấy loại máy bay cho chuyến bay 2.")
            else:
                # No plane types found or invalid structure
                input_plane_type1.setText("Đang cập nhật")
                input_plane_type2.setText("Đang cập nhật")
                self.error_messages.append("Không tìm thấy loại máy bay cho chuyến bay 1.")
                self.error_messages.append("Không tìm thấy loại máy bay cho chuyến bay 2.")

        # Process flight codes
        note_flights = self._note_flight_pattern.findall(normalized_text)
        flight_codes = []
        self.detected_airlines = []
        for flight_code, flight_num, airline_name in note_flights:
            full_code = f"{flight_code.upper()}{flight_num}"
            normalized_airline = self.normalize_airline_name(airline_name)
            if normalized_airline:
                flight_codes.append((full_code, normalized_airline))
                if normalized_airline not in self.detected_airlines:
                    self.detected_airlines.append(normalized_airline)

        if not flight_codes:
            flight_matches = self._flight_pattern.findall(normalized_text)
            for flight_code, flight_num in flight_matches:
                full_code = f"{flight_code.upper()}{flight_num}"
                normalized_airline = self.normalize_airline_name(flight_code)
                if normalized_airline:
                    flight_codes.append((full_code, normalized_airline))
                    if normalized_airline not in self.detected_airlines:
                        self.detected_airlines.append(normalized_airline)

        if not self.detected_airlines:
            for airline in self.airlines_config:
                airline_name_lower = airline.lower()
                airline_code = self.airlines_config[airline].get('code', '').lower()
                if airline_name_lower in normalized_text or airline_code in normalized_text:
                    self.detected_airlines.append(airline)
            if not self.detected_airlines:
                self.error_messages.append("Không nhận diện được hãng bay từ văn bản.")

        if flight_codes:
            if len(flight_codes) >= 1:
                full_code1, airline_name1 = flight_codes[0]
                if not airline_name1 and self.detected_airlines:
                    airline_name1 = self.detected_airlines[0]
                if not airline_name1:
                    for airline, config in self.airlines_config.items():
                        if full_code1.upper().startswith(config.get('code', '').upper()):
                            airline_name1 = airline
                            break
                if airline_name1:
                    display_name1 = self.display_airline_name(airline_name1)
                    flight_info1 = f"{display_name1.upper()} | {full_code1}"
                    input_flight_number1.setText(flight_info1)
                    label_flight_number1.clear()
                    self.load_logo(label_flight_number1, airline_name1, parent)
                else:
                    input_flight_number1.setText(f"UNKNOWN | {full_code1}")
                    label_flight_number1.setText("❓")
                    self.error_messages.append(f"Không nhận diện được hãng bay cho mã {full_code1}")

            if len(flight_codes) >= 2 and self.is_round_trip:
                full_code2, airline_name2 = flight_codes[1]
                if not airline_name2 and self.detected_airlines:
                    airline_name2 = self.detected_airlines[0]
                if not airline_name2:
                    for airline, config in self.airlines_config.items():
                        if full_code2.upper().startswith(config.get('code', '').upper()):
                            airline_name2 = airline
                            break
                if airline_name2:
                    display_name2 = self.display_airline_name(airline_name2)
                    flight_info2 = f"{display_name2.upper()} | {full_code2}"
                    input_flight_number2.setText(flight_info2)
                    label_flight_number2.clear()
                    self.load_logo(label_flight_number2, airline_name2, parent)
                else:
                    input_flight_number2.setText(f"UNKNOWN | {full_code2}")
                    label_flight_number2.setText("❓")
                    self.error_messages.append(f"Không nhận diện được hãng bay cho mã {full_code2}")
        else:
            self.error_messages.append("Không tìm thấy mã chuyến bay nào trong văn bản.")

        # Save to cache
        self.clipboard_cache[cache_key] = {
            'price': input_price.text(),
            'flight1': input_flight1.text(),
            'time1': input_time1.text(),
            'flight_number1': input_flight_number1.text(),
            'plane_type1': input_plane_type1.text(),
            'flight2': input_flight2.text(),
            'time2': input_time2.text(),
            'flight_number2': input_flight_number2.text(),
            'plane_type2': input_plane_type2.text(),
            'is_round_trip': self.is_round_trip,
            'detected_airlines': self.detected_airlines
        }

        self.show_errors(parent)

    def show_errors(self, parent):
        if self.error_messages:
            QMessageBox.warning(parent, "Cảnh báo", "\n".join(self.error_messages))

    def apply_cached_data(self, parent, data, input_price, input_flight1, input_time1,
                         label_flight_number1, input_flight_number1, input_plane_type1,
                         input_flight2, input_time2, label_flight_number2,
                         input_flight_number2, input_plane_type2, round_trip_checkbox):
        input_price.setText(data['price'])
        input_flight1.setText(data['flight1'])
        input_time1.setText(data['time1'])
        input_flight_number1.setText(data['flight_number1'])
        input_plane_type1.setText(data['plane_type1'])
        input_flight2.setText(data['flight2'])
        input_time2.setText(data['time2'])
        input_flight_number2.setText(data['flight_number2'])
        input_plane_type2.setText(data['plane_type2'])
        self.is_round_trip = data['is_round_trip']
        self.detected_airlines = data['detected_airlines']
        round_trip_checkbox.setChecked(self.is_round_trip)
        parent.flight2_group.setVisible(self.is_round_trip)

        flight_number1 = data['flight_number1']
        airline_name1 = None
        for airline, config in self.airlines_config.items():
            if flight_number1.upper().startswith(config.get('code', '').upper()):
                airline_name1 = airline
                break
        if not airline_name1 and self.detected_airlines:
            airline_name1 = self.detected_airlines[0]
        label_flight_number1.clear()
        self.load_logo(label_flight_number1, airline_name1, parent)

        if self.is_round_trip:
            flight_number2 = data['flight_number2']
            airline_name2 = None
            for airline, config in self.airlines_config.items():
                if flight_number2.upper().startswith(config.get('code', '').upper()):
                    airline_name2 = airline
                    break
            if not airline_name2 and self.detected_airlines:
                airline_name2 = self.detected_airlines[0]
            label_flight_number2.clear()
            self.load_logo(label_flight_number2, airline_name2, parent)

    def clean_city_name(self, city, parent):
        code_match = re.search(r'\(([A-Z]{3})\)', city, re.IGNORECASE)
        code = code_match.group(1).upper() if code_match else None

        cleaned_city = re.sub(r'\s*\([A-Z]{3}\)\s*(?:\(t[1-4]\))?', '', city, flags=re.IGNORECASE).strip()
        cleaned_city = re.sub(r'\s*\(t[1-4]\)', '', cleaned_city, flags=re.IGNORECASE).strip()
        cleaned_city = re.sub(r'^tp\s+', '', cleaned_city, flags=re.IGNORECASE).strip()

        if self.city_trie.search(cleaned_city.lower()):
            matched_cities = [c for c in self.cities if c['city_name'].lower() == cleaned_city.lower() or any(alias.lower() == cleaned_city.lower() for alias in c['aliases'])]
            if code:
                matched_cities = [c for c in matched_cities if c['code'].upper() == code]
            if len(matched_cities) > 1:
                selected_city = self.select_airport(cleaned_city, parent)
                if selected_city:
                    return f"{selected_city['name']} ({selected_city['code']})"
            elif matched_cities:
                return f"{matched_cities[0]['name']} ({matched_cities[0]['code']})"

        return f"{cleaned_city} ({code})" if code else cleaned_city