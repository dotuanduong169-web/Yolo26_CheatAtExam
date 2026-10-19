# ExamCheat AI — Hệ thống phát hiện gian lận phòng thi

Hệ thống giám sát thi cử bằng AI, hỗ trợ 2 chế độ:

* **Phòng thi trực tiếp**: camera máy chủ, IP camera/RTSP hoặc video mẫu → mô hình
  YOLO26n-seg phát hiện `Cheat_Paper` (tài liệu) và `cellphone` (điện thoại),
  mô hình YOLO26n-pose phát hiện hành vi `quay_dau`, `quay_sau`, `cui_xuong`.
* **Thi trực tuyến**: thí sinh mở link `/exam`, nhập SBD, dùng webcam trình duyệt
  gửi frame về server; mỗi phiên thí sinh có worker AI riêng, giám thị theo dõi
  trạng thái từng thí sinh trên lưới dashboard.

Khi vi phạm được xác nhận (debounce nhiều frame), hệ thống lưu ảnh bằng chứng vào
`images/` và ghi sự kiện vào PostgreSQL. Giám thị có thể xác minh đúng/sai và sửa
nhãn thủ công; thống kê tự tính lại theo nhãn đã sửa.

## Tính năng

* Giám sát trực tiếp: xem luồng MJPEG đã vẽ khung/polygon AI, chụp snapshot, theo dõi FPS.
* Phát hiện vật thể gian lận bằng YOLO26n-seg 2 nhãn kèm mask polygon (OpenVINO tăng tốc CPU).
* Phát hiện hành vi bằng YOLO26n-pose + luật hình học keypoints (không cần train lại).
* Chống nhiễu: debounce theo cửa sổ frame (vật thể 3/5, hành vi 4/6) và cooldown 15s/6s.
* Thi online: tạo ca thi, nhập danh sách thí sinh (SBD, họ tên, lớp), mở/đóng ca,
  link dự thi, vào thi idempotent (vào lại vẫn giữ phiên), token nộp frame lưu DB
  (sống qua restart), tự dừng worker khi phiên kết thúc hoặc idle 120 giây.
* Quy tắc riêng cho thi online: `vang_mat` (vắng mặt > 10 giây), `nhieu_nguoi` (> 1 người).
* Lịch sử: danh sách ca thi, chi tiết phiên, xem/xác minh sự kiện, xóa phiên (admin xóa mọi phiên).
* Thống kê: theo ngày, theo tuần, theo khoảng ngày, tổng hợp và phân bố hành vi; biểu đồ Plotly.
* Quản trị: JWT (cookie HttpOnly hoặc Bearer), phân quyền `admin`/`teacher`,
  rate-limit đăng nhập/đăng ký, blacklist token khi logout, quản lý thiết bị biên RTSP.

## Kiến trúc

```text
Trình duyệt giám thị ── Streamlit :8501 ──┐
Trình duyệt thí sinh ── /exam (webcam) ───┼── FastAPI :8000 ── PostgreSQL 16 :5432
                                          │        │
                                          │        ├── YOLO26n-seg  (OpenVINO, fallback .pt)
                                          │        ├── YOLO26n-pose (OpenVINO) + luật hành vi
                                          │        └── ảnh bằng chứng: images/ (gitignore)
                                          └── luồng MJPEG /camera/video_feed cho trang giám sát
```

Luồng xử lý phòng thi: thread capture đọc frame liên tục → worker infer riêng vẽ
kết quả → kiểm tra debounce/cooldown → lưu ảnh + sự kiện. Luồng thi online:
browser gửi JPEG mỗi 2,5 giây → hàng đợi giữ frame mới nhất → worker riêng từng
phiên → debounce → snapshot.

## Yêu cầu

* Python 3.11+ (khuyến nghị 3.11/3.12), pip, venv.
* Docker (Docker Desktop trên macOS, `docker.io` + `docker-compose-plugin` trên Linux)
  hoặc PostgreSQL 16 cài sẵn.
* Webcam hoặc IP camera RTSP nếu giám sát trực tiếp; có thể dùng video mẫu
  `videos/test_exam.mp4`, `videos/test_exam_2.mp4` (không cần camera).
* Chạy AI trên CPU là đủ (OpenVINO tăng tốc ~2,6 lần); không bắt buộc GPU.
* Trình duyệt hỗ trợ webcam. `getUserMedia` của thí sinh chỉ hoạt động trên
  `localhost` hoặc HTTPS.

