import time
import requests
import json

url_non_stream = "http://localhost:8000/api/chat"
url_stream = "http://localhost:8000/api/chat/stream"

prompt = "giúp tôi liệt kê các bạn sinh viên lớp HCM-KS26-CNTT1 nghỉ không phép quá 2 ngày ở môn nhập môn công nghệ thông tin"

print("="*60)
print("1. ĐO LƯỜNG VỚI STREAMING SSE (/api/chat/stream)")
print("="*60)

t0 = time.time()
ttfb = None
first_token_time = None
total_tokens = 0

with requests.post(url_stream, json={"message": prompt, "session_id": "bench_stream"}, stream=True, timeout=120) as r:
    ttfb = time.time() - t0
    for line in r.iter_lines():
        if line:
            decoded = line.decode('utf-8', errors='ignore')
            if decoded.startswith("data: "):
                payload = json.loads(decoded[6:])
                p_type = payload.get("type")
                if p_type == "chunk":
                    if first_token_time is None:
                        first_token_time = time.time() - t0
                    total_tokens += len(payload.get("data", ""))

total_stream_time = time.time() - t0

print(f" • Thời gian kết nối ban đầu (TTFB): {ttfb:.2f}s")
print(f" • Thời gian đến ký tự phản hồi đầu tiên: {first_token_time:.2f}s")
print(f" • Tổng thời gian stream hoàn tất: {total_stream_time:.2f}s")
print(f" • Tổng số ký tự nhận được: {total_tokens}")

print("\n" + "="*60)
print("2. ĐO LƯỜNG VỚI NON-STREAMING (/api/chat)")
print("="*60)

t1 = time.time()
res = requests.post(url_non_stream, json={"message": prompt, "session_id": "bench_non_stream"}, timeout=120)
total_non_stream_time = time.time() - t1
print(f" • Tổng thời gian xử lý trọn gói: {total_non_stream_time:.2f}s")

with open("benchmark_result.json", "w", encoding="utf-8") as f:
    json.dump({
        "first_token_time": round(first_token_time, 2) if first_token_time else None,
        "total_stream_time": round(total_stream_time, 2),
        "total_non_stream_time": round(total_non_stream_time, 2)
    }, f)
