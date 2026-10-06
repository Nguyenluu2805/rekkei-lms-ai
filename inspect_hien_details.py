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

hien_id = "6ab08eebd2575492aec03365"

print("--- STUDENT DETAIL ---")
st, detail = get(f"/api/students/{hien_id}")
print(json.dumps(detail, ensure_ascii=False, indent=2))

print("\n--- FIND CLASS HCM-KS26-CNTT1 ---")
st, classes = get("/api/staff/classes", {"limit": 100})
items = classes.get("data", {}).get("items", [])
hien_cls = [c for c in items if c.get("classCode") == "HCM-KS26-CNTT1" or c.get("name") == "HCM-KS26-CNTT1"]
if hien_cls:
    cls_obj = hien_cls[0]
    print(json.dumps(cls_obj, ensure_ascii=False, indent=2))
    
    # Try endpoints on this class & courseIds
    cid = cls_obj["id"]
    course_ids = cls_obj.get("courseIds", [])
    
    print("\n--- CLASS DETAIL ---")
    st, cdetail = get(f"/api/staff/classes/{cid}")
    print(json.dumps(cdetail, ensure_ascii=False, indent=2))
    
    print("\n--- COURSES IN CLASS ---")
    for cr_id in course_ids:
        st, crdetail = get(f"/api/staff/courses/{cr_id}")
        print(f"Course {cr_id}: {st}")
        print(json.dumps(crdetail, ensure_ascii=False, indent=2)[:500])
