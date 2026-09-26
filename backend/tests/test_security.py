#!/usr/bin/env python3
"""Kiểm thử bảo mật: xác thực JWT và giới hạn lượt đăng nhập.
Luồng chính: đăng ký → đăng nhập sai tới ngưỡng → đăng nhập đúng → làm mới và thu hồi token."""

import requests
import time
import json
from datetime import datetime

# Cấu hình địa chỉ API và tài khoản kiểm thử
API_URL = "http://localhost:8000"
TEST_USERNAME = f"test_{int(time.time())}"
TEST_PASSWORD = "Password123"
TEST_NAME = "Security Test User"

class SecurityTester:
    """Bộ kiểm thử bảo mật qua HTTP, gom kết quả từng bước.
    Điểm logic: dùng một session để giữ cookie xuyên suốt các bước."""
    def __init__(self, base_url=API_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []

    def log(self, test_name, status, message):
        """Ghi một kết quả kiểm thử vào danh sách tổng hợp."""
        emoji = "✅" if status == "PASS" else "❌"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {emoji} {test_name}: {message}")
        self.results.append({"test": test_name, "status": status, "message": message})

    def test_registration(self):
        """Kiểm thử đăng ký và chặn tên đăng nhập trùng.
        Điểm logic: đăng ký đúng trả 200, đăng ký lại tên cũ phải trả 409."""
        print("\n📝 Testing Registration Endpoint...")

        # Trường hợp 1: đăng ký hợp lệ
        payload = {
            "TenDangNhap": TEST_USERNAME,
            "MatKhau": TEST_PASSWORD,
            "HoVaTen": TEST_NAME
        }
        response = self.session.post(f"{self.base_url}/users/register", json=payload)

        if response.status_code == 200:
            self.log("Registration", "PASS", f"User created: {TEST_USERNAME}")
        else:
            self.log("Registration", "FAIL", f"Status {response.status_code}: {response.text}")

        # Trường hợp 2: đăng ký trùng tên đăng nhập
        response = self.session.post(f"{self.base_url}/users/register", json=payload)
        if response.status_code == 409:  # Conflict
            self.log("Duplicate Registration", "PASS", "Correctly rejected duplicate username")
        else:
            self.log("Duplicate Registration", "FAIL", f"Expected 409, got {response.status_code}")

    def test_login_rate_limiting(self):
        """Kiểm thử chặn đăng nhập sai liên tiếp.
        Điểm logic: 5 lượt sai đầu trả 401, lượt thứ 6 phải trả 429."""
        print("\n🔐 Testing Login Rate Limiting...")

        # Đăng nhập sai 6 lần: 5 lần cho qua, lần 6 phải bị chặn
        for attempt in range(1, 7):
            payload = {"TenDangNhap": TEST_USERNAME, "MatKhau": "WrongPassword"}
            response = self.session.post(f"{self.base_url}/users/login", json=payload)

            if attempt < 5:
                if response.status_code == 401:
                    self.log(f"Failed Login Attempt {attempt}", "PASS", "Rejected bad credentials")
                else:
                    self.log(f"Failed Login Attempt {attempt}", "FAIL", f"Unexpected status {response.status_code}")

            elif attempt == 5:
                if response.status_code == 401:
                    self.log("Failed Login Attempt 5", "PASS", "Rejected after 5 failed attempts")
                else:
                    self.log("Failed Login Attempt 5", "FAIL", f"Unexpected status {response.status_code}")

            elif attempt == 6:
                if response.status_code == 429:  # Too Many Requests
                    self.log("Rate Limit Enforcement", "PASS", f"Blocked 6th attempt with 429: {response.json()['detail']}")
                else:
                    self.log("Rate Limit Enforcement", "FAIL", f"Expected 429, got {response.status_code}")

            time.sleep(0.2)  # Nghỉ ngắn giữa các lượt để tách từng lần thử

    def test_successful_login(self):
        """Kiểm thử đăng nhập đúng và cấp token.
        Điểm logic: chờ 30 giây cho hết cửa sổ chặn rồi dùng tài khoản mới tinh."""
        print("\n✅ Testing Successful Login...")

        # Chờ hết cửa sổ chặn trước khi thử lại
        print("   ⏳ Waiting for rate limit to cool down (30 seconds)...")
        time.sleep(30)

        # Session mới để thoát đếm rate-limit của IP cũ
        self.session = requests.Session()

        # Đăng ký tài khoản mới để có lượt đăng nhập sạch
        test_username = f"clean_{int(time.time())}"
        register_payload = {
            "TenDangNhap": test_username,
            "MatKhau": TEST_PASSWORD,
            "HoVaTen": "Clean Test"
        }
        self.session.post(f"{self.base_url}/users/register", json=register_payload)

        # Đăng nhập bằng tài khoản vừa tạo
        login_payload = {"TenDangNhap": test_username, "MatKhau": TEST_PASSWORD}
        response = self.session.post(f"{self.base_url}/users/login", json=login_payload)

        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "refresh_token" in data:
                self.log("Successful Login", "PASS", f"Tokens generated for {test_username}")
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                self.test_username = test_username
                return True
        else:
            self.log("Successful Login", "FAIL", f"Status {response.status_code}: {response.text}")
            return False

        return False

    def test_authentication(self):
        """Kiểm thử vào endpoint bảo vệ bằng JWT.
        Điểm logic: thử cả cookie mặc định và header Bearer."""
        print("\n🔒 Testing Authentication...")

        if not hasattr(self, 'access_token'):
            self.log("Profile Access", "FAIL", "No access token from login")
            return

        # Thử với cookie mặc định của session
        response = self.session.get(f"{self.base_url}/users/profile")

        if response.status_code == 200:
            self.log("Profile Access (Cookie)", "PASS", "Successfully accessed protected endpoint")
        else:
            self.log("Profile Access (Cookie)", "FAIL", f"Status {response.status_code}")

        # Thử với header Bearer
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(f"{self.base_url}/users/profile", headers=headers)

        if response.status_code == 200:
            self.log("Profile Access (Header)", "PASS", "Authentication works with Bearer token")
        else:
            self.log("Profile Access (Header)", "FAIL", f"Status {response.status_code}")

    def test_token_refresh(self):
        """Kiểm thử cấp access token mới từ refresh token.
        Điểm logic: thiếu refresh token thì bỏ qua, không gọi API."""
        print("\n🔄 Testing Token Refresh...")

        if not hasattr(self, 'refresh_token'):
            self.log("Token Refresh", "FAIL", "No refresh token available")
            return

        response = self.session.post(f"{self.base_url}/users/refresh")

        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                self.log("Token Refresh", "PASS", "Successfully generated new access token")
                self.access_token = data["access_token"]
            else:
                self.log("Token Refresh", "FAIL", "No access token in response")
        else:
            self.log("Token Refresh", "FAIL", f"Status {response.status_code}: {response.json()}")

    def test_logout(self):
        """Kiểm thử đăng xuất và thu hồi token.
        Điểm logic: sau logout mà vào hồ sơ phải trả 401 mới đạt."""
        print("\n🚪 Testing Logout...")

        response = self.session.post(f"{self.base_url}/users/logout")

        if response.status_code == 200:
            self.log("Logout", "PASS", "Successfully logged out")

            # Vào lại endpoint bảo vệ, phải bị từ chối
            time.sleep(0.5)
            response = self.session.get(f"{self.base_url}/users/profile")

            if response.status_code == 401:
                self.log("Token Blacklist", "PASS", "Token correctly invalidated after logout")
            else:
                self.log("Token Blacklist", "FAIL", f"Expected 401 after logout, got {response.status_code}")
        else:
            self.log("Logout", "FAIL", f"Status {response.status_code}")

    def test_health_check(self):
        """Kiểm thử endpoint sức khỏe công khai.
        Điểm logic: phải trả trạng thái healthy mới coi như API sẵn sàng."""
        print("\n💚 Testing Health Check...")

        response = requests.get(f"{self.base_url}/health")

        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] == "healthy":
                self.log("Health Check", "PASS", f"API healthy - Environment: {data.get('environment', 'unknown')}")
            else:
                self.log("Health Check", "FAIL", "Unexpected response format")
        else:
            self.log("Health Check", "FAIL", f"Status {response.status_code}")

    def summary(self):
        """In tóm tắt số lượt đạt và hỏng cùng tỉ lệ thành công."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = len(self.results)

        for result in self.results:
            emoji = "✅" if result["status"] == "PASS" else "❌"
            print(f"{emoji} {result['test']}: {result['message']}")

        print("\n" + "-"*60)
        print(f"Results: {passed}/{total} passed, {failed} failed")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print("="*60)

    def run_all(self):
        """Chạy toàn bộ bộ kiểm thử bảo mật theo đúng thứ tự.
        Điểm logic: API không reachable thì dừng ngay; chỉ test token khi đăng nhập sạch thành công."""
        print("\n" + "="*60)
        print("🔐 SECURITY TEST SUITE")
        print("="*60)
        print(f"API URL: {self.base_url}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        # API không reachable thì dừng ngay
        try:
            self.test_health_check()
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return

        try:
            self.test_registration()
            self.test_login_rate_limiting()

            if self.test_successful_login():
                self.test_authentication()
                self.test_token_refresh()
                self.test_logout()

            self.summary()

        except Exception as e:
            print(f"❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    tester = SecurityTester()
    tester.run_all()
