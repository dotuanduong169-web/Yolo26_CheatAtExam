# ExamCheat AI — Hệ thống phát hiện gian lận phòng thi

Hệ thống giám sát thi cử bằng AI, hỗ trợ 2 chế độ:

* **Phòng thi trực tiếp**: camera máy chủ, IP camera/RTSP hoặc video mẫu → mô hình
  YOLO26n-seg phát hiện `Cheat_Paper` (tài liệu) và `cellphone` (điện thoại),
  mô hình YOLO26n-pose phát hiện hành vi `quay_dau`, `quay_sau`, `cui_xuong`.
* **Thi trực tuyến**: thí sinh mở link `/exam`, nhập SBD, dùng webcam trình duyệt
  gửi frame về server; mỗi phiên thí sinh có worker AI riêng, giám thị theo dõi
  trạng thái từng thí sinh trên lưới dashboard.
* **2 camera/thí sinh (demo)**: webcam máy tính là camera trước (`front`) + điện thoại
  là camera phụ (`side`) mở link riêng, giúp quan sát cả mặt và góc bàn học.

Khi vi phạm được xác nhận (debounce nhiều frame), hệ thống lưu ảnh bằng chứng vào
`images/` và ghi sự kiện vào PostgreSQL. Ảnh snapshot đi qua pipeline 2 bước:
lưu **raw** trước, sau đó chuẩn hóa thành `normalized`/`thumbnail`/`annotated`;
DB chỉ lưu đường dẫn + metadata, không lưu blob. Giám thị có thể xác minh đúng/sai
và sửa nhãn thủ công; thống kê tự tính lại theo nhãn đã sửa.

## Tính năng

* Giám sát trực tiếp: xem luồng MJPEG đã vẽ khung/polygon AI, chụp snapshot, theo dõi FPS.
* Phát hiện vật thể gian lận bằng YOLO26n-seg 2 nhãn kèm mask polygon (OpenVINO tăng tốc CPU).
* Phát hiện hành vi bằng YOLO26n-pose + luật hình học keypoints (không cần train lại).
* Chống nhiễu: debounce theo cửa sổ frame (vật thể 3/5, hành vi 4/6) và cooldown 15s/6s.
* Thi online: tạo ca thi, nhập danh sách thí sinh (SBD, họ tên, lớp), mở/đóng ca,
  link dự thi, vào thi idempotent (vào lại vẫn giữ phiên), token riêng theo từng
  luồng camera lưu DB (sống qua restart), tự dừng worker khi phiên kết thúc hoặc idle 120 giây.
* 2 camera/thí sinh: camera trước `front` chạy object + pose + `vang_mat`/`nhieu_nguoi`;
  camera phụ `side` (điện thoại) chỉ chạy object detection, có token/worker/queue riêng.
* Snapshot pipeline: `images/raw/` → `images/processed/` (`normalized`, `thumbnail`,
  `annotated`), metadata ở `tbl_snapshot` / `tbl_snapshot_processed`; lưu raw trước,
  chuẩn hóa sau, dashboard chỉ đọc ảnh đã chuẩn hóa.
* Quy tắc riêng cho thi online: `vang_mat` (vắng mặt > 10 giây), `nhieu_nguoi` (> 1 người).
* Lịch sử: danh sách ca thi, chi tiết phiên, xem/xác minh sự kiện, xóa phiên (admin xóa mọi phiên).
* Thống kê: theo ngày, theo tuần, theo khoảng ngày, tổng hợp và phân bố hành vi; biểu đồ Plotly.
* Quản trị: JWT (cookie HttpOnly hoặc Bearer), phân quyền `admin`/`teacher`,
  rate-limit đăng nhập/đăng ký, blacklist token khi logout, quản lý thiết bị biên RTSP.

## Kiến trúc

```text
Trình duyệt giám thị ── Streamlit :8501 ──┐
Trình duyệt thí sinh ── /exam (webcam) ───┼── FastAPI :8000 ── PostgreSQL 16 :5433
Điện thoại thí sinh ── /exam?role=side ───┘        │
                                                    ├── YOLO26n-seg  (OpenVINO, fallback .pt)
                                                    ├── YOLO26n-pose (OpenVINO) + luật hành vi
                                                    ├── ảnh gốc:   images/raw/ (gitignore)
                                                    ├── ảnh d.suất: images/processed/ (gitignore)
                                                    └── luồng MJPEG /camera/video_feed cho trang giám sát
```

