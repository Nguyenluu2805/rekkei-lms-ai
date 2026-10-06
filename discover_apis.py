"""
Script tự động khám phá và liệt kê các API endpoint của LMS Rikkei Admin.
Sử dụng token đã lưu từ auth_manager.py
"""
import json
import requests
from auth_manager import RikkeiPortalAPI, get_valid_token

BASE_URL = "https://lms-admin.rikkei.edu.vn"

# ================================================================
# DANH SÁCH CÁC ENDPOINT ĐÃ QUAN SÁT TỪ NETWORK LOG
# ================================================================
KNOWN_ENDPOINTS = [
    # --- Xác thực & Người dùng ---
    ("GET",  "/api/staff/profile/me",                 "Lấy thông tin profile cá nhân"),
    ("GET",  "/api/staff/notifications/received",     "Lấy thông báo đã nhận"),

    # --- Hệ thống (Systems) ---
    ("GET",  "/api/systems",                          "Danh sách tất cả hệ thống/khoá học"),

    # --- Các endpoint phổ biến cần thăm dò ---
    ("GET",  "/api/classes",                          "Danh sách lớp học"),
    ("GET",  "/api/students",                         "Danh sách sinh viên"),
    ("GET",  "/api/staff",                            "Danh sách nhân viên/giảng viên"),
    ("GET",  "/api/courses",                          "Danh sách khoá học"),
    ("GET",  "/api/assignments",                      "Danh sách bài tập"),
    ("GET",  "/api/attendance",                       "Điểm danh"),
    ("GET",  "/api/grades",                           "Điểm số"),
    ("GET",  "/api/schedules",                        "Lịch học"),
    ("GET",  "/api/reports",                          "Báo cáo"),
    ("GET",  "/api/exams",                            "Kỳ thi"),
    ("GET",  "/api/subjects",                         "Môn học"),
    ("GET",  "/api/departments",                      "Khoa/Bộ phận"),
    ("GET",  "/api/semesters",                        "Học kỳ"),
    ("GET",  "/api/staff/leaves",                     "Đơn nghỉ phép"),
    ("GET",  "/api/staff/leaves/received",            "Đơn nghỉ phép nhận được"),
    ("GET",  "/api/staff/notifications",              "Tất cả thông báo"),

    # --- Swagger / OpenAPI Documentation ---
    ("GET",  "/api/docs",                             "Swagger UI Docs"),
    ("GET",  "/api/swagger",                          "Swagger"),
    ("GET",  "/api/openapi.json",                     "OpenAPI JSON spec"),
    ("GET",  "/api/swagger.json",                     "Swagger JSON spec"),
    ("GET",  "/swagger",                              "Swagger (root)"),
    ("GET",  "/docs",                                 "API Docs (root)"),
]

def test_endpoint(session, method, path, description):
    """Gọi một endpoint và kiểm tra kết quả."""
    url = BASE_URL + path
    try:
        resp = session.request(method, url, timeout=8, params={"limit": 5, "offset": 0})
        status = resp.status_code
        try:
            body = resp.json()
            # Lấy một mẫu nhỏ của response
            body_preview = str(body)[:200]
        except:
            body_preview = resp.text[:200]
        return status, body_preview
    except Exception as e:
        return 0, str(e)

def main():
    print("=" * 70)
    print("  KHÁM PHÁ API LMS RIKKEI ADMIN")
    print("=" * 70)

    # Lấy token
    api = RikkeiPortalAPI()
    api._ensure_authenticated()
    token = api.token

    # Tạo session với Bearer Token
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    results = []
    print(f"\n{'PHƯƠNG THỨC':<8} {'ENDPOINT':<50} {'STATUS':<8} PHÂN LOẠI")
    print("-" * 100)

    for method, path, description in KNOWN_ENDPOINTS:
        status, preview = test_endpoint(session, method, path, description)

        if status == 200:
            tag = "✅ CÓ DỮ LIỆU"
        elif status == 401:
            tag = "🔒 CẦN XÁC THỰC"
        elif status == 403:
            tag = "🚫 KHÔNG CÓ QUYỀN"
        elif status == 404:
            tag = "❌ KHÔNG TỒN TẠI"
        elif status == 0:
            tag = "⚠️  LỖI KẾT NỐI"
        else:
            tag = f"⚡ HTTP {status}"

        print(f"{method:<8} {path:<50} {str(status):<8} {tag}")

        results.append({
            "method": method,
            "path": path,
            "description": description,
            "status": status,
            "preview": preview
        })

    # In chi tiết các endpoint trả về 200
    print("\n" + "=" * 70)
    print("  CHI TIẾT CÁC ENDPOINT HOẠT ĐỘNG (HTTP 200)")
    print("=" * 70)
    active = [r for r in results if r["status"] == 200]
    if active:
        for r in active:
            print(f"\n[{r['method']}] {r['path']}")
            print(f"  Mô tả  : {r['description']}")
            print(f"  Preview: {r['preview']}")
    else:
        print("Không tìm thấy endpoint nào hoạt động.")

    # Lưu kết quả ra file
    with open("api_discovery_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Đã lưu kết quả vào: api_discovery_results.json")

if __name__ == "__main__":
    main()
