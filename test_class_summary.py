import time
from auth_manager import RikkeiPortalAPI
import requests
from concurrent.futures import ThreadPoolExecutor

api = RikkeiPortalAPI()
api._ensure_authenticated()
s = requests.Session()
s.headers.update({'Authorization': f'Bearer {api.token}'})

class_id = '6aac91736fde2b6e692ed4f8'

t0 = time.time()
# 1. Lấy danh sách sessions của lớp
r_sess = s.get(f'https://lms-admin.rikkei.edu.vn/api/staff/attendance/sessions?classId={class_id}')
sessions = r_sess.json().get('data', [])
print(f"Tổng sessions của lớp: {len(sessions)}")

# 2. Quét song song roster của tất cả sessions bằng ThreadPoolExecutor
def fetch_roster(sess):
    sid = sess['_id']
    meta = sess.get('sessionId', {})
    name = meta.get('name', 'N/A') if isinstance(meta, dict) else str(meta)
    date = (sess.get('date') or '')[:10]
    period = sess.get('period')
    course_id = sess.get('courseId')
    
    r = s.get(f'https://lms-admin.rikkei.edu.vn/api/staff/attendance/sessions/{sid}/roster')
    roster = []
    if r.status_code == 200:
        roster = r.json().get('data', {}).get('roster', [])
    return {
        'session_id': sid,
        'date': date,
        'period': period,
        'lesson': name,
        'course_id': course_id,
        'roster': roster
    }

with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(fetch_roster, sessions))

# 3. Tổng hợp theo từng sinh viên
students_map = {} # studentId -> data

for res in results:
    date = res['date']
    lesson = res['lesson']
    course_id = res['course_id']
    for item in res['roster']:
        stu_id = item.get('studentId')
        code = item.get('studentCode', 'N/A')
        name = item.get('fullName', 'N/A')
        status = item.get('status')
        
        if stu_id not in students_map:
            students_map[stu_id] = {
                'studentCode': code,
                'fullName': name,
                'present_count': 0,
                'excused_count': 0,
                'unexcused_count': 0,
                'unexcused_details': []
            }
            
        if status in ('PRESENT', 'LATE'):
            students_map[stu_id]['present_count'] += 1
        elif status == 'ABSENT_EXCUSED':
            students_map[stu_id]['excused_count'] += 1
        elif status == 'ABSENT_UNEXCUSED':
            students_map[stu_id]['unexcused_count'] += 1
            students_map[stu_id]['unexcused_details'].append({
                'date': date,
                'lesson': lesson,
                'course_id': course_id
            })

all_students = list(students_map.values())
all_students.sort(key=lambda x: -x['unexcused_count'])

t_total = time.time() - t0
print(f"Thời gian quét toàn bộ {len(sessions)} buổi học: {t_total:.2f}s")
print(f"Tổng số sinh viên trong lớp: {len(all_students)}")

over_2 = [st for st in all_students if st['unexcused_count'] > 2]
print(f"\n=> Sinh viên nghỉ không phép > 2 buổi TOÀN LỚP: {len(over_2)} bạn")
for st in over_2:
    print(f"  • {st['studentCode']} - {st['fullName']}: {st['unexcused_count']} buổi không phép (Có mặt: {st['present_count']}, Có phép: {st['excused_count']})")
    for d in st['unexcused_details']:
        print(f"     + [{d['date']}] {d['lesson'][:50]}")
