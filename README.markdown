# Flight Ticket Calculator

## Giới thiệu

**Flight Ticket Calculator** là một ứng dụng Python sử dụng giao diện đồ họa (GUI) được xây dựng với thư viện **PyQt6**. Ứng dụng hỗ trợ tính toán chi phí vé máy bay nội địa và quốc tế, bao gồm các khoản giảm giá (voucher) và hiển thị thông tin chi tiết về chuyến bay. Ứng dụng có khả năng nhận dạng thông tin từ clipboard, xuất kết quả dưới dạng ảnh hoặc văn bản, và hiển thị thông tin một cách trực quan.

### Tính năng chính

- **Tính toán chi phí vé máy bay**: Tính tổng chi phí cho người lớn, trẻ em (2-11 tuổi) và trẻ dưới 2 tuổi, áp dụng giảm giá voucher.
- **Hỗ trợ chuyến bay khứ hồi**: Cho phép nhập thông tin cho cả chuyến đi và chuyến về.
- **Nhận dạng thông tin từ clipboard**: Tự động trích xuất thông tin như hãng bay, số hiệu chuyến bay, lộ trình, thời gian, và giá vé từ văn bản trong clipboard.
- **Hiển thị logo hãng bay**: Hiển thị logo của các hãng như Vietjet Air, Bamboo Airways, Vietnam Airlines, Vietravel Airlines, Pacific Airlines.
- **Xuất kết quả**: Lưu kết quả dưới dạng ảnh chụp màn hình hoặc văn bản vào clipboard.
- **Ghi chú tùy chỉnh**: Hiển thị thông tin về hành lý và các lưu ý liên quan đến hãng bay.
- **Giao diện thân thiện**: Thiết kế đẹp, dễ sử dụng, với các trường nhập liệu được định dạng tự động.

## Yêu cầu hệ thống

- **Hệ điều hành**: Windows, macOS, hoặc Linux.
- **Python**: Phiên bản 3.8 trở lên.
- **Thư viện**:
  - PyQt6
- **Tệp bổ sung**:
  - Thư mục `images/` chứa các file logo của hãng bay (`vietjet_air.gif`, `bamboo_airways.gif`, v.v.), biểu tượng mũi tên (`arrow.png`), và ảnh chụp màn hình (`screenshot.png`).
  - File `icon.ico` cho biểu tượng ứng dụng (tùy chọn).

## Cài đặt

1. **Clone repository**:

   ```bash
   git clone https://github.com/vtn19081998/flight-ticket-calculator.git
   cd flight-ticket-calculator
   ```

2. **Cài đặt Python** (nếu chưa có): Tải và cài đặt từ python.org.

3. **Cài đặt thư viện cần thiết**:

   ```bash
   pip install PyQt6
   ```

4. **Chuẩn bị thư mục** `images`:

   - Tạo thư mục `images/` trong thư mục dự án.
   - Sao chép các file logo của hãng bay (`vietjet_air.gif`, `bamboo_airways.gif`, v.v.), file `arrow.png`, và file ảnh chụp màn hình (`screenshot.png`) vào thư mục này.
   - (Tùy chọn) Thêm file `icon.ico` vào thư mục gốc để hiển thị biểu tượng ứng dụng.

## Cách sử dụng

1. **Chạy ứng dụng**:

   ```bash
   python ticket_calculator.py
   ```

2. **Nhập thông tin**:

   - **Thông tin chuyến bay**: Nhập số hiệu chuyến bay, lộ trình, thời gian, và loại máy bay (hoặc sử dụng nút "Nhập dữ liệu" để trích xuất từ clipboard).
   - **Thông tin hành khách**: Nhập số lượng người lớn, trẻ em (2-11 tuổi), trẻ dưới 2 tuổi, giá vé gốc, và tỷ lệ giảm giá (%).
   - **Chuyến bay khứ hồi**: Chọn ô "Chuyến bay khứ hồi" để nhập thông tin chuyến bay thứ hai.

3. **Tính toán và xuất kết quả**:

   - Nhấn **Tính toán** để hiển thị bảng chi phí và tổng chi phí.
   - Nhấn **Xuất dữ liệu** để sao chép kết quả dưới dạng văn bản vào clipboard.
   - Nhấn **Chụp ảnh màn hình** để sao chép ảnh giao diện vào clipboard.
   - Nhấn **Xóa dữ liệu** để làm mới các trường nhập liệu.

4. **Nhận dạng từ clipboard**:

   - Sao chép văn bản chứa thông tin chuyến bay (hãng bay, số hiệu, lộ trình, giá vé, v.v.) vào clipboard.
   - Nhấn **Nhập dữ liệu** để ứng dụng tự động điền các trường tương ứng.

## Ảnh chụp màn hình

Dưới đây là giao diện chính của ứng dụng:

![Giao diện Flight Ticket Calculator](v5.1.1/Python/images/screenshot.png)

## Cấu trúc mã nguồn

- `ticket_calculator.py`: File chính chứa toàn bộ mã nguồn của ứng dụng.
- **Thư mục** `images/`:
  - Chứa các file logo của hãng bay (`*.gif`), biểu tượng mũi tên (`arrow.png`), và ảnh chụp màn hình (`screenshot.png`).
  - File `icon.ico` (tùy chọn) cho biểu tượng cửa sổ ứng dụng.

## Ghi chú

- **Hãng bay được hỗ trợ**: Vietjet Air, Bamboo Airways, Vietnam Airlines, Vietravel Airlines, Pacific Airlines.
- **Hành lý**:
  - Vietjet Air, Bamboo Airways: 7kg xách tay + 20kg ký gửi.
  - Vietnam Airlines: 10kg xách tay + 23kg ký gửi.
  - Vietravel Airlines: 7kg xách tay + 15kg ký gửi.
  - Pacific Airlines: 7kg xách tay + 23kg ký gửi.
- **Giảm giá**:
  - Trẻ em (2-11 tuổi): Giảm 30% giá vé gốc.
  - Trẻ dưới 2 tuổi: Miễn phí.
  - Voucher: Áp dụng thêm tỷ lệ giảm giá (%) do người dùng nhập.
- Đảm bảo thư mục `images/` chứa đầy đủ các file cần thiết để hiển thị logo, biểu tượng, và ảnh chụp màn hình.

## Tác giả

- **Tác giả**: Batman
- **Phiên bản**: 5.1.1

## Giấy phép

Dự án này được phát hành dưới dạng mã nguồn mở. Vui lòng liên hệ tác giả để biết thêm chi tiết về giấy phép sử dụng.