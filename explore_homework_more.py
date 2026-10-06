import json
import requests
from auth_manager import RikkeiPortalAPI

BASE_URL = "https://lms-admin.rikkei.edu.vn"

api = RikkeiPortalAPI()
api._ensure_authenticated()
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {api.token}"})

def get(path, params=None):
    r = session.get(BASE_URL + path, params=params or {}, timeout=10)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text[:300]

sess_id = "6aae2d7f051be35c19c09b49" # Session 01 - Học tập chủ động
cls_id = "6aac91736fde2b6e692ed4f8"  # Class HCM-KS26-CNTT1
hien_id = "6ab08eebd2575492aec03365" # Phan Gia Hiển

print("=== 1. HOMEWORK INFO FOR SESSION ===")
st_hw, hw_info = get(f"/api/homework/session/{sess_id}")
print(f"Status: {st_hw}")
print(json.dumps(hw_info, ensure_ascii=False, indent=2))

print("\n=== 2. ALL SUBMISSIONS FOR SESSION & CLASS ===")
st_comp, comp_info = get(f"/api/homework/completion/session/{sess_id}", {"classId": cls_id})
print(f"Status: {st_comp}")
submissions = comp_info.get("data", [])
print(f"Total submissions returned: {len(submissions)}")

hien_sub = [s for s in submissions if s.get("studentId") == hien_id or "Hiển" in s.get("student", {}).get("fullName", "")]

print("\n=== 3. PHAN GIA HIỂN HOMEWORK SUBMISSION ===")
if hien_sub:
    print(json.dumps(hien_sub[0], ensure_ascii=False, indent=2))
else:
    print("Sinh viên Phan Gia Hiển chưa nộp bài tập về nhà buổi này!")
    # Show stats of who submitted
    completed = [s for s in submissions if s.get("status") == "COMPLETED"]
    print(f"Thống kê lớp: {len(completed)}/{len(submissions)} sinh viên đã nộp.")
    for s in submissions[:5]:
        st_obj = s.get("student", {})
        print(f"  • {st_obj.get('studentCode')} - {st_obj.get('fullName')}: {s.get('status')} | Link: {s.get('githubUrl')}")
