import json
import requests
from auth_manager import RikkeiPortalAPI

api = RikkeiPortalAPI()
api._ensure_authenticated()
s = requests.Session()
s.headers.update({'Authorization': f'Bearer {api.token}'})

class_id = '6aac91736fde2b6e692ed4f8'
att_id = '6abefd63b2bf6b5877dc8d36'

r = s.get(f'https://lms-admin.rikkei.edu.vn/api/homework/completion/session/{att_id}?classId={class_id}')
data = r.json().get('data', [])

print(f"TỔNG SỐ HỌC VIÊN TRẢ VỀ TỪ API: {len(data)}")

statuses = {}
for item in data:
    st = str(item.get('status'))
    statuses[st] = statuses.get(st, 0) + 1
print("\nThống kê status:")
print(statuses)

submitted = []
unsubmitted = []

for item in data:
    st = item.get('status')
    student = item.get('student', {})
    code = student.get('studentCode', 'N/A')
    name = student.get('fullName', 'N/A')
    submitted_at = item.get('submittedAt')
    github = item.get('githubUrl')
    score = item.get('aiScore') or item.get('score')

    record = {
        "code": code,
        "name": name,
        "status": st,
        "submittedAt": submitted_at,
        "github": bool(github),
        "score": score
    }

    if st in ['SUBMITTED', 'GRADED', 'COMPLETED'] or submitted_at or github:
        submitted.append(record)
    else:
        unsubmitted.append(record)

print(f"\n=> Thực tế đã nộp: {len(submitted)} học viên")
print(f"=> Thực tế chưa nộp: {len(unsubmitted)} học viên")

print("\n--- DANH SÁCH ĐÃ NỘP (5 bạn đầu) ---")
for s in submitted[:5]:
    print(f"  • {s['code']} - {s['name']}: {s['status']} | Điểm: {s['score']}")

print(f"\n--- DANH SÁCH CHƯA NỘP ({len(unsubmitted)} bạn) ---")
for u in unsubmitted:
    print(f"  • {u['code']} - {u['name']} (status={u['status']})")
