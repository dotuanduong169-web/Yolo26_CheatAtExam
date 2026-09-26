# ExamCheat AI — Hệ thống phát hiện gian lận phòng thi

Hệ thống giám sát phòng thi bằng AI: camera hoặc video ghi sẵn → mô hình
YOLO26 instance segmentation phát hiện `Answer_paper / Cheat_Paper / cellphone`
→ lưu snapshot mỗi 30 giây → dashboard theo dõi, sửa nhãn thủ công, thống kê.

## Tính năng

* Giám sát trực tiếp: mở camera phòng thi hoặc chạy file video có sẵn,
  xem luồng MJPEG trực tiếp trên dashboard.
* Phát hiện gian lận: vẽ khung + polygon lên từng vật (giấy thi sạch màu xanh,
  tài liệu gian lận và điện thoại màu đỏ/cam), phân biệt gian lận/không gian lận.
* Lưu lịch sử: mỗi 30 giây lưu 1 ảnh + sự kiện gian lận đã debounce (≥3/5 frame) + thống kê vào PostgreSQL.
* Sửa nhãn thủ công: xác minh sự kiện đúng/sai kèm nhãn sửa khi AI sai,
  thống kê tự tính lại theo nhãn đã sửa.
* Thống kê: xem theo phiên thi, theo ngày/tuần, tỉ lệ bài sạch.
* Quản trị: đăng ký/đăng nhập bằng tên đăng nhập (JWT), phân quyền admin/teacher, quản lý thiết bị biên RTSP, tạo admin.

## Yêu cầu

* Linux, Python 3.11+, Docker (để chạy PostgreSQL).
* Camera USB/webcam nếu giám sát trực tiếp (không bắt buộc — có thể dùng
  video file `videos/test_exam*.mp4` có sẵn).

## Cài đặt

```bash
./setup.sh
```

Script tự: cài Docker (nếu thiếu), dựng PostgreSQL 16 qua `docker-compose.yml`,
tạo file `.env` từ mẫu, tạo venv `.venv`, cài PyTorch CPU + `backend/requirements.txt`
+ Streamlit. Nếu đã có Docker/Postgres riêng, bỏ qua bước đó và chỉ cần:

```bash
cp .env.example .env   # rồi sửa DATABASE_URL, SECRET_KEY
python3 -m venv .venv
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/pip install streamlit plotly pandas
```

## Cấu hình (.env)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | `postgresql://examcheat:examcheat123@localhost:5432/examcheat` | Kết nối PostgreSQL |
| `SECRET_KEY` | — | **Bắt buộc đổi** trước khi dùng thật |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Địa chỉ backend |
| `MODEL_PATH` | `backend/ai_model/weights/best.pt` | Weights YOLO26-seg |
| `MODEL_CONF` | `0.25` | Ngưỡng tin cậy
| `MODEL_IMGSZ` | `512` | Kích thước ảnh inference |

## Chạy

```bash
# 1. Backend API (từ thư mục gốc dự án)
.venv/bin/uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000

# 2. Tạo tài khoản admin (lần đầu)
.venv/bin/python backend/scripts/create_admin.py admin@exam.local matkhau

# 3. Giao diện web
.venv/bin/streamlit run frontend/app.py
```

Mở trình duyệt: API `http://localhost:8000/docs`, giao diện `http://localhost:8501`.

## Hướng dẫn sử dụng

1. Đăng nhập trên giao diện web.
2. Mở phiên giám sát mới:
   * Đăng ký thiết bị trước: `POST /devices {"TenThietBi": "Cam P101", "DuongDanRTSP": "0"}`
   * Camera trực tiếp: `POST /camera/start?device_id=1&phong_thi=P101&mon_thi=Toan`
   * Video có sẵn: `POST /camera/start?device_id=1&phong_thi=P101&video_path=videos/test_exam.mp4`
3. Xem luồng trực tiếp: `GET /camera/video_feed` (hoặc ngay trên trang chủ).
4. Hệ thống tự lưu ảnh + kết quả mỗi 30 giây. Vào trang phân tích phiên để xem
   lưới ảnh, trang chi tiết ảnh để click sửa nhãn từng vật.
5. Xem thống kê ngày/tuần ở trang thống kê; xóa phiên cũ ở trang lịch sử.
6. Kết thúc: `POST /camera/stop`.

