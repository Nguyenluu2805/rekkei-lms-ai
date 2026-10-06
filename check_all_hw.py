import requests
from auth_manager import RikkeiPortalAPI

api = RikkeiPortalAPI()
api._ensure_authenticated()
s = requests.Session()
s.headers.update({'Authorization': f'Bearer {api.token}'})

class_id = '6aac91736fde2b6e692ed4f8'

sessions = [
    ("6ab9cb69355d17176f25e8af", "Định hướng môn học (27/09)"),
    ("6abc51b36ceddb538d8f80d9", "Session 01: Tổng quan ngành CNTT (29/09)"),
    ("6abefd63b2bf6b5877dc8d36", "Session 02: Kiến trúc Hệ Điều Hành (01/10)"),
    ("6ac2e9f90a04225dcbb77abd", "Session 03: Luyện tập tổng hợp (04/10)")
]

for sid, label in sessions:
    print("="*70)
    print(f"KIỂM TRA: {label} (ID: {sid})")
    
    # 1. Chi tiết đề bài
    r_detail = s.get(f'https://lms-admin.rikkei.edu.vn/api/homework/session/{sid}')
    print(f"  API đề bài status: {r_detail.status_code}")
    if r_detail.status_code == 200:
        hw_list = r_detail.json().get('data', [])
        print(f"  Số lượng bài tập được giao: {len(hw_list)}")
        for hw in hw_list:
            print(f"    * [{hw.get('_id')}] {hw.get('title') or hw.get('name')}")
            
    # 2. Tình hình nộp bài
    r_sub = s.get(f'https://lms-admin.rikkei.edu.vn/api/homework/completion/session/{sid}?classId={class_id}')
    print(f"  API nộp bài status: {r_sub.status_code}")
    if r_sub.status_code == 200:
        sub_list = r_sub.json().get('data', [])
        submitted = [x for x in sub_list if x.get('status') or x.get('submittedAt') or x.get('githubUrl')]
        print(f"  Tổng sinh viên: {len(sub_list)} | Đã nộp: {len(submitted)} | Chưa nộp: {len(sub_list) - len(submitted)}")