Luồng xử lý phòng thi: thread capture đọc frame liên tục → worker infer riêng vẽ
kết quả → kiểm tra debounce/cooldown → lưu ảnh + sự kiện. Luồng thi online:
browser gửi JPEG mỗi 2,5 giây kèm `vai_tro` → hàng đợi riêng từng luồng camera →
worker riêng từng `(phiên, vai trò)` → debounce → snapshot raw → chuẩn hóa.

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
| `SAVE_INTERVAL_SECONDS` | `10` | Chu kỳ lưu snapshot sự kiện định kỳ |
| `SNAPSHOT_INTERVAL_SECONDS` | `30` | Chu kỳ lưu snapshot nền cho mỗi luồng camera (giây) |
| `SNAPSHOT_MAX_WIDTH` / `SNAPSHOT_THUMB_WIDTH` | `1280` / `480` | Cạnh rộng tối đa của ảnh normalized / thumbnail |
| `SNAPSHOT_JPEG_QUALITY` | `85` | Chất lượng JPEG khi ghi ảnh đã chuẩn hóa |
| `TIMELINE_ENABLED` | `1` | Bật nhật ký tick (`tbl_candidate_timeline`); `0` để tắt |
| `TIMELINE_HEARTBEAT_SECONDS` | `30` | Chu kỳ ghi heartbeat khi không có cảnh báo (giây, tối thiểu 5) |
| `TIMELINE_IMAGE_MAX_WIDTH` / `TIMELINE_JPEG_QUALITY` | `480` / `72` | Kích thước và chất lượng thumbnail nhẹ cho mỗi tick |
| `OBJECT_COOLDOWN_SECONDS` / `POSE_COOLDOWN_SECONDS` | `15` / `6` | Khoảng chờ giữa 2 lần lưu cùng loại vi phạm |
| `BEH_FACE_VIS_MIN`, `BEH_SHO_VIS_MIN`, `BEH_TURN_RATIO`, `BEH_BEND_RATIO` | `0.25`, `0.35`, `0.32`, `0.05` | Ngưỡng luật hành vi (xem `backend/ai_model/behavior.py`) |

`API_HOST`/`API_PORT` trong `core/config.py` chỉ mang tính tham khảo; lệnh chạy
uvicorn bên dưới mới quyết định địa chỉ lắng nghe.

`API_BASE_URL` là biến môi trường của Streamlit (không nằm trong `.env` backend),
mặc định `http://127.0.0.1:8000`; khi cho điện thoại mở link camera phụ trong LAN,
đặt `API_BASE_URL=http://<IP-LAN-của-máy-chủ>:8000` trước khi chạy Streamlit.

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
| Link camera phụ (điện thoại) | Giám thị bấm **Link camera phụ** ở card thí sinh để lấy link `.../exam?session_id=<id>&role=side&token=...` |
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
5. **Camera phụ (điện thoại):** trên card thí sinh đang thi, bấm **Link camera phụ**
   → mở link trên điện thoại (cùng mạng LAN, HTTPS hoặc localhost). Điện thoại dùng
   camera sau, gửi frame với `vai_tro=side`, không ảnh hưởng luồng webcam `front`.
   Link giữ nguyên hiệu lực tới khi ca thi kết thúc. Khi chạy demo qua điện thoại,
   đặt `API_BASE_URL=http://<IP-LAN-của-server>:8000` trước khi khởi động Streamlit
   để link cấp cho điện thoại trỏ đúng địa chỉ mở được.
6. Giám thị theo dõi lưới trạng thái từng thí sinh với **2 ô ảnh** (trước/phụ),
   số sự kiện, số chờ kiểm tra. Thí sinh tự bấm "Kết thúc bài thi" trên máy tính
   (không bấm trên điện thoại) hoặc giám thị **Kết thúc ca thi** để chốt toàn bộ phiên con.
7. Sự kiện và thống kê xem lại ở trang **Lịch sử** / **chi tiết phiên** / **Thống kê**;
   mỗi sự kiện ghi rõ nguồn **Camera trước** hay **Camera phụ**.

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
| | POST | `/candidates/join` | Thí sinh vào thi: `SBD` + `VaiTro` (`front`/`side`) |
| | GET | `/candidates/overview?session_id=` | Lưới trạng thái + trạng thái 2 camera |
| | POST | `/candidates/finish` | Thí sinh tự kết thúc (token front) |
| | POST | `/candidates/leave/{session_id}` | Giám thị chốt phiên con |
| | POST | `/candidates/session/create`, `/candidates/session/{id}/open`, `/candidates/session/{id}/close` | Tạo/mở/đóng ca thi |
| | POST | `/candidates/session/{id}/stream/{vai_tro}/token` | Cấp/tái sử dụng link camera (`refresh=true` để đổi token) |
| | GET | `/candidates/session/{id}/streams` | Danh sách luồng camera của phiên con |
| | GET | `/candidates/session/{id}/attach?token=` | Mở link camera bằng token có sẵn (không mint token mới) |
| | GET | `/candidates/session/{id}/snapshot?role=&variant=` | Ảnh snapshot: `role=front/side`, `variant=auto/normalized/thumbnail/annotated` |
| Ingest | POST | `/ingest/frame` | Form-data: `session_id`, `token`, `ts_client`, `vai_tro` (`front/side`), `frame` (JPEG ≤ 500 KB) |
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
* **Debounce**: vật thể cần ≥ 3/5 frame, hành vi cần ≥ 4/6 frame để kích hoạt lưu
  (riêng `quay_sau` dùng cửa sổ 3/4 và được giữ ngay khi đã có snapshot), cooldown
  15 giây cho vật thể và 6 giây cho hành vi.
