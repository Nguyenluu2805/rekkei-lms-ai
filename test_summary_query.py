import requests

url = 'http://localhost:8000/api/chat'
msg = 'Sinh viên vắng không phép > 2 buổi lớp HCM-KS26-CNTT1'

res = requests.post(url, json={'message': msg, 'session_id': 'test_summary_fixed'}, timeout=60)
data = res.json()

print('TOOLS ĐƯỢC GỌI:')
for tc in data.get('tool_calls', []):
    print(f" • {tc.get('name')}: {tc.get('args')}")

print('\nPHẢN HỒI:')
print(data.get('reply'))
