"""
Kiểm tra chính xác: Sinh viên lớp HCM-KS26-CNTT1
nghỉ không phép > 2 buổi ở môn IT108-K26 (Nhập Môn Công Nghệ Thông Tin)
Status thực: ABSENT_UNEXCUSED=nghỉ không phép, ABSENT_EXCUSED=nghỉ có phép
"""
import json
import requests
from auth_manager import RikkeiPortalAPI

BASE_URL = "https://lms-admin.rikkei.edu.vn"
api = RikkeiPortalAPI()
api._ensure_authenticated()
s = requests.Session()
s.headers.update({"Authorization": f"Bearer {api.token}"})

def get(path, params=None):
    r = s.get(BASE_URL + path, params=params or {}, timeout=10)
    try: return r.status_code, r.json()
    except: return r.status_code, {}

CLASS_ID  = "6aac91736fde2b6e692ed4f8"   # HCM-KS26-CNTT1
COURSE_ID = "6a88fb77a493e63f11a75432"    # IT108-K26

UNAUTHORIZED = {"ABSENT_UNEXCUSED"}
AUTHORIZED   = {"ABSENT_EXCUSED"}
PRESENT      = {"PRESENT", "LATE"}

# 1. Lấy sessions của môn IT108-K26
print("Lay sessions cua IT108-K26 (Nhap Mon CNTT)...")
_, sdata = get("/api/staff/attendance/sessions", {"classId": CLASS_ID})
all_sessions = sdata.get("data", []) if isinstance(sdata.get("data"), list) else []
it_sessions  = [s for s in all_sessions if s.get("courseId") == COURSE_ID]

print(f"Tong session lop: {len(all_sessions)} | Session IT108: {len(it_sessions)}")
for ss in it_sessions:
    si = ss.get("sessionId", {})
    print(f"  [{ss['_id'][:8]}...] {ss.get('date','')[:10]} Ca{ss.get('period')} | {si.get('name','') if isinstance(si,dict) else si}")

if not it_sessions:
    print("Khong co session nao cho IT108-K26!")
    print("Cac courseId hien co trong sessions:")
    cids = set(ss.get("courseId") for ss in all_sessions)
    for cid in cids:
        _, cr = get(f"/api/staff/courses/{cid}")
        print(f"  {cid} => {cr.get('data',{}).get('name')}")
    exit()

# 2. Quét roster từng session
student_data = {}  # {studentId: {code, name, sessions[]}}

for sess_obj in it_sessions:
    sess_id = sess_obj["_id"]
    si = sess_obj.get("sessionId", {})
    lesson = si.get("name", f"Ca {sess_obj.get('period')}") if isinstance(si, dict) else f"Ca {sess_obj.get('period')}"
    date   = sess_obj.get("date", "")[:10]

    _, rdata = get(f"/api/staff/attendance/sessions/{sess_id}/roster")
    roster = rdata.get("data", {}).get("roster", [])

    for item in roster:
        sid    = item.get("studentId")
        status = item.get("status") or "UNKNOWN"
        if sid not in student_data:
            student_data[sid] = {
                "code": item.get("studentCode", ""),
                "name": item.get("fullName", ""),
                "sessions": []
            }
        student_data[sid]["sessions"].append({
            "date": date, "lesson": lesson, "status": status, "note": item.get("note","")
        })

# 3. Thống kê & lọc
print("\n" + "="*60)
print("TONG HOP DIEM DANH - IT108-K26 - HCM-KS26-CNTT1")
print("="*60)

results = []
for sid, info in student_data.items():
    unauthorized = [r for r in info["sessions"] if r["status"] in UNAUTHORIZED]
    authorized   = [r for r in info["sessions"] if r["status"] in AUTHORIZED]
    present      = [r for r in info["sessions"] if r["status"] in PRESENT]
    results.append({
        "code": info["code"], "name": info["name"],
        "present": len(present), "authorized": len(authorized),
        "unauthorized": len(unauthorized), "total": len(info["sessions"]),
        "unauthorized_detail": unauthorized
    })

results.sort(key=lambda x: -x["unauthorized"])

print(f"{'Ma SV':<14} {'Ho ten':<35} {'Co mat':>7} {'Phep':>6} {'K.phep':>7} {'Tong':>6}")
print("-"*75)
for r in results:
    mark = " *** CANH BAO ***" if r["unauthorized"] > 2 else ""
    print(f"{r['code']:<14} {r['name'][:34]:<35} {r['present']:>7} {r['authorized']:>6} {r['unauthorized']:>7} {r['total']:>6}{mark}")

print("\n" + "="*60)
flagged = [r for r in results if r["unauthorized"] > 2]
if not flagged:
    # Kiểm tra xem data có thực sự đầy đủ không
    none_count = sum(1 for info in student_data.values()
                     for r in info["sessions"] if r["status"] == "UNKNOWN")
    max_absent = max((r["unauthorized"] for r in results), default=0)
    print(f"Khong co sinh vien nghi khong phep > 2 buoi.")
    print(f"  - Max nghi khong phep: {max_absent} buoi")
    print(f"  - So ban ghi status UNKNOWN: {none_count}")
    print(f"  - Tong buoi IT108 da scan: {len(it_sessions)}")
    print(f"  - Co the cac buoi chua diem danh (status=None)")
else:
    print(f"CO {len(flagged)} SINH VIEN NGHI KHONG PHEP > 2 BUOI:")
    for r in flagged:
        print(f"\n  {r['code']} - {r['name']}: {r['unauthorized']} buoi")
        for d in r["unauthorized_detail"]:
            print(f"    [{d['date']}] {d['status']} | {d['lesson'][:60]}")
