"""
Tìm endpoint điểm danh cho sinh viên Phan Gia Hiển (RE26444)
"""
import json
import requests
from auth_manager import RikkeiPortalAPI

BASE_URL = "https://lms-admin.rikkei.edu.vn"

api = RikkeiPortalAPI()
api._ensure_authenticated()
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {api.token}"})

def get(path, params=None):
    r = session.get(BASE_URL + path, params=params or {}, timeout=8)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text[:200]

# -----------------------------------------------------------
# Bước 1: Tìm Phan Gia Hiển
# -----------------------------------------------------------
print("=" * 60)
print("BƯỚC 1: Tìm sinh viên Phan Gia Hiển")
print("=" * 60)

_, data = get("/api/students", {"search": "Phan Gia Hiển", "limit": 5})
students = data.get("data", {}).get("items", [])
if not students:
    _, data = get("/api/students", {"search": "Hiển", "limit": 10})
    students = [s for s in data.get("data",{}).get("items",[]) if "Hiển" in s.get("fullName","")]

student = students[0] if students else None
if not student:
    print("Không tìm thấy sinh viên!")
    exit()

sid  = student["id"]
code = student["studentCode"]
name = student["fullName"]
cls  = student.get("className","?")
print(f"ID: {sid}")
print(f"Mã: {code} | Tên: {name} | Lớp: {cls}")
print(f"Chi tiết đầy đủ: {json.dumps(student, ensure_ascii=False, indent=2)}")

# -----------------------------------------------------------
# Bước 2: Lấy chi tiết sinh viên (tìm classId thực tế)
# -----------------------------------------------------------
print("\n" + "=" * 60)
print("BƯỚC 2: Chi tiết sinh viên")
print("=" * 60)
_, detail = get(f"/api/students/{sid}")
student_detail = detail.get("data", {})
print(json.dumps(student_detail, ensure_ascii=False, indent=2))

# -----------------------------------------------------------
# Bước 3: Tìm lớp của sinh viên, sau đó tìm class ID
# -----------------------------------------------------------
print("\n" + "=" * 60)
print("BƯỚC 3: Tìm lớp theo className")
print("=" * 60)

_, classes_data = get("/api/staff/classes", {"limit": 100})
all_classes = classes_data.get("data", {}).get("items", [])
matched = [c for c in all_classes if c.get("classCode") == cls or c.get("name") == cls]
print(f"Lớp khớp: {[c['classCode'] for c in matched]}")
if matched:
    class_id = matched[0]["id"]
    course_ids = matched[0].get("courseIds", [])
    print(f"Class ID: {class_id}")
    print(f"Course IDs: {course_ids}")

# -----------------------------------------------------------
# Bước 4: Thử tất cả pattern endpoint điểm danh
# -----------------------------------------------------------
print("\n" + "=" * 60)
print("BƯỚC 4: Quét endpoint điểm danh")
print("=" * 60)

endpoints_to_try = []

# Pattern với student ID
endpoints_to_try += [
    (f"/api/students/{sid}/attendances",        "Student attendances"),
    (f"/api/students/{sid}/attendance",         "Student attendance"),
    (f"/api/students/{sid}/sessions",           "Student sessions"),
    (f"/api/students/{sid}/scores",             "Student scores"),
    (f"/api/students/{sid}/grades",             "Student grades"),
    (f"/api/students/{sid}/progress",           "Student progress"),
    (f"/api/students/{sid}/courses",            "Student courses"),
    (f"/api/students/{sid}/learning",           "Student learning"),
]

# Pattern với studentCode
endpoints_to_try += [
    (f"/api/attendance?studentCode={code}",     "Attendance by code"),
    (f"/api/attendances?studentId={sid}",       "Attendances by ID"),
    (f"/api/attendance?studentId={sid}",        "Attendance by ID"),
    (f"/api/score?studentId={sid}",             "Score by ID"),
    (f"/api/scores?studentId={sid}",            "Scores by ID"),
    (f"/api/grade?studentId={sid}",             "Grade by ID"),
]

# Pattern theo class
if matched:
    cid = matched[0]["id"]
    endpoints_to_try += [
        (f"/api/staff/classes/{cid}/attendance",        "Class attendance"),
        (f"/api/staff/classes/{cid}/attendances",       "Class attendances"),
        (f"/api/staff/classes/{cid}/scores",            "Class scores"),
        (f"/api/staff/classes/{cid}/students",          "Class students"),
        (f"/api/staff/classes/{cid}/sessions",          "Class sessions"),
        (f"/api/staff/classes/{cid}/grades",            "Class grades"),
    ]
    # Pattern theo từng course
    for cour_id in course_ids[:3]:
        endpoints_to_try += [
            (f"/api/staff/courses/{cour_id}/attendance",      f"Course {cour_id[:8]} attendance"),
            (f"/api/staff/courses/{cour_id}/attendances",     f"Course {cour_id[:8]} attendances"),
            (f"/api/staff/courses/{cour_id}/sessions",        f"Course {cour_id[:8]} sessions"),
            (f"/api/staff/courses/{cour_id}/scores",          f"Course {cour_id[:8]} scores"),
        ]

print(f"\n{'PATH':<65} {'STATUS'} KẾT QUẢ")
print("-" * 100)
found = []
for path, desc in endpoints_to_try:
    status, body = get(path)
    if status == 200:
        tag = "✅ CÓ DỮ LIỆU"
        found.append((path, desc, body))
    elif status == 403:
        tag = "🚫 KHÔNG CÓ QUYỀN"
    elif status == 422:
        tag = "⚡ THIẾU THAM SỐ (422)"
    else:
        tag = f"❌ {status}"
    print(f"{path:<65} {status:<6} {tag}")

print("\n" + "=" * 60)
print("ENDPOINT CÓ DỮ LIỆU:")
print("=" * 60)
for path, desc, body in found:
    print(f"\n[{desc}] {path}")
    print(json.dumps(body, ensure_ascii=False, indent=2)[:800])