## Cài đặt

Cách nhanh (Linux tự cài Docker, macOS cần Docker Desktop có sẵn):

```bash
./setup.sh
```

Script tự: dựng PostgreSQL 16 qua `docker-compose.yml`, tạo `.env` từ
`.env.example`, tạo venv `.venv`, cài PyTorch CPU + `backend/requirements.txt`
+ `frontend/requirements.txt`.

Cài thủ công (khi đã có PostgreSQL/Docker riêng):

```bash
cp .env.example .env          # sửa DATABASE_URL, SECRET_KEY
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/pip install -r frontend/requirements.txt
docker compose up -d postgres  # nếu dùng docker-compose.yml
```

## Cấu hình (.env)

Sao chép từ `.env.example`. Các biến chính:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | (trống, **bắt buộc**) | Chuỗi kết nối PostgreSQL |
| `SECRET_KEY` | `default-secret-key-change-this` | Khóa ký JWT — **bắt buộc đổi khi triển khai thật** |
| `ENVIRONMENT` | `development` | `production` sẽ bắt buộc cookie `Secure` (HTTPS) |
| `DEBUG` | `False` | Bật log SQL của SQLAlchemy |
| `ALLOWED_ORIGINS` | (trống) | Danh sách origin CORS cách nhau dấu phẩy; trống thì development cho phép `localhost:8501/8502`, production dùng `https://yourdomain.com` |
| `MODEL_PATH` | tự chọn OpenVINO rồi `.pt` | Weights YOLO26n-seg; đường dẫn tương đối tính từ gốc dự án |
| `MODEL_CONF` / `MODEL_IMGSZ` | `0.25` / `512` | Ngưỡng tin cậy và kích thước suy luận của model seg |
| `MODEL_TRACK` / `MODEL_STRIDE` / `MODEL_KEEP` | `1` / `2` / `5` | Bật ByteTrack, infer cách frame, số frame giữ box |
| `POSE_MODEL_PATH` | thư mục pose OpenVINO | Weights YOLO26n-pose (imgsz cố định 320) |
| `POSE_CONF` / `POSE_STRIDE` / `MODEL_BEH_KEEP` | `0.25` / `3` / `5` | Ngưỡng, chu kỳ và thời gian giữ box hành vi |
| `SAVE_INTERVAL_SECONDS` | `10` | Chu kỳ ghi bản ghi thống kê |
| `OBJECT_COOLDOWN_SECONDS` / `POSE_COOLDOWN_SECONDS` | `15` / `6` | Khoảng chờ giữa 2 lần lưu cùng loại vi phạm |
| `BEH_FACE_VIS_MIN`, `BEH_SHO_VIS_MIN`, `BEH_TURN_RATIO`, `BEH_BEND_RATIO` | `0.25`, `0.35`, `0.32`, `0.05` | Ngưỡng luật hành vi (xem `backend/ai_model/behavior.py`) |

`API_HOST`/`API_PORT` trong `core/config.py` chỉ mang tính tham khảo; lệnh chạy
uvicorn bên dưới mới quyết định địa chỉ lắng nghe.

## Chạy

Chạy từ **gốc dự án** để `load_dotenv()` đọc đúng `.env`:

```bash
# 1. Backend API
.venv/bin/uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000

# 2. Giao diện giám thị (Streamlit)
.venv/bin/streamlit run frontend/app.py
```

Lần khởi động đầu, backend tự tạo bảng, tự chạy migration cần thiết và tự tạo
tài khoản **`admin` / `Admin123`** nếu chưa có — hãy đổi mật khẩu ngay sau khi
đăng nhập. Muốn tạo admin khác:

```bash
.venv/bin/python backend/scripts/create_admin.py <tendangnhap> <matkhau> "Họ Tên"
```

Địa chỉ truy cập:

| Mục | URL |
|---|---|
| API docs (Swagger) | `http://localhost:8000/docs` |
| Giao diện giám thị | `http://localhost:8501` |
| Trang thi cho thí sinh | `http://localhost:8000/exam?session_id=<id>` |
| Trang test camera + AI | `http://localhost:8000/camera-test` |
| Health check | `http://localhost:8000/health` |

## Hướng dẫn sử dụng

### 1. Đăng nhập

