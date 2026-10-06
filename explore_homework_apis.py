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

print("=== 1. TEST USER HOMEWORK COMPLETION ENDPOINT ===")
sess_id = "6aae2d7f051be35c19c09b49"
cls_id = "6aac91736fde2b6e692ed4f8"

ep1 = f"/api/homework/completion/session/{sess_id}"
st1, res1 = get(ep1, {"classId": cls_id})
print(f"GET {ep1}?classId={cls_id} -> Status: {st1}")
print(json.dumps(res1, ensure_ascii=False, indent=2)[:1500])

print("\n=== 2. PROBE OTHER HOMEWORK PATTERNS ===")
test_eps = [
    "/api/homework",
    "/api/homeworks",
    "/api/homework/sessions",
    f"/api/homework/session/{sess_id}",
    f"/api/homework/class/{cls_id}",
    "/api/staff/homework",
    "/api/staff/homeworks",
    f"/api/staff/homework/completion/session/{sess_id}",
    "/api/assignments",
    "/api/staff/assignments"
]

for ep in test_eps:
    s, data = get(ep, {"classId": cls_id})
    print(f"{ep:<55} -> {s}")
    if s in [200, 400, 422]:
        print("   Body:", str(data)[:300])
