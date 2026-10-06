"""
Script khám phá sâu hơn các API endpoint dựa trên cấu trúc dữ liệu đã tìm thấy.
"""
import json
import requests
from auth_manager import RikkeiPortalAPI

BASE_URL = "https://lms-admin.rikkei.edu.vn"

# System IDs đã tìm thấy từ /api/systems
SYSTEM_IDS = [
    "6a868c33c6d890523883e335",  # K26-QTKDS
    "6a868c22c6d890523883e324",  # K26-CNTT
]

# Student ID mẫu từ /api/students
SAMPLE_STUDENT_ID = "6ab0ee764cf535213d26a981"

# Endpoints nâng cao cần thăm dò
DEEP_ENDPOINTS = [
    # --- Sinh viên ---
    ("GET",  "/api/students",                                        "Danh sách tất cả sinh viên"),
    ("GET",  f"/api/students/{SAMPLE_STUDENT_ID}",                   "Chi tiết một sinh viên"),
    ("GET",  f"/api/students/{SAMPLE_STUDENT_ID}/attendances",       "Điểm danh của sinh viên"),
    ("GET",  f"/api/students/{SAMPLE_STUDENT_ID}/grades",            "Điểm số của sinh viên"),
    ("GET",  f"/api/students/{SAMPLE_STUDENT_ID}/leaves",            "Đơn nghỉ phép của sinh viên"),

    # --- Hệ thống (System) ---
    ("GET",  "/api/systems",                                         "Danh sách hệ thống"),
    ("GET",  f"/api/systems/{SYSTEM_IDS[0]}",                        "Chi tiết hệ thống K26-QTKDS"),
    ("GET",  f"/api/systems/{SYSTEM_IDS[0]}/classes",                "Lớp học của hệ thống K26-QTKDS"),
    ("GET",  f"/api/systems/{SYSTEM_IDS[0]}/students",               "Sinh viên của hệ thống K26-QTKDS"),
    ("GET",  f"/api/systems/{SYSTEM_IDS[1]}/classes",                "Lớp học của hệ thống K26-CNTT"),

    # --- Lớp học (Classes) ---
    ("GET",  "/api/class",                                           "Danh sách lớp học"),
    ("GET",  "/api/class-rooms",                                     "Danh sách phòng học"),
    ("GET",  "/api/class-room",                                      "Danh sách phòng học (alt)"),

    # --- Nhân viên & Phòng ban ---
    ("GET",  "/api/staff/me",                                        "Profile nhân viên (alt)"),
    ("GET",  "/api/staff/profile",                                   "Profile nhân viên"),
    ("GET",  "/api/department",                                      "Phòng ban"),
    ("GET",  "/api/departments",                                     "Phòng ban (plural)"),
    ("GET",  "/api/roles",                                           "Danh sách role/quyền"),

    # --- Điểm danh & Điểm số ---
    ("GET",  "/api/attendance",                                      "Điểm danh (root)"),
    ("GET",  "/api/attendances",                                     "Điểm danh (plural)"),
    ("GET",  "/api/grade",                                           "Điểm số (root)"),

    # --- Thông báo (Notifications) ---
    ("GET",  "/api/staff/notifications",                             "Thông báo nhân viên"),
    ("GET",  "/api/staff/notifications/received",                    "Thông báo đã nhận"),
    ("POST", "/api/staff/notifications",                             "Gửi thông báo"),

    # --- Đơn xin nghỉ phép ---
    ("GET",  "/api/leave",                                           "Đơn nghỉ phép (root)"),
    ("GET",  "/api/leaves",                                          "Đơn nghỉ phép (plural)"),
    ("GET",  "/api/leave-requests",                                  "Yêu cầu nghỉ phép"),

    # --- Môn học & Lịch ---
    ("GET",  "/api/subject",                                         "Môn học"),
    ("GET",  "/api/subjects",                                        "Môn học (plural)"),
    ("GET",  "/api/schedule",                                        "Lịch học"),
    ("GET",  "/api/timetable",                                       "Thời khoá biểu"),

    # --- Bài tập & Kiểm tra ---
    ("GET",  "/api/assignment",                                      "Bài tập"),
    ("GET",  "/api/exam",                                            "Kỳ thi"),
    ("GET",  "/api/quiz",                                            "Bài kiểm tra"),

    # --- Cấu hình ---
    ("GET",  "/api/config",                                          "Cấu hình hệ thống"),
    ("GET",  "/api/settings",                                        "Cài đặt"),
]

def test_endpoint(session, method, path, description):
    url = BASE_URL + path
    try:
        if method == "GET":
            resp = session.get(url, timeout=8, params={"limit": 3, "offset": 0})
        else:
            # Không thực sự gửi POST, chỉ thử OPTIONS
            resp = session.options(url, timeout=8)
        return resp.status_code, resp.text[:300]
    except Exception as e:
        return 0, str(e)

def main():
    print("=" * 80)
    print("  KHÁM PHÁ SÂU API LMS RIKKEI ADMIN")
    print("=" * 80)

    api = RikkeiPortalAPI()
    api._ensure_authenticated()
    token = api.token

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })

    results = []
    active = []

    print(f"\n{'METHOD':<8} {'ENDPOINT':<55} {'STATUS':<8} KẾT QUẢ")
    print("-" * 110)

    for method, path, description in DEEP_ENDPOINTS:
        status, preview = test_endpoint(session, method, path, description)

        if status == 200:
            tag = "✅ CÓ DỮ LIỆU"
            active.append((method, path, description, preview))
        elif status == 401:
            tag = "🔒 CẦN XÁC THỰC"
        elif status == 403:
            tag = "🚫 KHÔNG CÓ QUYỀN"
        elif status == 404:
            tag = "❌ KHÔNG TỒN TẠI"
        elif status == 422:
            tag = "⚡ THIẾU THAM SỐ (422)"
        elif status == 0:
            tag = "⚠️  LỖI KẾT NỐI"
        else:
            tag = f"⚡ HTTP {status}"

        print(f"{method:<8} {path:<55} {str(status):<8} {tag}")
        results.append({
            "method": method,
            "path": path,
            "description": description,
            "status": status,
        })

    # In chi tiết
    print("\n" + "=" * 80)
    print("  TỔNG HỢP CÁC ENDPOINT HOẠT ĐỘNG")
    print("=" * 80)
    for method, path, description, preview in active:
        print(f"\n{'─'*60}")
        print(f"[{method}] {path}")
        print(f"  📌 {description}")
        print(f"  📦 Preview: {preview[:250]}")

    # Lưu kết quả
    with open("api_deep_discovery.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n\n✅ Đã lưu kết quả đầy đủ vào: api_deep_discovery.json")
    print(f"📊 Tổng endpoints thử: {len(results)} | Hoạt động: {len(active)}")

if __name__ == "__main__":
    main()
