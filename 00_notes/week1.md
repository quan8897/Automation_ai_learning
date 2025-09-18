# Tuần 1 – Học Python cơ bản & thao tác file

## 🎯 Mục tiêu tuần
- Hiểu cú pháp Python cơ bản (biến, vòng lặp, hàm, if/else).
- Thao tác file & thư mục (`os`, `shutil`, `pathlib`).
- Viết script đổi tên file trong thư mục `inbox`.

---

## ✅ Việc đã làm
- [ ] Hoàn thành bài học Python cơ bản.
- [ ] Viết script `rename_files.py` đổi tên file theo format `YYYYMMDD_tenCu.ext`.
- [ ] Thêm logging cho script (in tên file trước & sau khi đổi).
- [ ] Test trên thư mục `inbox/` với 3–5 file.

---

## 🧠 Kiến thức rút ra
- Ví dụ: `os.listdir()` duyệt tất cả file trong thư mục.
- `os.path.splitext(filename)` tách tên và phần mở rộng.
- Logging giúp dễ debug hơn khi code chạy trên nhiều file.

---

## 🛠️ Vấn đề gặp phải
- File trùng tên → script báo lỗi.
- Khi chạy trên Windows, đường dẫn cần `r"..."` để tránh lỗi escape.

---

## 📊 Tự đánh giá
- Focus: 4/5
- Output: 3/5

---

## 🚀 Kế hoạch tuần sau (Tuần 2)
- Học về `csv` & `pandas`.
- Viết script `sales_report.py`:
  - Gộp 3 file `week1.csv`, `week2.csv`, `week3.csv`.
  - Tính tổng doanh thu theo sản phẩm.
  - Xuất kết quả ra file Excel `report.xlsx`.

