# 📍 GẠO MAPS - BẢN ĐỒ DẤU CHÂN KỶ NIỆM

Ứng dụng bản đồ tương tác lưu giữ kỷ niệm du lịch, đánh dấu chủ quyền biển đảo Việt Nam, tính toán đa lộ trình đường bộ và trình chiếu hành trình (Cinema Replay).

---

## 🔒 1. Hướng dẫn Đẩy Code lên GitHub (Bảo mật mã nguồn)

Để bảo mật mã nguồn dự án của bạn, hãy tạo **Private Repository** (Kho riêng tư) trên GitHub:

### Bước 1: Tạo Repository riêng tư trên GitHub
1. Truy cập [GitHub](https://github.com/new).
2. Đặt tên Repository (ví dụ: `gao-maps` hoặc `DAUCHANCUAGAO`).
3. **Quan trọng**: Chọn chế độ **Private** (Chỉ bạn và người được mời mới có quyền xem mã nguồn).
4. Nhấn **Create repository**.

### Bước 2: Đẩy mã nguồn từ máy tính lên GitHub
Mở Terminal trong thư mục dự án và chạy các lệnh sau:

```bash
# 1. Khởi tạo git (nếu chưa có)
git init

# 2. Thêm tất cả các file (các file nhạy cảm và .env đã được .gitignore bảo vệ tự động)
git add .

# 3. Tạo commit
git commit -m "Cập nhật hoàn chỉnh Gạo Maps với Google Maps & cấu hình Vercel"

# 4. Đổi tên nhánh chính thành main
git branch -M main

# 5. Liên kết tới GitHub Repository của bạn (thay YOUR_USERNAME và REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# 6. Đẩy code lên GitHub
git push -u origin main
```

---

## 🚀 2. Hướng dẫn Triển khai lên Vercel (Miễn phí & Tự động)

Vercel là nền tảng máy chủ hàng đầu thế giới dành cho ứng dụng web với tốc độ cao, chứng chỉ SSL/HTTPS bảo mật và hỗ trợ custom domain.

### Triển khai tự động qua GitHub (Khuyên dùng):
1. Truy cập [Vercel Dashboard](https://vercel.com/dashboard) và đăng nhập bằng tài khoản GitHub.
2. Nhấn **Add New...** -> **Project**.
3. Chọn Repository GitHub riêng tư bạn vừa tạo (`Import`).
4. Cấu hình dự án (Vercel sẽ tự nhận diện qua tệp `vercel.json` đã chuẩn bị sẵn):
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Nhấn **Deploy**. 
6. Chỉ sau khoảng 30 giây, ứng dụng của bạn sẽ hoạt động trực tuyến với tên miền bảo mật `https://tên-dự-án.vercel.app`. Mỗi khi bạn `git push` lên GitHub, Vercel sẽ tự động cập nhật bản mới nhất.

---

## 🛠️ 3. Chạy Thử Nghiệm Trên Máy Cục Bộ (Local)

```bash
# Cài đặt thư viện phụ thuộc
npm install

# Khởi chạy server phát triển
npm run dev

# Đóng gói sản phẩm xuất bản
npm run build
```

---

## 🛡️ 4. Tính năng Bảo mật Đã Tích hợp
- **Bảo vệ Header HTTP (`vercel.json`)**: Chống tấn công XSS, Clickjacking (`X-Frame-Options: SAMEORIGIN`), MIME Sniffing (`X-Content-Type-Options: nosniff`) và bảo vệ quyền riêng tư định vị (`Permissions-Policy`).
- **Bảo mật `.gitignore`**: Ngăn chặn tuyệt đối việc vô tình đưa các tệp cấu hình `.env`, mã khóa bảo mật hoặc tệp tạm lên GitHub.

