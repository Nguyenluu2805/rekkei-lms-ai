import requests

res = requests.post("http://localhost:8000/api/chat/stream", json={"message": "Xem điểm danh của sinh viên Phan Gia Hiển"}, stream=True)
print("Status:", res.status_code)
for line in res.iter_lines():
    if line:
        print(line.decode('utf-8'))