Mở `http://localhost:8501`, đăng nhập bằng tài khoản admin hoặc tài khoản được
tạo từ API/trang quản trị. Giao diện gồm các trang: Giám sát trực tiếp, Thi online,
Lịch sử, Thống kê, Thiết bị, Tài khoản.

### 2. Giám sát phòng thi trực tiếp

1. Trang **Thiết bị**: admin đăng ký thiết bị biên, `DuongDanRTSP` nhận
   index webcam (`0`, `1`, ...) hoặc URL `rtsp://...`; nút "Kiểm tra" đo kết nối.
2. Trang **Giám sát trực tiếp**: nhập mã phòng thi, tên môn, chọn camera
   (hoặc "Camera máy chủ / Webcam") và chế độ nguồn (RTSP trực tiếp hoặc video mẫu
   `videos/test_exam.mp4`), bấm **Bắt đầu ca thi & Mở camera**.
3. Xem luồng trực tiếp có khung AI, danh sách cảnh báo mới; bấm vào cảnh báo để
   mở chi tiết sự kiện (ảnh bằng chứng + tọa độ), xác minh `Đúng`/`Sai` kèm nhãn sửa.
4. Bấm **Kết thúc ca thi & Đóng camera** để chốt phiên và trả thiết bị về trạng thái sẵn sàng.

Lưu ý: hệ thống chỉ chạy **một phiên camera trực tiếp tại một thời điểm**;
mở luồng mới khi đang chạy sẽ trả về phiên hiện tại.

### 3. Thi trực tuyến

1. Trang **Thi online**: tạo ca thi mới (phòng thi, môn thi).
2. Nhập danh sách thí sinh, mỗi dòng `SBD, Họ tên, Lớp` (ví dụ `TS001, Nguyễn Văn A, 12A1`).
3. Bấm **Mở ca thi**, sau đó gửi link `http://<địa-chỉ-server>:8000/exam?session_id=<id>` cho thí sinh.
4. Thí sinh mở link, nhập **SBD** (chỉ cần SBD nằm trong danh sách ca đang mở),
   cấp quyền camera. Trình duyệt gửi frame mỗi 2,5 giây; vào lại cùng SBD sẽ
   trả về đúng phiên đang mở kèm token mới.
5. Giám thị theo dõi lưới trạng thái từng thí sinh (đang giám sát, số sự kiện,
   số chờ kiểm tra, ảnh snapshot mới nhất). Thí sinh tự bấm "Kết thúc bài thi"
   hoặc giám thị **Kết thúc ca thi** để chốt toàn bộ phiên con.
6. Sự kiện và thống kê xem lại ở trang **Lịch sử** / **chi tiết phiên** / **Thống kê**.

## API chính

Xác thực: cookie `access_token`/`refresh_token` hoặc header `Authorization: Bearer <token>`.
Các endpoint thí sinh (`/candidates/join`, `/ingest/frame`, `/candidates/finish`)
không cần JWT — xác thực bằng SBD và token nộp frame.

