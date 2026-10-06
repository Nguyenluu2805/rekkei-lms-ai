import json
import requests
from auth_manager import RikkeiPortalAPI

api = RikkeiPortalAPI()
api._ensure_authenticated()
s = requests.Session()
s.headers.update({'Authorization': f'Bearer {api.token}'})

class_id = '6aac91736fde2b6e692ed4f8'
# URL: https://lms-admin.rikkei.edu.vn/api/homework/completion/session/6aae2d7f051be35c19c09b49?classId=6aac91736fde2b6e692ed4f8
r = s.get(f'https://lms-admin.rikkei.edu.vn/api/homework/completion/session/6aae2d7f051be35c19c09b49?classId={class_id}')
data = r.json().get('data', [])

print(f"Tổng số sinh viên trong session 6aae2d7f: {len(data)}")
submitted = [x for x in data if x.get('status') == 'SUBMITTED' or x.get('submittedAt') or x.get('githubUrl')]
print(f"Số lượng đã nộp: {len(submitted)}")

for x in submitted:
    stu = x.get('student', {})
    print(f"  • {stu.get('studentCode')} - {stu.get('fullName')}: aiScore={x.get('aiScore')}, status={x.get('status')}")

# Kiểm tra bài tập chi tiết của session này
r_detail = s.get('https://lms-admin.rikkei.edu.vn/api/homework/session/6aae2d7f051be35c19c09b49')
print("\nChi tiết đề bài:", r_detail.status_code)
if r_detail.status_code == 200:
    d = r_detail.json().get('data', {})
    print("Tên buổi:", d.get('name') or d.get('title'))
    print("Bài tập:", [hw.get('title') or hw.get('name') for hw in d.get('homeworks', [])])
