import time
import requests

url = "http://localhost:8000/api/chat"

test_cases = [
    {
        "name": "Case 1: THIẾU THÔNG TIN (Không rõ môn / lớp)",
        "message": "xem giúp tôi tình hình điểm danh của bạn Phan Gia Hiển"
    },
    {
        "name": "Case 2: THÔNG TIN KHÔNG CHUẨN XÁC / KHÔNG TỒN TẠI",
        "message": "liệt kê sinh viên nghỉ không phép của lớp HCM-K99-CNTT99 môn Nhập môn lập trình"
    }
]

for tc in test_cases:
    print("="*70)
    print(tc["name"])
    print(f"Câu hỏi: \"{tc['message']}\"")
    print("="*70)
    res = requests.post(url, json={"message": tc["message"], "session_id": f"test_{time.time()}"}, timeout=60)
    data = res.json()
    print("Tools gọi:")
    for t in data.get("tool_calls", []):
        print(f"  -> {t.get('name')}({t.get('args')})")
    print("\nPhản hồi từ Chatbot:")
    print(data.get("reply"))
    print("\n")