| Nhóm | Method | Endpoint | Ghi chú |
|---|---|---|---|
| Users | POST | `/users/register`, `/users/login` | Đăng ký / đăng nhập |
| | GET | `/users/profile`, POST `/users/refresh`, `/users/logout` | Hồ sơ, làm mới, thu hồi token |
| | PUT | `/users/update`, `/users/change-password` | Sửa họ tên / đổi mật khẩu |
| | GET | `/users/list` | Admin |
| | PUT/POST | `/users/{id}`, `/users/create` | Admin đổi vai trò/trạng thái, tạo tài khoản |
| Devices | GET | `/devices`, `/devices/{id}` | Mọi user đăng nhập |
| | POST/PUT/DELETE | `/devices`, `/devices/{id}` | Admin; DELETE có thể bị chặn nếu còn ca thi |
| | POST | `/devices/{id}/test` | Kiểm tra kết nối camera/RTSP |
| Camera | POST | `/camera/start?device_id=&phong_thi=&mon_thi=&video_path=` | Tạo phiên + mở nguồn; `video_path` đè RTSP |
| | POST | `/camera/stop` | Dừng, chốt phiên |
| | GET | `/camera/video_feed`, `/camera/list`, `/camera/info`, `/camera/status` | Luồng MJPEG, danh sách nguồn, trạng thái |
| | GET | `/camera/snapshot` | Ảnh JPEG frame mới nhất đã vẽ AI |
| Candidates | POST | `/candidates/import`, GET `/candidates?session_id=` | Nhập/liệt kê danh sách thí sinh |
| | POST | `/candidates/join` | Thí sinh vào thi bằng SBD |
| | GET | `/candidates/overview?session_id=` | Lưới trạng thái cho giám thị |
| | POST | `/candidates/finish` | Thí sinh tự kết thúc (token) |
| | POST | `/candidates/leave/{session_id}` | Giám thị chốt phiên con |
| | POST | `/candidates/session/create`, `/candidates/session/{id}/open`, `/candidates/session/{id}/close` | Tạo/mở/đóng ca thi |
| | GET | `/candidates/session/{id}/snapshot` | Ảnh snapshot thí sinh |
| Ingest | POST | `/ingest/frame` | Form-data: `session_id`, `token`, `ts_client`, `frame` (JPEG ≤ 500 KB) |
| Events | GET | `/events/session/{id}`, `/events`, `/events/{id}` | Danh sách/chi tiết sự kiện |
| | PATCH | `/events/{id}` | `{"TrangThaiKiemTra": "dung"/"sai", "LoaiHanhVi": "cellphone"}` |
| | GET | `/events/system/notifications` | Thông báo cảnh báo mới nhất |
| | GET | `/events/evidences/{id}/file` | Tải ảnh bằng chứng |
| History | GET | `/history/sessions`, `/history/summary`, `/history/session/{id}` | Phân trang, tìm kiếm, chi tiết |
| | DELETE | `/history/session/{id}` | Chặn xóa phiên đang chạy |
| Stats | GET | `/stats/daily`, `/stats/by-date`, `/stats/weekly`, `/stats/summary`, `/stats/distribution` | Thống kê theo quyền admin/teacher |
| System | GET | `/health`, `/camera-test`, `/exam` | Health, trang test, trang thí sinh |

Chi tiết đầy đủ tham số xem tại `/docs` khi backend đang chạy.

## Mô hình AI và ngưỡng phát hiện

* **Model vật thể** (`backend/ai_model/weights/best_openvino_model`, fallback `best.pt`):
  YOLO26n-seg, thứ tự nhãn bắt buộc `["Cheat_Paper", "cellphone"]`, imgsz 512, conf 0.25.
* **Model hành vi** (`backend/ai_model/weights/yolo26n-pose_openvino_model`):
  YOLO26n-pose COCO-17, suy luận imgsz 320; luật hình học từ mũi/mắt/tai/vai phân loại
  `nhin_thang`, `quay_dau`, `quay_sau`, `cui_xuong` (xem `backend/ai_model/behavior.py`).
* **Debounce**: vật thể cần ≥ 3/5 frame, hành vi cần ≥ 4/6 frame (riêng `quay_sau` 3/4),
  cooldown 15 giây cho vật thể và 6 giây cho hành vi.
* **Thi online bổ sung**: `vang_mat` khi không thấy người > 10 giây (chỉ ghi 1 lần mỗi đợt),
  `nhieu_nguoi` khi phát hiện > 1 người; worker tự dừng khi phiên kết thúc hoặc không
  nhận frame trong 120 giây.
* Thiếu weights: hệ thống không crash, chỉ log cảnh báo và trả kết quả rỗng; thiếu
  model pose thì chỉ tắt nhánh hành vi.

## Cơ sở dữ liệu

Các bảng chính (tự tạo bằng `Base.metadata.create_all` khi khởi động):

| Bảng | Nội dung |
|---|---|
| `tbl_user` | Tài khoản, vai trò `admin`/`teacher`, trạng thái `hoat_dong`/`khoa` |
| `tbl_edgedevice` | Thiết bị biên: tên, `DuongDanRTSP`, vị trí, trạng thái |
| `tbl_monitoring_sessions` | Ca thi/phiên giám sát: giờ bắt đầu/kết thúc, phòng, môn, thiết bị, thí sinh (`FK_MaThiSinh`), token tham gia |
| `tbl_thi_sinh` | Danh sách thí sinh theo ca, SBD duy nhất trong một ca |
| `tbl_detected_events` | Sự kiện gian lận: loại hành vi, tọa độ, độ tin cậy, trạng thái kiểm tra, người kiểm tra |
| `tbl_evidences` | Bằng chứng gắn sự kiện, đường dẫn tệp trong `images/` |
| `statistics` | Bản ghi thống kê định kỳ (`total_students`, `sleeping_count`, `focus_rate`) |

