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

print("=== 1. TEST DIRECT ENDPOINT FROM USER ===")
st, data = get("/api/staff/attendance/sessions/6ab0dd5b4cf535213d22e426/roster")
print(f"Status: {st}")
print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])

print("\n=== 2. PROBE ATTENDANCE ROOT & SESSION ENDPOINTS ===")
endpoints = [
    "/api/staff/attendance",
    "/api/staff/attendance/sessions",
    "/api/staff/attendance/classes",
    "/api/staff/attendance/reports",
    "/api/staff/attendance/students",
    f"/api/staff/attendance/students/6ab08eebd2575492aec03365",
    "/api/staff/classes/6aac91736fde2b6e692ed4f8/attendance",
    "/api/staff/classes/6aac91736fde2b6e692ed4f8/sessions",
    "/api/staff/classes/6aac91736fde2b6e692ed4f8/attendance/sessions",
]

for ep in endpoints:
    s, resp = get(ep)
    print(f"{ep:<65} -> {s}")
    if s in [200, 400, 422]:
        print("   Res:", str(resp)[:300])
