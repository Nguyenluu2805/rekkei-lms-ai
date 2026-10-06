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

# Search for Phan Gia Hien
code, res = get("/api/students", {"limit": 100})
items = res.get("data", {}).get("items", [])
hien_list = [s for s in items if "Hiển" in s.get("fullName", "") or "Hien" in s.get("fullName", "")]
print("Found students with name Hien:")
for h in hien_list:
    print(f"ID: {h['id']} | Code: {h['studentCode']} | Name: {h['fullName']} | Class: {h.get('className')}")

# Also check /api/staff/students
code2, res2 = get("/api/staff/students", {"limit": 100})
if code2 == 200:
    items2 = res2.get("data", {}).get("items", [])
    hien_list2 = [s for s in items2 if "Hiển" in s.get("fullName", "") or "Hien" in s.get("fullName", "")]
    print("\nFound in /api/staff/students:")
    for h in hien_list2:
        print(f"ID: {h['id']} | Code: {h['studentCode']} | Name: {h['fullName']} | Class: {h.get('className')}")

# Also let's probe all possible attendance/schedule endpoints
test_endpoints = [
    "/api/attendances",
    "/api/attendance",
    "/api/roll-call",
    "/api/rollcall",
    "/api/schedules",
    "/api/schedule",
    "/api/lessons",
    "/api/timetables",
    "/api/staff/attendances",
    "/api/staff/attendance",
    "/api/staff/schedules",
    "/api/staff/schedule",
    "/api/staff/lessons",
    "/api/student-attendances",
    "/api/student-schedules",
    "/api/reports/attendance",
    "/api/reports/student-attendance",
]

print("\n--- Probing attendance / schedule root endpoints ---")
for ep in test_endpoints:
    st, data = get(ep)
    print(f"{ep:<40} -> Status: {st}")
    if st in [200, 400, 422]:
        print("   Body:", str(data)[:200])