Nhãn hợp lệ của `LoaiHanhVi`: `Cheat_Paper`, `cellphone`, `quay_dau`, `quay_sau`,
`cui_xuong`, `vang_mat`, `nhieu_nguoi`, `Answer_paper` (tương thích weights cũ).

Khi khởi động, `backend/main.py` tự bổ sung cột `FK_MaThiSinh`, `TokenThamGia`,
nới `FK_MaThietBi` cho phép NULL và cập nhật CHECK constraint. Với DB cũ có thể
chạy thủ công (từ gốc dự án):

```bash
.venv/bin/python backend/scripts/migrate_online_exam.py
.venv/bin/python backend/scripts/migrate_session_token.py
.venv/bin/python backend/scripts/migrate_event_labels.py
```

## Huấn luyện / thay mô hình

Repo **không kèm dataset và log train** (đã gitignore: `training/dataset_*`,
`training/realworld_data`, `training/runs`, `runs/`). Hiện có sẵn:

* `backend/ai_model/weights/best.pt` và `best_openvino_model/` — model seg 2 nhãn đang dùng.
* `training/yolo26n-pose_openvino_model/` — model pose OpenVINO (bản dùng ở backend).
* `training/scripts/check_dataset.py` — kiểm tra dataset YOLO-seg (khớp ảnh/nhãn,
  phân bố lớp, rò rỉ train/valid, vẽ mẫu).
* `backend/scripts/migrate_dataset.py` — gộp `training/dataset_seg` + `training/realworld_data`
  thành `training/dataset_seg_v4` với 2 nhãn (cần tự chuẩn bị dữ liệu nguồn).

Quy trình huấn luyện lại model vật thể:

```bash
.venv/bin/python backend/scripts/migrate_dataset.py --clean
.venv/bin/python training/scripts/check_dataset.py --root training/dataset_seg_v4
.venv/bin/yolo task=segment mode=train model=<yolo26n-seg.pt> \
  data=training/dataset_seg_v4/data.yaml epochs=50 imgsz=512 batch=2 device=cpu
.venv/bin/yolo export model=runs/segment/train/weights/best.pt format=openvino imgsz=512
cp -R runs/segment/train/weights/best_openvino_model backend/ai_model/weights/
```

Thay model không cần sửa code: trỏ `MODEL_PATH`/`POSE_MODEL_PATH` trong `.env`
tới weights mới, hoặc thay trực tiếp thư mục trong `backend/ai_model/weights/`.
Giữ đúng thứ tự nhãn `Cheat_Paper`, `cellphone` khi train seg.

## Cấu trúc thư mục

```text
backend/
  main.py                    # FastAPI, CORS, router, auto-migration, tạo admin mặc định
  core/                      # config, JWT/dependencies, security, rate-limit, blacklist, logger
  database/database.py       # Engine + SessionLocal (validate DATABASE_URL khi import)
  models/                    # ORM: tbl_user, tbl_edgedevice, tbl_monitoring_sessions,
                             #      tbl_thi_sinh, tbl_detected_events, tbl_evidences, statistics
  schemas/                   # Pydantic request/response
  crud/                      # Truy vấn DB
  api/router/                # users, devices, camera, candidates, ingest, events, history, statistics
  service/                   # camera_service, camera_state, pipeline_service, stream_service,
                             # ingest_service, session_service, statistics_service, user_service
  ai_model/                  # ai_pipeline.py (seg + track), behavior.py (luật pose), weights/
  scripts/                   # create_admin, migrate_online_exam, migrate_session_token,
                             # migrate_event_labels, migrate_dataset
  static/                    # exam.html (thí sinh), camera_test.html (test nhanh)
  tests/test_security.py     # Script kiểm thử bảo mật thủ công (cần backend đang chạy)
  utils/                     # create_admin (bản argparse), label_utils
frontend/
  app.py                     # Điểm vào Streamlit, khôi phục phiên từ localStorage/query params
  config.py                  # API_BASE_URL (đổi khi chạy server khác 127.0.0.1)
  components/                # evidence_dialog, nav_tabs
  pages/                     # login, home, online_exam, history, session_detail,
                             # event_detail, statistics, devices, users
  services/                  # Gọi API: auth, device, candidate, event, history, stats, user
  styles/, utils/            # CSS và helper (http, auth_guard, load_css, notify, ...)
training/
  yolo26n-pose_openvino_model/  # Model pose OpenVINO
  scripts/check_dataset.py      # Kiểm tra dataset YOLO-seg
videos/                      # Video mẫu test_exam.mp4, test_exam_2.mp4
images/                      # Ảnh bằng chứng sinh ra khi chạy (gitignore)
docker-compose.yml           # PostgreSQL 16 (examcheat / examcheat123)
setup.sh                     # Cài đặt tự động
```

