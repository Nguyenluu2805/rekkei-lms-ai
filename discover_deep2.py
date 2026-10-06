"""
Script thứ 4: Khám phá sâu vào staff/classes và staff/courses
"""
import json
import requests
from auth_manager import RikkeiPortalAPI

BASE_URL = "https://lms-admin.rikkei.edu.vn"

def test(session, path, params=None):
    url = BASE_URL + path
    try:
        resp = session.get(url, timeout=8, params=params or {"limit": 3})
        try:
            body = resp.json()
            preview = str(body)[:500]
        except:
            preview = resp.text[:300]
        return resp.status_code, preview
    except Exception as e:
        return 0, str(e)

def main():
    api = RikkeiPortalAPI()
    api._ensure_authenticated()
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api.token}",
        "Content-Type": "application/json",
    })

    print("=" * 70)
    print("BƯỚC 1: Lấy dữ liệu thực tế từ staff/classes và staff/courses")
    print("=" * 70)

    # Lấy danh sách classes
    r = session.get(BASE_URL + "/api/staff/classes", params={"limit": 50})
    classes = r.json()["data"]["items"]
    class_id = classes[0]["id"]
    class_code = classes[0]["classCode"]
    course_ids = classes[0].get("courseIds", [])
    print(f"\nTổng số lớp: {len(classes)}")
    print(f"Tất cả lớp: {[c['classCode'] for c in classes]}")
    print(f"Lớp mẫu: {class_code} (ID: {class_id})")
    print(f"CourseIds trong lớp: {course_ids}")

    # Lấy danh sách courses
    r2 = session.get(BASE_URL + "/api/staff/courses", params={"limit": 50})
    courses = r2.json()["data"]["items"]
    course_id = courses[0]["id"]
    course_code = courses[0]["courseCode"]
    print(f"\nTổng số khoá học: {len(courses)}")
    print(f"Tất cả khoá học: {[c['courseCode'] for c in courses]}")
    print(f"Khoá học mẫu: {course_code} (ID: {course_id})")

    print("\n" + "=" * 70)
    print("BƯỚC 2: Thử sub-endpoints theo ID thực tế")
    print("=" * 70)

    test_cases = [
        # --- Class sub-endpoints ---
        (f"/api/staff/classes/{class_id}",                    "Chi tiết lớp học"),
        (f"/api/staff/classes/{class_id}/students",           "Sinh viên trong lớp"),
        (f"/api/staff/classes/{class_id}/courses",            "Khoá học trong lớp"),
        (f"/api/staff/classes/{class_id}/sessions",           "Buổi học của lớp"),
        (f"/api/staff/classes/{class_id}/attendances",        "Điểm danh của lớp"),
        (f"/api/staff/classes/{class_id}/scores",             "Điểm số của lớp"),
        (f"/api/staff/classes/{class_id}/grades",             "Kết quả học tập"),
        (f"/api/staff/classes/{class_id}/leaves",             "Đơn nghỉ phép"),
        (f"/api/staff/classes/{class_id}/notifications",      "Thông báo lớp"),
        (f"/api/staff/classes/{class_id}/schedule",           "Lịch học"),

        # --- Course sub-endpoints ---
        (f"/api/staff/courses/{course_id}",                   "Chi tiết khoá học"),
        (f"/api/staff/courses/{course_id}/sessions",          "Buổi học của khoá"),
        (f"/api/staff/courses/{course_id}/lessons",           "Bài học"),
        (f"/api/staff/courses/{course_id}/quizzes",           "Bài kiểm tra"),
        (f"/api/staff/courses/{course_id}/assignments",       "Bài tập"),
        (f"/api/staff/courses/{course_id}/students",          "Sinh viên khoá học"),
        (f"/api/staff/courses/{course_id}/attendances",       "Điểm danh khoá học"),

        # --- Root endpoints mới ---
        ("/api/courses",                                       "Tất cả khoá học (root)"),
        (f"/api/courses/{course_id}",                         "Chi tiết khoá học (root)"),
        (f"/api/courses/{course_id}/sessions",                "Sessions khoá học (root)"),
        ("/api/specialize",                                    "Chuyên ngành"),
        ("/api/specializes",                                   "Chuyên ngành (plural)"),
        ("/api/locations",                                     "Địa điểm"),
        ("/api/location",                                      "Địa điểm (singular)"),
        ("/api/staff/schedule",                                "Lịch của nhân viên"),
        ("/api/staff/leaves",                                  "Nghỉ phép nhân viên"),
        ("/api/staff/absences",                                "Vắng mặt nhân viên"),
    ]

    results = []
    active = []

    print(f"\n{'ENDPOINT':<65} {'STATUS':<8} KẾT QUẢ")
    print("-" * 110)

    for path, description in test_cases:
        status, preview = test(session, path)

        if status == 200:
            tag = "✅ CÓ DỮ LIỆU"
            active.append((path, description, preview))
        elif status == 403:
            tag = "🚫 KHÔNG CÓ QUYỀN"
        elif status == 422:
            tag = "⚡ THIẾU THAM SỐ"
        elif status == 404:
            tag = "❌ KHÔNG TỒN TẠI"
        else:
            tag = f"HTTP {status}"

        print(f"{path:<65} {str(status):<8} {tag}")
        results.append({"path": path, "description": description, "status": status, "preview": preview[:300]})

    print("\n" + "=" * 70)
    print("ENDPOINT HOẠT ĐỘNG MỚI")
    print("=" * 70)
    for path, description, preview in active:
        print(f"\n[GET] {path}")
        print(f"  📌 {description}")
        print(f"  📦 {preview[:500]}")

    with open("api_final_discovery.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Lưu: api_final_discovery.json | Active: {len(active)}/{len(results)}")

if __name__ == "__main__":
    main()
