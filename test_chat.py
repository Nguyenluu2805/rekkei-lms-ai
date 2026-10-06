import requests
import json

url = "http://localhost:8000/api/chat"
prompt = "giúp tôi liệt kê các bạn sinh viên lớp HCM-KS26-CNTT1 nghỉ không phép quá 2 ngày ở môn nhập môn công nghệ thông tin"

print("Đang gửi yêu cầu tới Rika Chatbot...")
try:
    res = requests.post(url, json={"message": prompt, "session_id": "test_eval"}, timeout=180)
    print("STATUS CODE:", res.status_code)
    data = res.json()
    print("\n--- TOOL CALLS ĐƯỢC AGENT SỬ DỤNG ---")
    for tc in data.get("tool_calls", []):
        print(f" • {tc.get('name')}: {tc.get('args')}")
    print("\n--- PHẢN HỒI TỪ RIKA CHATBOT ---")
    print(data.get("reply"))
except Exception as e:
    print("LỖI GỌI API:", e)