## Kiểm thử

```bash
# Cần backend đang chạy ở http://localhost:8000
.venv/bin/python backend/tests/test_security.py
```

Script tự đăng ký user test, kiểm tra rate-limit đăng nhập, xác thực JWT, refresh
và thu hồi token, in bảng kết quả PASS/FAIL.

## Xử lý sự cố

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `ValueError: DATABASE_URL must be set` | Chưa có `.env` hoặc chạy lệnh ngoài gốc dự án (`.env` được đọc theo thư mục hiện hành) |
| Backend không kết nối DB | PostgreSQL chưa chạy: `docker compose up -d postgres`; kiểm tra cổng 5432 bị chiếm |
| `ModuleNotFoundError: streamlit_autorefresh` | Chưa cài frontend deps: `.venv/bin/pip install -r frontend/requirements.txt` |
| Webcam không mở | Cấp quyền camera cho terminal/trình duyệt, đóng ứng dụng đang chiếm webcam; kiểm tra bằng nút Test ở trang Thiết bị |
| RTSP treo/không kết nối | Sai IP/cổng hoặc camera ngoại tuyến; hệ thống đã giới hạn timeout 2,5 giây và sẽ báo lỗi rõ |
| `/exam` báo không mở được camera | `getUserMedia` yêu cầu `localhost` hoặc HTTPS; dùng Chrome/Edge/Firefox bản mới |
| Link thi trỏ về `127.0.0.1` | `frontend/config.py` đang hardcode `API_BASE_URL`; đổi thành IP LAN/tên miền server và thêm origin vào `ALLOWED_ORIGINS` rồi khởi động lại Streamlit |
| Lỗi CORS trên trình duyệt | Thêm origin của Streamlit/FE vào `ALLOWED_ORIGINS` hoặc đặt `ENVIRONMENT=production` kèm danh sách origin đúng |
| Log `Weights not found` | Sai `MODEL_PATH`/`POSE_MODEL_PATH`; hệ thống vẫn chạy nhưng không phát hiện gì |
| Video mẫu chạy mãi | Video file được thiết kế lặp lại (`loop_video=True`); bấm Kết thúc ca thi để dừng |

## Lưu ý và giới hạn

* `Cheat_Paper` có ít mẫu kiểm chứng nên độ chính xác thấp hơn `cellphone`; nên bổ
  sung ảnh thật trước khi dùng chính thức.
* Model pose hiện dùng pretrained COCO, chưa fine-tune trên footage phòng thi nên
  ngưỡng hành vi là tạm thời; video test ít thấy đầu, cần tune lại `BEH_*` với dữ liệu thật.
* `quay_sau` và luật `vang_mat`/`nhieu_nguoi` chỉ áp dụng khi bật model pose; camera
  tĩnh chỉ phát hiện vật thể (`Cheat_Paper`, `cellphone`).
* Chỉ chạy được một phiên camera trực tiếp đồng thời (CameraState là singleton),
  trong khi các phiên thi online chạy worker song song theo từng phiên.
* Xóa phiên chỉ xóa dữ liệu trong DB; ảnh bằng chứng trong `images/` không tự xóa.
* Thống kê tuần dùng `to_char` của PostgreSQL nên yêu cầu đúng PostgreSQL.
* Bảo mật khi triển khai thật: đổi `Admin123`, đổi `SECRET_KEY`, chạy HTTPS
  (`ENVIRONMENT=production`), siết `ALLOWED_ORIGINS`, giới hạn quyền truy cập
  `/users/register` (endpoint hiện cho phép truyền `VaiTro`, cần hạn chế trước khi
  mở công khai) và không chia sẻ link/token ca thi ra ngoài phạm vi phòng thi.
