# Tuần 1 – Python cơ bản & thao tác file

## 🎯 Mục tiêu tuần
- Hiểu cú pháp Python cơ bản (biến, vòng lặp, hàm, if/else).
- Thao tác file & thư mục (`os`, `shutil`, `pathlib`).
- Viết script `rename_files.py` để đổi tên file trong thư mục `inbox`.

---

## 🗓️ Lịch học theo ngày

### 📅 Day 1 – Biến & kiểu dữ liệu
- Học: `int`, `float`, `str`, `bool`.
- Thử: ép kiểu (`str()` ↔ `int()`).
- Bài tập: tạo biến `name`, `age`, `height`, in ra thông tin.

### 📅 Day 2 – List, dict, tuple, set
- Học: cách khai báo, thêm, xóa, duyệt phần tử.
- Bài tập: 
  - Tạo list số nguyên → in tổng, max, min.
  - Tạo dict học sinh → in ra format đẹp.

### 📅 Day 3 – Vòng lặp & điều kiện
- Học: `for`, `while`, `if/else`, `break`, `continue`.
- Bài tập: 
  - In bảng cửu chương.
  - Viết chương trình kiểm tra số nguyên tố.

### 📅 Day 4 – Hàm
- Học: định nghĩa hàm (`def`), tham số, `return`.
- Bài tập: 
  - Viết hàm `square_list(numbers)`.
  - Viết hàm `is_prime(n)`.

### 📅 Day 5 – File I/O
- Học: `open()`, `read()`, `write()`, `with open(...)`.
- Bài tập: 
  - Ghi 5 dòng `"Hello Python"` vào file.
  - Đọc file và in từng dòng.

### 📅 Day 6 – Thư viện hệ thống
- Học: `os`, `pathlib`, `shutil`.
  - `os.listdir()`, `os.rename()`.
  - `Path.glob()`, `.stem`, `.suffix`.
  - `shutil.copy()`, `shutil.move()`.
- Bài tập: 
  - Viết script đổi tên file `.txt` trong thư mục.

### 📅 Day 7 – Mini project & review
- Hoàn thành script **`rename_files.py`**:
  - Đổi tên file thành `YYYYMMDD_tenCu.ext`.
  - Có logging (tên cũ → tên mới).
  - Xử lý trùng tên bằng hậu tố `_1`, `_2`.
- Viết phần tổng kết:
  - Kiến thức rút ra.
  - Vấn đề gặp phải.
  - Kế hoạch tuần 2.

---

## ✅ Checklist
- [ ] Nắm chắc biến, kiểu dữ liệu, cấu trúc dữ liệu.
- [ ] Viết được hàm cơ bản.
- [ ] Đọc/ghi file `.txt`.
- [ ] Hiểu `os`, `pathlib`, `shutil`.
- [ ] Hoàn thành `rename_files.py`.

---

## 🧠 Kiến thức rút ra (điền sau khi học)
- Ví dụ: `os.path.splitext(filename)` tách tên và phần mở rộng.
- Logging giúp debug dễ hơn.

---

## 🛠️ Vấn đề gặp phải (điền sau khi học)
- File trùng tên → script báo lỗi.
- Windows cần `r"..."` cho đường dẫn.

---

## 📊 Tự đánh giá (điền cuối tuần)
- Focus: _/5
- Output: _/5

---

## 🚀 Kế hoạch tuần sau (Tuần 2)
- Học về `csv` & `pandas`.
- Viết script `sales_report.py` để gộp dữ liệu và tạo báo cáo.
