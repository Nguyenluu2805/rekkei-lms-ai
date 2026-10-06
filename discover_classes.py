"""
Script thứ 3: Dựa vào dữ liệu thực tế để tìm các endpoint liên quan đến lớp học.
"""
import json
import requests
from auth_manager import RikkeiPortalAPI

BASE_URL = "https://lms-admin.rikkei.edu.vn"

def test(session, method, path, description, params=None):
    url = BASE_URL + path
    try:
        resp = session.request(method, url, timeout=8, params=params or {"limit": 3})
        try:
            body = resp.json()
            preview = str(body)[:400]
        except:
            preview = resp.text[:400]
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
    print("BƯỚC 1: Lấy dữ liệu sinh viên để tìm classId, systemId thực tế")
    print("=" * 70)

    # Lấy danh sách sinh viên
    resp = session.get(BASE_URL + "/api/students", params={"limit": 1})
    students_data = resp.json()
    first_student = students_data["data"]["items"][0]
    student_id = first_student["id"]
    print(f"Sinh viên mẫu: {first_student['fullName']} (ID: {student_id})")
    print(f"Dữ liệu đầy đủ: {json.dumps(first_student, ensure_ascii=False, indent=2)[:1000]}")

    # Lấy chi tiết sinh viên để tìm thêm IDs
    resp2 = session.get(BASE_URL + f"/api/students/{student_id}")
    student_detail = resp2.json().get("data", {})
    print(f"\nChi tiết đầy đủ:\n{json.dumps(student_detail, ensure_ascii=False, indent=2)[:1000]}")

    # Lấy danh sách systems
    resp3 = session.get(BASE_URL + "/api/systems")
    systems = resp3.json().get("data", [])
    system_ids = [s["id"] for s in systems]
    system_codes = [s["systemCode"] for s in systems]
    print(f"\nCác hệ thống: {[s['systemCode'] for s in systems]}")

    print("\n" + "=" * 70)
    print("BƯỚC 2: Thử các endpoint với pattern khác nhau")
    print("=" * 70)

    # Các class IDs nếu có trong student_detail
    class_ids = student_detail.get("classIds", []) or student_detail.get("classes", []) or []
    if class_ids:
        class_id = class_ids[0] if isinstance(class_ids[0], str) else class_ids[0].get("id", "")
    else:
        class_id = ""

    print(f"Class IDs tìm thấy: {class_ids}")

    # Thử các pattern endpoint mới
    test_cases = []

    # Với systemCode
    for code in system_codes[:2]:
        test_cases += [
            ("GET", f"/api/classes?systemCode={code}", f"Classes theo systemCode={code}", None),
            ("GET", f"/api/class?systemCode={code}", f"Class theo systemCode={code}", None),
        ]

    # Với systemId
    for sid in system_ids[:2]:
        test_cases += [
            ("GET", f"/api/classes?systemId={sid}", f"Classes theo systemId", None),
            ("GET", f"/api/students?systemId={sid}", f"Students theo systemId", None),
        ]

    # Thêm các prefix khác
    additional = [
        ("GET", "/api/classes",               "Lớp học"),
        ("GET", "/api/class-groups",           "Nhóm lớp"),
        ("GET", "/api/learning-classes",       "Lớp học (learning)"),
        ("GET", "/api/course-classes",         "Lớp khoá học"),
        ("GET", "/api/staff/classes",          "Lớp của nhân viên"),
        ("GET", "/api/staff/profile/me",       "Profile nhân viên"),
        ("GET", "/api/staff/courses",          "Khoá học của nhân viên"),
        ("GET", "/api/staff/students",         "Sinh viên của nhân viên"),
        ("GET", "/api/student-classes",        "Lớp của sinh viên"),
        ("GET", "/api/classroom",              "Phòng học"),
        ("GET", "/api/classrooms",             "Phòng học (plural)"),
        ("GET", "/api/session",               "Buổi học"),
        ("GET", "/api/sessions",              "Buổi học (plural)"),
        ("GET", "/api/lesson",                "Bài học"),
        ("GET", "/api/lessons",               "Bài học (plural)"),
        ("GET", "/api/absence",               "Vắng mặt"),
        ("GET", "/api/absences",              "Vắng mặt (plural)"),
        ("GET", "/api/score",                 "Điểm"),
        ("GET", "/api/scores",                "Điểm (plural)"),
        ("GET", "/api/rubric",                "Rubric"),
        ("GET", "/api/rubrics",               "Rubric (plural)"),
    ]

    if class_id:
        additional += [
            ("GET", f"/api/classes/{class_id}",            "Chi tiết lớp học"),
            ("GET", f"/api/classes/{class_id}/students",   "Sinh viên trong lớp"),
            ("GET", f"/api/classes/{class_id}/sessions",   "Buổi học của lớp"),
        ]

    test_cases += [(m, p, d, None) for m, p, d in additional]

    results = []
    active = []

    print(f"\n{'METHOD':<6} {'ENDPOINT':<60} {'STATUS':<8} KẾT QUẢ")
    print("-" * 100)

    for method, path, description, params in test_cases:
        # Nếu params đã trong path (query string), không truyền thêm
        if "?" in path:
            url = BASE_URL + path
            try:
                resp = session.get(url, timeout=8)
                status = resp.status_code
                try:
                    preview = str(resp.json())[:300]
                except:
                    preview = resp.text[:300]
            except Exception as e:
                status, preview = 0, str(e)
        else:
            status, preview = test(session, method, path, description, {"limit": 3})

        if status == 200:
            tag = "✅ CÓ DỮ LIỆU"
            active.append((method, path, description, preview))
        elif status == 403:
            tag = "🚫 KHÔNG CÓ QUYỀN"
        elif status == 422:
            tag = "⚡ THIẾU THAM SỐ"
        elif status == 404:
            tag = "❌ KHÔNG TỒN TẠI"
        elif status == 204:
            tag = "📭 TRỐNG (204)"
        elif status == 0:
            tag = "⚠️  LỖI"
        else:
            tag = f"HTTP {status}"

        print(f"{method:<6} {path:<60} {str(status):<8} {tag}")
        results.append({"method": method, "path": path, "description": description, "status": status, "preview": preview})

    print("\n" + "=" * 70)
    print("CÁC ENDPOINT HOẠT ĐỘNG MỚI TÌM THẤY")
    print("=" * 70)
    for method, path, description, preview in active:
        print(f"\n[{method}] {path}")
        print(f"  📌 {description}")
        print(f"  📦 {preview[:400]}")

    with open("api_class_discovery.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Lưu kết quả: api_class_discovery.json | Active: {len(active)}/{len(results)}")

if __name__ == "__main__":
    main()
