import requests
from auth_manager import RikkeiPortalAPI

api = RikkeiPortalAPI()
api._ensure_authenticated()
s = requests.Session()
s.headers.update({'Authorization': f'Bearer {api.token}'})

# Lấy chi tiết môn IT108-K26 (Nhập môn CNTT)
r = s.get('https://lms-admin.rikkei.edu.vn/api/staff/courses/6a88fb77a493e63f11a75432')
cdata = r.json().get('data', {})
print("Môn học:", cdata.get('name'), "| Code:", cdata.get('courseCode'))

sessions = cdata.get('sessions', [])
print(f"Tổng số buổi học trong môn: {len(sessions)}")
for s_item in sessions:
    sid = s_item.get('_id') or s_item.get('id')
    name = s_item.get('name')
    print(f"  • Session ID: {sid} | Tên: {name}")

    # Thử gọi API đề bài tập về nhà của session này
    hw_r = s.get(f'https://lms-admin.rikkei.edu.vn/api/homework/session/{sid}')
    if hw_r.status_code == 200:
        hw_data = hw_r.json().get('data', [])
        print(f"    -> Có {len(hw_data)} bài tập về nhà")
        for hw in hw_data:
            print(f"       + [{hw.get('_id')}] {hw.get('title') or hw.get('name')}")
