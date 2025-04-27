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
    _route_pattern = None
    _alt_route_pattern = None
    _vn_city_pattern = None
    _intl_city_pattern = None
    _price_pattern = re.compile(r'\d{1,3}(?:[.,]\d{3})*(?:\.\d{2})?')
    _flight_pattern = re.compile(
        r'(?:(vietnam\s*airlines|vietjet\s*air|bamboo\s*airways|pacific\s*airlines|vietravel\s*airlines|singapore\s*airlines|thai\s*airways|japan\s*airlines)\s+)?(?:\s*(vj|vn|qh|vu|bl|sq|tg|jl)[-|\s]*(\d{3,4})(?=\s|$|[^\d]))',
        re.IGNORECASE
    )
    _note_flight_pattern = re.compile(
        r'(vj|vn|qh|vu|bl|sq|tg|jl)(\d{3,4})\s*:\s*(vietnam\s*airlines|vietjet\s*air|bamboo\s*airways|pacific\s*airlines|vietravel\s*airlines|singapore\s*airlines|thai\s*airways|japan\s*airlines)',
        re.IGNORECASE
    )
    _day_pattern = re.compile(r'(thứ\s*(?:hai|ba|tư|năm|sáu|bảy)|chủ nhật|c\.nhật|t\.\w+)', re.IGNORECASE)
    _date_pattern = re.compile(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)')
    _time_range_pattern = re.compile(r'(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})')
    _plane_type_pattern = re.compile(
        r'(?:máy bay\s*:\s*)?(a\d{2,3}|boeing\s*\d{3}|boeing\s*777|boeing\s*787|airbus\s*a\d{2,3}|airbus\s*a380|embraer\s*e\d{2,3}|atr\s*\d{2}|bombardier\s*[a-zA-Z0-9]+)',
        re.IGNORECASE
    )
    _duration_pattern = re.compile(r'(\d+)\s*giờ(?:\+(\d+)p)?', re.IGNORECASE)

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
            elif city_name:
                pass

        if not unique_cities:
            raise ValueError("Danh sách thành phố trống sau khi loại bỏ trùng lặp.")

        # Xây dựng trie cho tìm kiếm tên thành phố
        trie = Trie()
        for city in unique_cities:
            trie.insert(city['city_name'].lower())
            for alias in city['aliases']:
                trie.insert(alias.lower())

        # Chia regex thành hai nhóm: Việt Nam và quốc tế
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
            rf'([a-zA-Z\s]+?)(?:\s*(?:to|→|-)\s*|\s+)([a-zA-Z\s]+?)(?:\s*(?:thứ\s*(?:hai|ba|tư|năm|sáu|bảy)|chủ nhật|c\.nhật|t\.\w+|\d{{1,2}}/\d{{1,2}}))|([A-Z]{{3}})\s*-\s*([A-Z]{{3}})',
            re.IGNORECASE
        )

        return unique_cities, trie

    def __init__(self, airlines_config, cities_file='data/cities.json'):
        self.airlines_config = airlines_config
        self.detected_airlines = []
        self.is_round_trip = False
        self.clipboard_cache = {}
        self.cache_timer = QTimer()
        self.cache_timer.timeout.connect(self.clear_cache)
        self.cache_timer.start(300000)  # Xóa cache sau 5 phút

        if InputProcessor._route_pattern is None:
            self.cities, self.city_trie = self._load_cities_and_compile_regex(cities_file)
        else:
            self.cities, self.city_trie = self._load_cities_and_compile_regex(cities_file)
            self.cities = [city for city in self.cities]

        self.error_messages = []

    def clear_cache(self):
        self.clipboard_cache.clear()

    def normalize_airline_name(self, name):
        name = name.lower().replace(" ", "")
        if "vietjet" in name:
            return "vietjetair"
        if "vietnam" in name:
            return "vietnamairlines"
        if "bamboo" in name:
            return "bambooairways"
        if "pacific" in name:
            return "pacificairlines"
        if "vietravel" in name:
            return "vietravelairlines"
        if "singapore" in name:
            return "singaporeairlines"
        if "thai" in name:
            return "thaiairways"
        if "japan" in name:
            return "japanairlines"
        return name

    def display_airline_name(self, normalized_name):
        name_map = {
            "vietjetair": "Vietjet Air",
            "vietnamairlines": "Vietnam Airlines",
            "bambooairways": "Bamboo Airways",
            "pacificairlines": "Pacific Airlines",
            "vietravelairlines": "Vietravel Airlines",
            "singaporeairlines": "Singapore Airlines",
            "thaiairways": "Thai Airways",
            "japanairlines": "Japan Airlines"
        }
        return name_map.get(normalized_name, normalized_name.replace("air", " Air"))

    def get_airline_key(self, airline_name):
        airline_name_lower = self.normalize_airline_name(airline_name)
        for airline in self.airlines_config:
            if self.normalize_airline_name(airline) == airline_name_lower:
                return airline
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
        
        # Xử lý giá vé
        prices = self._price_pattern.findall(text)
        if prices:
            max_price = max(float(p.replace(',', '').replace('.', '')) for p in prices)
            input_price.setText("{:,.0f}".format(max_price))
            parent.price_multiplied = True
        else:
            self.error_messages.append("Không tìm thấy giá vé trong văn bản.")

        # Xử lý hãng bay
        self.detected_airlines = []
        normalized_text_clean = self.normalize_airline_name(normalized_text)
        for airline in self.airlines_config:
            airline_clean = self.normalize_airline_name(airline)
            if airline_clean in normalized_text_clean:
                self.detected_airlines.append(airline)
        if not self.detected_airlines:
            self.error_messages.append("Không nhận diện được hãng bay từ văn bản.")
        airline_info = []
        for airline in self.detected_airlines:
            display_name = self.display_airline_name(self.normalize_airline_name(airline))
            luggage = self.airlines_config.get(airline, {}).get('luggage', 'Không có thông tin hành lý')
            airline_info.append(f"{display_name}: Hành lý: {luggage}")
        parent.update_note_label(airline_info)

        # Xử lý tuyến bay
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

        # Xử lý ngày và giờ
        day_map = {
            'thứ hai': 'THỨ HAI', 'thứ ba': 'THỨ BA', 'thứ tư': 'THỨ TƯ', 'thứ năm': 'THỨ NĂM',
            'thứ sáu': 'THỨ SÁU', 'thứ bảy': 'THỨ BẢY', 'chủ nhật': 'CHỦ NHẬT',
            't.hai': 'THỨ HAI', 't.ba': 'THỨ BA', 't.tư': 'THỨ TƯ', 't.năm': 'THỨ NĂM',
            't.sáu': 'THỨ SÁU', 't.bảy': 'THỨ BẢY', 'c.nhật': 'CHỦ NHẬT'
        }
        days = [day_map.get(d.strip().lower(), d.strip().upper()) for d in self._day_pattern.findall(text.lower())]
        dates = self._date_pattern.findall(text)
        time_ranges = self._time_range_pattern.findall(text)

        if days:
            date1 = dates[0].upper() if dates else ''
            time_range1 = time_ranges[0].upper() if time_ranges else ''
            time_start1 = time_range1.split('-')[0].strip() if time_range1 else ''
            time_end1 = time_range1.split('-')[1].strip() if time_range1 and '-' in time_range1 else ''
            formatted_time1 = f"{days[0]} | <b>{date1}</b> | <b>{time_start1}</b> - {time_end1}"
            input_time1.setText(formatted_time1)

            if self.is_round_trip and len(days) > 1:
                date2 = dates[1].upper() if len(dates) > 1 else ''
                time_range2 = time_ranges[1].upper() if len(time_ranges) > 1 else ''
                time_start2 = time_range2.split('-')[0].strip() if time_range2 else ''
                time_end2 = time_range2.split('-')[1].strip() if time_range2 and '-' in time_range2 else ''
                formatted_time2 = f"{days[1]} | <b>{date2}</b> | <b>{time_start2}</b> - {time_end2}"
                input_time2.setText(formatted_time2)

        # Xử lý mã chuyến bay
        note_flights = self._note_flight_pattern.findall(normalized_text)
        flight_codes = []
        self.detected_airlines = []
        for flight_code, flight_num, airline_name in note_flights:
            full_code = f"{flight_code.upper()}{flight_num}"
            flight_codes.append((full_code, airline_name))
            if airline_name and airline_name not in self.detected_airlines:
                self.detected_airlines.append(airline_name)

        if not flight_codes:
            flight_matches = self._flight_pattern.findall(normalized_text)
            for airline_name, flight_code, flight_num in flight_matches:
                full_code = f"{flight_code.upper()}{flight_num}"
                flight_codes.append((full_code, airline_name))
                if airline_name and airline_name not in self.detected_airlines:
                    self.detected_airlines.append(airline_name)

        if not self.detected_airlines:
            normalized_text_clean = self.normalize_airline_name(normalized_text)
            for airline in self.airlines_config:
                airline_clean = self.normalize_airline_name(airline)
                if airline_clean in normalized_text_clean:
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
                    display_name1 = self.display_airline_name(self.normalize_airline_name(airline_name1))
                    input_flight_number1.setText(f"{display_name1.upper()} | {full_code1}")
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
                    display_name2 = self.display_airline_name(self.normalize_airline_name(airline_name2))
                    input_flight_number2.setText(f"{display_name2.upper()} | {full_code2}")
                    self.load_logo(label_flight_number2, airline_name2, parent)
                else:
                    input_flight_number2.setText(f"UNKNOWN | {full_code2}")
                    label_flight_number2.setText("❓")
                    self.error_messages.append(f"Không nhận diện được hãng bay cho mã {full_code2}")
        else:
            self.error_messages.append("Không tìm thấy mã chuyến bay nào trong văn bản.")

        # Xử lý loại máy bay
        plane_types = self._plane_type_pattern.findall(normalized_text)
        if plane_types:
            plane_type1 = plane_types[0].upper()
            if "airbus" in normalized_text.lower() and "AIRBUS" not in plane_type1:
                plane_type1 = f"AIRBUS {plane_type1}"
            input_plane_type1.setText(plane_type1)
            if len(plane_types) > 1 and self.is_round_trip:
                plane_type2 = plane_types[1].upper()
                if "airbus" in normalized_text.lower() and "AIRBUS" not in plane_type2:
                    plane_type2 = f"AIRBUS {plane_type2}"
                input_plane_type2.setText(plane_type2)
        else:
            self.error_messages.append("Không tìm thấy loại máy bay trong văn bản.")

        # Lưu vào cache
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

        # Hiển thị lỗi (nếu có)
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

        airline_info = []
        for airline in self.detected_airlines:
            display_name = self.display_airline_name(self.normalize_airline_name(airline))
            luggage = self.airlines_config.get(airline, {}).get('luggage', 'Không có thông tin hành lý')
            airline_info.append(f"{display_name}: Hành lý: {luggage}")
        parent.update_note_label(self.detected_airlines)

        flight_number1 = data['flight_number1']
        airline_name1 = None
        for airline, config in self.airlines_config.items():
            if flight_number1.startswith(airline.upper()) or config.get('code', '').upper() in flight_number1:
                airline_name1 = airline
                break
        if not airline_name1 and self.detected_airlines:
            airline_name1 = self.detected_airlines[0]
        self.load_logo(label_flight_number1, airline_name1, parent)

        if self.is_round_trip:
            flight_number2 = data['flight_number2']
            airline_name2 = None
            for airline, config in self.airlines_config.items():
                if flight_number2.startswith(airline.upper()) or config.get('code', '').upper() in flight_number2:
                    airline_name2 = airline
                    break
            if not airline_name2 and self.detected_airlines:
                airline_name2 = self.detected_airlines[0]
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