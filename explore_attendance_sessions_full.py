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

hien_id = "6ab08eebd2575492aec03365" # Phan Gia Hiển
hien_class_id = "6aac91736fde2b6e692ed4f8" # HCM-KS26-CNTT1

print("=== 1. LIST ALL ATTENDANCE SESSIONS FOR HIEN'S CLASS ===")
st, data = get("/api/staff/attendance/sessions", {"classId": hien_class_id})
print(f"Status with classId param: {st}")
sessions_list = data.get("data", []) if isinstance(data.get("data"), list) else []
print(f"Total sessions found: {len(sessions_list)}")

if not sessions_list:
    st, data = get("/api/staff/attendance/sessions", {"limit": 100})
    sessions_list = data.get("data", []) if isinstance(data.get("data"), list) else []
    print(f"Total sessions without filter: {len(sessions_list)}")

print("\n--- SESSIONS LIST PREVIEW ---")
for s in sessions_list:
    print(f"Session ID: {s.get('_id')} | ClassId: {s.get('classId')} | CourseId: {s.get('courseId')} | Date: {s.get('date')} | Period: {s.get('period')}")
    if isinstance(s.get("sessionId"), dict):
        print(f"   Name: {s['sessionId'].get('name')} | Type: {s['sessionId'].get('type')}")

print("\n=== 2. CHECK ROSTERS FOR SESSIONS OF CLASS HCM-KS26-CNTT1 ===")
hien_class_sessions = [s for s in sessions_list if s.get("classId") == hien_class_id]
print(f"Found {len(hien_class_sessions)} sessions specifically for HCM-KS26-CNTT1")

hien_attendance_records = []

for sess in hien_class_sessions:
    sess_id = sess["_id"]
    st_r, roster_data = get(f"/api/staff/attendance/sessions/{sess_id}/roster")
    if st_r == 200:
        r_info = roster_data.get("data", {})
        session_info = r_info.get("session", {})
        roster = r_info.get("roster", [])
        
        # Look for Phan Gia Hiển in roster
        for student in roster:
            if student.get("studentId") == hien_id or "Hiển" in student.get("fullName", ""):
                hien_attendance_records.append({
                    "session_id": sess_id,
                    "date": session_info.get("date"),
                    "period": session_info.get("period"),
                    "course_id": session_info.get("courseId"),
                    "lesson_name": session_info.get("sessionId", {}).get("name") if isinstance(session_info.get("sessionId"), dict) else "N/A",
                    "status": student.get("status"), # PRESENT, ABSENT, etc.
                    "note": student.get("note"),
                    "fullName": student.get("fullName"),
                    "studentCode": student.get("studentCode")
                })

print("\n=== 3. PHAN GIA HIỂN ATTENDANCE RECORDS ===")
print(json.dumps(hien_attendance_records, ensure_ascii=False, indent=2))