* **Thi online bổ sung**: `vang_mat` khi không thấy người > 10 giây (chỉ ghi 1 lần mỗi đợt),
  `nhieu_nguoi` khi phát hiện > 1 người; worker tự dừng khi phiên kết thúc hoặc không
  nhận frame trong 120 giây.
* **Camera phụ `side`**: chỉ chạy YOLO26n-seg (`enable_pose=False`), không kích hoạt
  luật tư thế/`vang_mat`/`nhieu_nguoi` để tránh báo trùng và giảm tải CPU.
* Thiếu weights: hệ thống không crash, chỉ log cảnh báo và trả kết quả rỗng; thiếu
  model pose thì chỉ tắt nhánh hành vi.

## Cơ sở dữ liệu

Các bảng chính (tự tạo bằng `Base.metadata.create_all` khi khởi động):

| Bảng | Nội dung |
|---|---|
| `tbl_user` | Tài khoản, vai trò `admin`/`teacher`, trạng thái `hoat_dong`/`khoa` |
| `tbl_edgedevice` | Thiết bị biên: tên, `DuongDanRTSP`, vị trí, trạng thái |
| `tbl_monitoring_sessions` | Ca thi/phiên giám sát: giờ bắt đầu/kết thúc, phòng, môn, thiết bị, thí sinh (`FK_MaThiSinh`), token tham gia (legacy) |
| `tbl_thi_sinh` | Danh sách thí sinh theo ca, SBD duy nhất trong một ca |
| `tbl_camera_stream` | Luồng camera `front`/`side` của phiên con: token riêng, trạng thái, lần nhận cuối |
| `tbl_snapshot` | Metadata ảnh gốc (`images/raw/`): hash, kích thước, trạng thái xử lý |
| `tbl_snapshot_processed` | Ảnh dẫn xuất (`normalized`/`thumbnail`/`annotated`) trong `images/processed/` |
| `tbl_detected_events` | Sự kiện gian lận: loại hành vi, tọa độ, độ tin cậy, trạng thái kiểm tra, người kiểm tra, vai trò camera |
| `tbl_evidences` | Bằng chứng gắn sự kiện, đường dẫn tệp trong `images/`, vai trò camera |
| `tbl_candidate_timeline` | Nhật ký quan sát theo tick: mọi tick có cảnh báo, tick đổi trạng thái, heartbeat 30 giây; kèm thumbnail, thí sinh, độ trễ `DoTreMs` và liên kết sự kiện |

Số liệu thống kê được tổng hợp trực tiếp từ `tbl_detected_events` (sự kiện đã
debounce) và `tbl_candidate_timeline` (mốc quan sát đầy đủ); model `statistics`
cũ không còn được đăng ký/ghi dữ liệu.

Nhãn hợp lệ của `LoaiHanhVi`: `Cheat_Paper`, `cellphone`, `quay_dau`, `quay_sau`,
`cui_xuong`, `vang_mat`, `nhieu_nguoi`, `Answer_paper` (tương thích weights cũ).

Khi khởi động, `backend/main.py` tự tạo các bảng mới (`tbl_camera_stream`,
`tbl_snapshot`, `tbl_snapshot_processed`, `tbl_candidate_timeline`) và tự bổ sung `FK_MaThiSinh`,
`VaiTroCamera` (trên sự kiện/bằng chứng), nới `FK_MaThietBi`
cho phép NULL và cập nhật CHECK constraint. Cột `TokenThamGia` (legacy) được thêm
bằng script riêng. Với DB cũ có thể chạy thủ công (từ gốc dự án):

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
                             #      tbl_thi_sinh, tbl_camera_stream, tbl_snapshot,
                             #      tbl_snapshot_processed, tbl_detected_events, tbl_evidences
  schemas/                   # Pydantic request/response
  crud/                      # Truy vấn DB
  api/router/                # users, devices, camera, candidates, ingest, events, history, statistics
  service/                   # camera_service, camera_state, pipeline_service, stream_service,
                             # ingest_service, snapshot_service, session_service,
                             # statistics_service, user_service
  ai_model/                  # ai_pipeline.py (seg + track), behavior.py (luật pose), weights/
  scripts/                   # create_admin, migrate_online_exam, migrate_session_token,
                             # migrate_event_labels, migrate_dataset
  static/                    # exam.html (thí sinh), camera_test.html (test nhanh)
  tests/test_security.py     # Script kiểm thử bảo mật thủ công (cần backend đang chạy)
  utils/                     # create_admin (bản argparse), label_utils
