# 💰 Quản lý chi tiêu hàng ngày

Ứng dụng web ghi chép thu chi cá nhân, viết bằng Python + [Streamlit](https://streamlit.io).

**Tính năng**

- Ghi thu/chi theo danh mục; sửa, xóa, lọc, xuất CSV
- Tổng quan tháng: tổng thu, tổng chi, so sánh với tháng trước
- Báo cáo: biểu đồ tròn theo danh mục, cột theo ngày, xu hướng 12 tháng
- Ngân sách tháng (tổng và theo danh mục): cảnh báo khi dùng ≥ 80%, báo đỏ khi vượt
- Tự quản lý danh mục; khóa app bằng mật khẩu

## Cấu trúc

```
app.py              # điểm vào: đăng nhập + menu
db.py               # bảng dữ liệu và các hàm đọc/ghi (SQLAlchemy)
utils.py            # định dạng tiền, tính ngân sách
views/              # mỗi trang một file
  dashboard.py  transactions.py  reports.py  budgets.py  categories.py
```

Dữ liệu lưu ở đâu được quyết định bởi `DATABASE_URL`:

| Môi trường | `DATABASE_URL` | Dữ liệu nằm ở |
|---|---|---|
| Chạy trên máy | không đặt | `data/expenses.db` (SQLite) |
| Streamlit Cloud | chuỗi kết nối Supabase | Postgres trên Supabase |

> Ổ đĩa của Streamlit Cloud bị xóa mỗi lần app khởi động lại, nên khi deploy **bắt buộc** dùng Supabase (hoặc Postgres khác).

## Chạy trên máy

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run app.py
```

Mở http://localhost:8501. Muốn đặt mật khẩu khi chạy local: chép `.streamlit/secrets.toml.example` thành `.streamlit/secrets.toml` và sửa `APP_PASSWORD`.

## Deploy lên mạng (miễn phí)

### 1. Tạo CSDL trên Supabase

1. Đăng ký tại https://supabase.com → **New project** (nhớ mật khẩu database, chọn region Singapore cho nhanh).
2. Vào **Connect** (hoặc *Project Settings → Database*), mục **Connection string**, chọn **Session pooler** và copy chuỗi dạng:
   `postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`
3. Thay `[YOUR-PASSWORD]` bằng mật khẩu database.

> Dùng **Session pooler**, không dùng "Direct connection": Streamlit Cloud chỉ có IPv4, còn direct connection của Supabase là IPv6.

Không cần tạo bảng: app tự tạo bảng và danh mục mặc định ở lần chạy đầu.

### 2. Đẩy code lên GitHub

```bash
git init
git add .
git commit -m "Ứng dụng quản lý chi tiêu"
git branch -M main
git remote add origin https://github.com/<tài-khoản>/<tên-repo>.git
git push -u origin main
```

`.gitignore` đã loại `data/`, `*.db` và `.streamlit/secrets.toml`, nên dữ liệu và mật khẩu không bị đẩy lên. Repo có thể để **Private**.

### 3. Deploy trên Streamlit Community Cloud

1. Vào https://share.streamlit.io, đăng nhập bằng GitHub → **Create app** → chọn repo, nhánh `main`, file `app.py`.
2. Mở **Advanced settings → Secrets**, dán:
   ```toml
   APP_PASSWORD = "mật-khẩu-mở-app"
   DATABASE_URL = "postgresql://postgres.xxxx:MAT_KHAU@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
   ```
3. **Deploy**. Mỗi lần `git push`, app tự cập nhật.

> Nên đặt `APP_PASSWORD`: link Streamlit Cloud là công khai, ai có link cũng mở được. Có thể đặt thêm chế độ riêng tư trong *Settings → Sharing* của app.

## Mở rộng sau này

- Thêm cột/bảng: sửa `db.py` (với Postgres đã có dữ liệu, cần `ALTER TABLE` thủ công hoặc dùng Alembic).
- Thêm trang: tạo file trong `views/` có hàm `page()`, rồi thêm `st.Page(...)` trong `app.py`.