## API chính

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/users/register`, `/users/login` | Tài khoản (tên đăng nhập) |
| POST | `/devices`, GET `/devices` | Đăng ký / liệt kê thiết bị biên |
| PUT, DELETE | `/devices/{id}` | Sửa / xóa thiết bị (admin) |
| POST | `/camera/start?device_id=&phong_thi=&mon_thi=` | Bắt đầu giám sát theo thiết bị |
| POST | `/camera/stop` | Dừng, chốt phiên |
| GET | `/camera/video_feed` | Luồng MJPEG trực tiếp |
| GET | `/camera/status`, `/camera/list` | Trạng thái, danh sách nguồn |
| GET | `/events/session/{id}` | Sự kiện gian lận của phiên (lọc trạng thái) |
| GET | `/events/{id}` | Chi tiết sự kiện + bằng chứng + tọa độ |
| PATCH | `/events/{id}` | Xác minh (`{"TrangThaiKiemTra": "dung"/"sai"}`) |
| GET | `/history/sessions`, `/history/summary` | Lịch sử phiên |
| GET | `/stats/daily`, `/stats/weekly`, `/stats/summary` | Thống kê |

Chi tiết đầy đủ xem tại `/docs` khi backend đang chạy.

## Huấn luyện mô hình mới

Dataset chuẩn là `training/dataset_seg_v4/` (3 class, xem
`training/dataset_seg_v4/data.yaml`). Dựng lại dataset từ dữ liệu gốc:

```bash
.venv/bin/python backend/scripts/migrate_dataset.py --clean
```

Huấn luyện (đúng cấu hình đã dùng cho `best.pt` hiện tại, chạy từ gốc dự án):

```bash
.venv/bin/yolo task=segment mode=train model=training/yolo26n-seg.pt \
  data=training/dataset_seg_v4/data.yaml epochs=50 patience=15 batch=2 imgsz=512 \
  device=cpu optimizer=AdamW lr0=0.0003 mosaic=1.0 erasing=0.4 \
  auto_augment=randaugment
```

Copy weights mới vào để API dùng ngay:

```bash
cp runs/segment/<ten-train>/weights/best.pt backend/ai_model/weights/best.pt
```

## Cấu trúc thư mục

```text
backend/
  main.py               # Khởi tạo FastAPI, gắn router
  core/                 # Cấu hình, JWT, bảo mật, rate-limit, logger
  database/             # Engine + session PostgreSQL
   models/               # tbl_user, tbl_edgedevice, tbl_monitoring_sessions, tbl_detected_events, tbl_evidences, statistics
  schemas/              # Pydantic request/response
  crud/                 # Truy vấn DB
   api/router/           # users, camera, devices, events, history, statistics
  service/              # Nghiệp vụ: camera, capture loop, stream MJPEG...
  ai_model/             # ai_pipeline.py (YOLO26-seg) + weights/best.pt
  scripts/              # create_admin.py, migrate_dataset.py
frontend/               # Giao diện Streamlit (trang chủ, phân tích, chi tiết...)
training/               # Toàn bộ src huấn luyện AI
  dataset_seg/          # Dataset gốc Roboflow (nguồn rebuild)
  realworld_data/       # Ảnh phòng thi thật bổ sung
  dataset_seg_v4/       # Dataset huấn luyện chính (data.yaml, nc=3)
  yolo26n-seg.pt        # Pretrained để train mới
  weights/              # Lưu các bản train (train..train-6-2, *_best/*_last)
  runs/                 # Log, biểu đồ, confusion matrix từng bản train
videos/                 # Video thi mẫu
docker-compose.yml      # PostgreSQL 16
setup.sh                # Cài đặt tự động
```

## Lưu ý

* Class `Cheat_Paper` hiện ít mẫu kiểm chứng (độ chính xác thấp) — nên bổ sung
  thêm ảnh tài liệu gian lận thật trước khi dùng chính thức.
* Polygon hiện tại suy từ khung chữ nhật, chưa phải mask thật — không ảnh hưởng
  phát hiện khung, chỉ ảnh hưởng độ khít của đường viền.
* Thống kê tuần dùng hàm `to_char` của PostgreSQL nên yêu cầu đúng PostgreSQL.