frontend/
  app.py                     # Điểm vào Streamlit, khôi phục phiên từ localStorage/query params
  config.py                  # API_BASE_URL (env, mặc định http://127.0.0.1:8000)
  components/                # evidence_dialog, nav_tabs
  pages/                     # login, home, online_exam, history, session_detail,
                             # event_detail, statistics, devices, users
  services/                  # Gọi API: auth, device, candidate, event, history, stats, user
  styles/, utils/            # CSS và helper (http, auth_guard, load_css, notify, ...)
training/
  yolo26n-pose_openvino_model/  # Model pose OpenVINO
  scripts/check_dataset.py      # Kiểm tra dataset YOLO-seg
videos/                      # Video mẫu test_exam.mp4, test_exam_2.mp4
images/                      # Ảnh sinh ra khi chạy (gitignore): raw/ + processed/ + bằng chứng
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
| Backend không kết nối DB | PostgreSQL chưa chạy: `docker compose up -d postgres`; kiểm tra cổng 5433 bị chiếm |
| `ModuleNotFoundError: streamlit_autorefresh` | Chưa cài frontend deps: `.venv/bin/pip install -r frontend/requirements.txt` |
| Webcam không mở | Cấp quyền camera cho terminal/trình duyệt, đóng ứng dụng đang chiếm webcam; kiểm tra bằng nút Test ở trang Thiết bị |
| RTSP treo/không kết nối | Sai IP/cổng hoặc camera ngoại tuyến; hệ thống đã giới hạn timeout 2,5 giây và sẽ báo lỗi rõ |
| `/exam` báo không mở được camera | `getUserMedia` yêu cầu `localhost` hoặc HTTPS; dùng Chrome/Edge/Firefox bản mới |
| Link thi trỏ về `127.0.0.1` | Đặt `API_BASE_URL=http://<IP-LAN-của-server>:8000` trước khi chạy Streamlit (mặc định `http://127.0.0.1:8000`); thêm origin frontend vào `ALLOWED_ORIGINS` nếu cần |
| Lỗi CORS trên trình duyệt | Thêm origin của Streamlit/FE vào `ALLOWED_ORIGINS` hoặc đặt `ENVIRONMENT=production` kèm danh sách origin đúng |
| Log `Weights not found` | Sai `MODEL_PATH`/`POSE_MODEL_PATH`; hệ thống vẫn chạy nhưng không phát hiện gì |
| Video mẫu chạy mãi | Video file được thiết kế lặp lại (`loop_video=True`); bấm Kết thúc ca thi để dừng |

## Lưu ý và giới hạn

* `Cheat_Paper` có ít mẫu kiểm chứng nên độ chính xác thấp hơn `cellphone`; nên bổ
  sung ảnh thật trước khi dùng chính thức.
* Model pose hiện dùng pretrained COCO, chưa fine-tune trên footage phòng thi nên
  ngưỡng hành vi là tạm thời; video test ít thấy đầu, cần tune lại `BEH_*` với dữ liệu thật.
* `quay_sau` và luật `vang_mat`/`nhieu_nguoi` chỉ áp dụng cho camera trước (`front`)
  khi bật model pose; camera phụ (`side`) và camera tĩnh chỉ phát hiện vật thể
  (`Cheat_Paper`, `cellphone`).
* Camera phụ cần cùng mạng LAN với server và trình duyệt hỗ trợ `getUserMedia`;
  trên điện thoại nên dùng HTTPS (hoặc localhost qua USB debugging) để trình duyệt
  cấp quyền camera. Link camera phụ chứa token nên không chia sẻ ra ngoài phòng thi.
* Chỉ chạy được một phiên camera trực tiếp đồng thời (CameraState là singleton),
  trong khi các phiên thi online chạy worker song song theo từng phiên.
* Xóa phiên chỉ xóa dữ liệu trong DB; ảnh bằng chứng trong `images/` không tự xóa.
* Thống kê tuần dùng `to_char` của PostgreSQL nên yêu cầu đúng PostgreSQL.
* Bảo mật khi triển khai thật: đổi `Admin123`, đổi `SECRET_KEY`, chạy HTTPS
  (`ENVIRONMENT=production`), siết `ALLOWED_ORIGINS`, giới hạn quyền truy cập
  `/users/register` (endpoint hiện cho phép truyền `VaiTro`, cần hạn chế trước khi
  mở công khai) và không chia sẻ link/token ca thi ra ngoài phạm vi phòng thi.
