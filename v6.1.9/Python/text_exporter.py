import re
from PyQt6.QtWidgets import QApplication, QMessageBox

class TextExporter:
    def __init__(self, airlines_config):
        self.airlines_config = airlines_config

    def copy_text(self, export_format, price_text, discount_text, adult_text, child_text, infant_text,
                  flight1_text, time1_text, flight_number1_text, flight2_text, time2_text,
                  flight_number2_text, is_round_trip, table, result_label_text, discount_amount,
                  detected_airlines):
        required_inputs = [price_text.strip(), discount_text.strip(), adult_text.strip(),
                          child_text.strip(), infant_text.strip()]
        if not all(required_inputs):
            QMessageBox.warning(None, "Thiếu thông tin", "Vui lòng nhập đầy đủ tất cả các trường trước khi Xuất dữ liệu.")
            return

        try:
            voucher_value = int(discount_text.strip() or "0")
            base_fare_value = int(price_text.strip().replace(',', '')) if price_text.strip().replace(',', '').isdigit() else 0
            adult_count = int(adult_text)
            child_count = int(child_text)
            infant_count = int(infant_text)
            total_guests = adult_count + child_count + infant_count
            discount = voucher_value / 100
            adult_price = base_fare_value * (1 - discount)
            child_price = (base_fare_value * 0.7) * (1 - discount)

            airlines = []
            airline1 = next((airline for airline in self.airlines_config if airline.upper() in flight_number1_text.upper()), "Không xác định")
            airlines.append(airline1)
            if is_round_trip and flight_number2_text:
                airline2 = next((airline for airline in self.airlines_config if airline.upper() in flight_number2_text.upper()), "Không xác định")
                airlines.append(airline2)
            airline_name = airlines[0] if len(airlines) == 1 or airlines[0] == airlines[1] else ", ".join(airlines[:2])

            def get_note_content(airlines):
                base_text = "Tổng giá vé đã bao gồm toàn bộ thuế phí"
                if any(self.airlines_config[airline].get('meal', False) for airline in airlines if airline in self.airlines_config):
                    base_text += ", suất ăn"
                luggage1 = self.airlines_config.get(airlines[0], {}).get('luggage', 'không có thông tin hành lý')
                luggage2 = self.airlines_config.get(airlines[1] if len(airlines) > 1 else airlines[0], {}).get('luggage', 'không có thông tin hành lý')
                if len(airlines) == 1 or luggage1 == luggage2:
                    return f"{base_text}, {luggage1}"
                return f"{base_text}\n● Với mỗi vé {airline1}, được mang {luggage1}\n● Với mỗi vé {airline2}, được mang {luggage2}"

            trip_type = "khứ hồi" if is_round_trip else "1 chiều"
            note_content = get_note_content(airlines)

            if export_format == "Văn bản ngắn gọn":
                suffix = " khứ hồi" if is_round_trip else ""
                clipboard_content = (
                    f"Em gửi Anh/chị chuyến này của hãng {airline_name} và mã voucher giảm giá {voucher_value}% "
                    f"cho các chuyến bay Nội địa - Quốc tế\n\n"
                    f"● Giá vé sau khi áp mã voucher còn: {adult_price:,.0f} VNĐ/vé người lớn{suffix}\n"
                    f"● Vé trẻ em 2-11 tuổi: {child_price:,.0f} VNĐ\n"
                    f"\n{note_content}"
                )

            elif export_format == "Văn bản hành trình":
                def format_route(route_text):
                    clean_text = re.sub(r'<[^>]+>', '', route_text).strip()
                    clean_text = re.sub(r'\s*[-→]\s*|\s{2,}', ' > ', clean_text)
                    parts = clean_text.split(' > ')
                    return f"{parts[0].strip()} > {parts[1].strip()}" if len(parts) >= 2 else "Không xác định"

                def extract_time_and_date(time_text):
                    time_text = re.sub(r'<[^>]+>', '', time_text)
                    parts = time_text.split('|')
                    if len(parts) >= 3:
                        time_range = parts[2].strip()
                        date = parts[1].strip()
                        start_time = time_range.split('-')[0].strip() if '-' in time_range else "Không xác định"
                        return start_time, date
                    return "Không xác định", "Không xác định"

                flight1_text = format_route(flight1_text)
                flight2_text = format_route(flight2_text) if is_round_trip else ""
                time1, date1 = extract_time_and_date(time1_text)
                time2, date2 = extract_time_and_date(time2_text) if is_round_trip else ("", "")

                clipboard_content = (
                    f"Chuyến bay: {flight1_text} ({airline1})\n"
                    f"● Khởi hành: {time1} ngày {date1}\n"
                )
                if is_round_trip:
                    clipboard_content += (
                        f"Chuyến 2: {flight2_text} ({airlines[1] if len(airlines) > 1 else airline1})\n"
                        f"● Khởi hành: {time2} ngày {date2}\n"
                    )
                clipboard_content += (
                    f"\nGiá vé sau khi áp mã voucher giảm {voucher_value}%:\n"
                    f"● {adult_price:,.0f} VNĐ/người lớn\n● {child_price:,.0f} VNĐ/trẻ em 2-11 tuổi\n"
                    f"\n{note_content}"
                )

            else:  # Văn bản chi tiết
                intro_text = "Em gửi anh/chị bảng tính toán chi phí chuyến bay:\n\n"
                trip_text = f"● Đây là chuyến bay {trip_type}.\n"
                airline_text = f"● Hãng bay: {airline_name}.\n"
                base_fare_text = f"● Giá gốc: {base_fare_value:,.0f} VNĐ/vé\n"
                voucher_text = f"● Mã voucher khuyến mãi: {voucher_value}%\n"
                guest_text = f"● Tổng số khách: {total_guests}\n"
                after_voucher = "Chi phí sau khuyến mãi:\n"

                table_data = ""
                for row in range(table.rowCount()):
                    item_quantity = table.item(row, 2)
                    if item_quantity and item_quantity.text().isdigit() and int(item_quantity.text()) > 0:
                        item_name = table.item(row, 1).text().strip()
                        quantity = int(item_quantity.text())
                        price = float(table.item(row, 3).text().replace(" VNĐ", "").replace(",", "").strip()) if "Miễn phí" not in table.item(row, 3).text() else 0
                        total = float(table.item(row, 4).text().replace(" VNĐ", "").replace(",", "").strip())
                        formatted_line = f"● {item_name}: {quantity} x {price:,.0f} = {total:,.0f} VNĐ\n" if price > 0 else f"● {item_name}: {quantity} x Miễn phí = 0 VNĐ\n"
                        table_data += formatted_line

                total_cost = result_label_text.strip()
                discount_text = f"● Số tiền tiết kiệm được trong chuyến bay này là: {discount_amount:,.0f} VNĐ.\n"
                clipboard_content = f"{intro_text}{trip_text}{airline_text}{guest_text}{voucher_text}\n{after_voucher}{table_data}{total_cost}\n\n{note_content}"

            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_content)
            QMessageBox.information(None, "Sao chép nội dung", f"Nội dung định dạng '{export_format}' đã được sao chép vào clipboard.")
        except Exception as e:
            QMessageBox.critical(None, "Lỗi", f"Có lỗi xảy ra: {str(e)}")