import requests

res = requests.post(
    "http://localhost:8000/api/chat/stream",
    json={"message": "Kiểm tra sinh viên Phan Gia Hiển đã nộp bài tập về nhà Session 01 (session_id: 6aae2d7f051be35c19c09b49) của lớp HCM-KS26-CNTT1 (class_id: 6aac91736fde2b6e692ed4f8) chưa?"},
    stream=True
)
print("Status:", res.status_code)
for line in res.iter_lines():
    if line:
        print(line.decode('utf-8'))
