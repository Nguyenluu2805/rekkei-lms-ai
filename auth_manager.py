import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

import json
import time
import base64
import re
import imaplib
import email
import requests
from playwright.sync_api import sync_playwright

import config

def _decode_jwt_exp(token):
    """Giải mã Base64 phần payload của JWT để đọc timestamp exp."""
    try:
        # JWT has 3 parts: header.payload.signature
        payload_b64 = token.split('.')[1]
        # Pad base64
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
        return payload.get('exp', 0)
    except Exception as e:
        print(f"Lỗi giải mã JWT: {e}")
        return 0

def get_valid_token():
    """Kiểm tra token từ biến môi trường hoặc cache, nếu còn hạn > 15 phút thì trả về token."""
    # 1. Ưu tiên biến môi trường LMS_TOKEN / RIKKEI_TOKEN (tiện lợi cho cloud Render/Railway/Docker)
    env_token = os.getenv("LMS_TOKEN") or os.getenv("RIKKEI_TOKEN")
    if env_token:
        exp = _decode_jwt_exp(env_token)
        current_time = int(time.time())
        # Nếu exp = 0 (token không phải JWT chuẩn) hoặc còn hạn > 60s
        if exp == 0 or exp - current_time > 60:
            return env_token

    # 2. Kiểm tra token trong file cache
    if os.path.exists(config.TOKEN_CACHE_FILE):
        try:
            with open(config.TOKEN_CACHE_FILE, 'r') as f:
                data = json.load(f)
                token = data.get('token')
                if token:
                    exp = _decode_jwt_exp(token)
                    current_time = int(time.time())
                    # Nếu còn hạn trên 15 phút (900 giây)
                    if exp - current_time > 900:
                        print("Sử dụng token từ cache.")
                        return token
        except Exception as e:
            print(f"Lỗi đọc token cache: {e}")
    return None

def save_token(token):
    """Lưu token vào cache."""
    os.makedirs(os.path.dirname(config.TOKEN_CACHE_FILE), exist_ok=True)
    with open(config.TOKEN_CACHE_FILE, 'w') as f:
        json.dump({'token': token, 'saved_at': int(time.time())}, f)

def get_latest_mail_id(mail):
    """Lấy ID của bức thư mới nhất trong hộp thư đến."""
    try:
        status, messages = mail.select("INBOX")
        if status == "OK":
            status, data = mail.search(None, "ALL")
            if status == "OK":
                mail_ids = data[0].split()
                if mail_ids:
                    return int(mail_ids[-1])
    except Exception as e:
        print(f"Lỗi lấy ID mail mới nhất: {e}")
    return 0

def get_otp_from_email(since_id):
    """Polling định kỳ mỗi 3 giây trong tối đa 75 giây để tìm thư mới gửi đến sau since_id."""
    print("Đang kết nối IMAP để lấy OTP...")
    try:
        mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
        mail.login(config.EMAIL_USER, config.EMAIL_APP_PASSWORD)
        
        max_retries = 25 # 25 * 3 = 75 giây
        for i in range(max_retries):
            print(f"Đang chờ email chứa OTP... (lần {i+1})")
            mail.select("INBOX")
            status, data = mail.search(None, "ALL")
            if status == "OK":
                mail_ids = data[0].split()
                if mail_ids:
                    latest_id = int(mail_ids[-1])
                    if latest_id > since_id:
                        # Có mail mới
                        status, msg_data = mail.fetch(str(latest_id), "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                # Lấy nội dung
                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        content_type = part.get_content_type()
                                        if content_type == "text/plain" or content_type == "text/html":
                                            body += part.get_payload(decode=True).decode(errors='ignore')
                                else:
                                    body = msg.get_payload(decode=True).decode(errors='ignore')
                                
                                # Tìm mã OTP 6 số
                                match = re.search(r'\b\d{6}\b', body)
                                if match:
                                    mail.logout()
                                    return match.group(0)
                        
                        # Cập nhật since_id nếu có mail mới nhưng không phải mail OTP (để không đọc lại)
                        since_id = latest_id
            
            time.sleep(3)
            
        mail.logout()
    except Exception as e:
        print(f"Lỗi đọc email: {e}")
    return None

def login_and_fetch_token():
    """Khởi chạy Trình duyệt giả lập Playwright để đăng nhập và lấy token."""
    print("Khởi chạy Playwright...")
    with sync_playwright() as p:
        # Sử dụng persistent context
        # Tự động bật headless nếu chạy trên Linux/Render hoặc biến môi trường HEADLESS=true
        is_headless = os.getenv("RENDER") is not None or sys.platform != "win32" or os.getenv("HEADLESS", "false").lower() == "true"
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.BROWSER_PROFILE_DIR,
            headless=is_headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        captured_token = None

        def on_response(response):
            nonlocal captured_token
            # Lắng nghe các API
            try:
                if response.request.resource_type in ["fetch", "xhr"] and response.status == 200:
                    body = response.json()
                    # Log body để debug cấu trúc API trả về
                    print(f"[Network] {response.url} -> {str(body)[:300]}...")
                    if 'token' in body:
                        captured_token = body['token']
                    elif 'data' in body and 'token' in body['data']:
                        captured_token = body['data']['token']
                    elif 'accessToken' in body:
                        captured_token = body['accessToken']
                    elif 'data' in body and 'accessToken' in body['data']:
                        captured_token = body['data']['accessToken']
            except Exception:
                pass

        page.on("response", on_response)

        try:
            print("Đang truy cập trang đăng nhập...")
            page.goto(config.LOGIN_URL)
            page.wait_for_timeout(3000)
            
            # Kiểm tra xem có bị chuyển hướng vào trong hệ thống luôn không (đã đăng nhập)
            if "login" not in page.url:
                print("Đã đăng nhập sẵn từ phiên bản trước!")
                needs_login = False
            else:
                needs_login = True
                # Đợi form load
                try:
                    page.wait_for_selector("input[type='password']", timeout=5000)
                except:
                    pass
                
            if needs_login:
                # 1. Điền tài khoản mật khẩu
                inputs = page.query_selector_all("input")
                email_input = None
                pass_input = None
                for inp in inputs:
                    input_type = inp.get_attribute("type")
                    if input_type in ["email", "text"] and not email_input:
                        email_input = inp
                    elif input_type == "password" and not pass_input:
                        pass_input = inp
                        
                if email_input and pass_input:
                    email_input.fill(config.RIKKEI_USERNAME)
                    pass_input.fill(config.RIKKEI_PASSWORD)
                elif len(inputs) >= 2:
                    inputs[0].fill(config.RIKKEI_USERNAME)
                    inputs[1].fill(config.RIKKEI_PASSWORD)
                
                # 2. Xử lý reCAPTCHA
                print("Đang chờ reCAPTCHA...")
                try:
                    recaptcha_frame = page.frame_locator('iframe[title="reCAPTCHA"]')
                    recaptcha_frame.locator('#recaptcha-anchor').click(timeout=10000)
                    
                    print("Đang chờ xác nhận reCAPTCHA (tối đa 45s)...")
                    # Vòng lặp kiểm tra Captcha Token
                    token_found = False
                    for _ in range(45):
                        try:
                            is_checked = recaptcha_frame.locator('#recaptcha-anchor').get_attribute('aria-checked')
                            if is_checked == "true":
                                print("[Browser] ✅ reCAPTCHA đã xác thực thành công (Green Tick)!")
                                token_found = True
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)
                    
                    if not token_found:
                        print("Không lấy được token reCAPTCHA kịp thời, tiếp tục submit thử...")
                        
                except Exception as e:
                    print(f"Lỗi khi xử lý reCAPTCHA: {e}, tiếp tục...")
    
                # Kết nối IMAP lấy mail_id mới nhất trước khi click Đăng nhập
                mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
                mail.login(config.EMAIL_USER, config.EMAIL_APP_PASSWORD)
                latest_id = get_latest_mail_id(mail)
                mail.logout()
    
                # 3. Bấm nút đăng nhập
                page.click("button[type='submit']", force=True)
                
                # 4. Lấy OTP từ email
                otp = get_otp_from_email(latest_id)
                if otp:
                    print(f"Đã lấy được OTP: {otp}")
                    # Điền OTP (Xử lý cả trường hợp 1 ô và 6 ô)
                    page.wait_for_selector("input", timeout=10000)
                    otp_inputs = page.query_selector_all("input[type='text'], input[type='number']")
                    
                    # Bỏ qua các input bị ẩn hoặc không dùng để nhập OTP
                    visible_inputs = [inp for inp in otp_inputs if inp.is_visible()]
                    
                    if len(visible_inputs) >= 6:
                        print("Phát hiện 6 ô nhập OTP, đang điền từng số...")
                        for i in range(6):
                            visible_inputs[i].fill(otp[i])
                    elif len(visible_inputs) > 0:
                        print("Phát hiện 1 ô nhập OTP, đang điền...")
                        visible_inputs[-1].fill(otp) # Điền vào ô input cuối cùng hiển thị trên màn hình
                    
                    # Bấm xác nhận
                    submit_buttons = page.query_selector_all("button[type='submit']")
                    if submit_buttons:
                        submit_buttons[-1].click(force=True)
                    
                    # Chờ cho đến khi request hoàn thành hoặc timeout
                    print("Đang chờ Token trả về...")
                    page.wait_for_timeout(5000)
                else:
                    print("Không lấy được OTP.")

            # Fallback đọc localStorage nếu không bắt được qua network
            if not captured_token:
                try:
                    # In toàn bộ localStorage keys để debug
                    keys = page.evaluate("Object.keys(localStorage)")
                    print(f"Các key có trong localStorage: {keys}")
                    
                    session_keys = page.evaluate("Object.keys(sessionStorage)")
                    print(f"Các key có trong sessionStorage: {session_keys}")
                    
                    cookies = context.cookies()
                    print(f"Các cookie hiện có: {[c['name'] for c in cookies]}")
                    
                    # 1. Tìm trong Cookie trước (vì hệ thống dùng Cookie)
                    for cookie in cookies:
                        if cookie['name'] == 'access_token':
                            val = cookie['value']
                            if val and len(val) > 50:
                                captured_token = val
                                print("Đã tìm thấy token trong Cookie (access_token)!")
                                break
                                
                    # 2. Tìm trong localStorage nếu chưa thấy
                    if not captured_token:
                        for key in keys:
                            if 'token' in key.lower():
                                val = page.evaluate(f"localStorage.getItem('{key}')")
                                # Kiểm tra xem có phải JWT không (dài > 50)
                                if val and len(val) > 50:
                                    captured_token = val
                                    print(f"Đã tìm thấy token trong localStorage với key: {key}")
                                    break
                except:
                    pass

        except Exception as e:
            print(f"Lỗi trong quá trình thao tác trên trình duyệt: {e}")
        finally:
            context.close()

        if captured_token:
            save_token(captured_token)
            return captured_token
            
    return None

class RikkeiPortalAPI:
    def __init__(self):
        self.token = get_valid_token()
        
    def _ensure_authenticated(self, force_refresh=False):
        if force_refresh or not self.token:
            print("Cần làm mới Token, đang chạy luồng đăng nhập...")
            self.token = login_and_fetch_token()
            
        if not self.token:
            raise Exception("Không thể xác thực với LMS.")
            
    def _make_request(self, method, url, **kwargs):
        self._ensure_authenticated()
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.token}"
        kwargs['headers'] = headers
        
        response = requests.request(method, url, **kwargs)
        
        # Cơ chế Auto Recovery
        if response.status_code in [401, 403]:
            print("Token hết hạn hoặc không hợp lệ (401/403). Đang đăng nhập lại...")
            self._ensure_authenticated(force_refresh=True)
            # Thử lại request
            headers['Authorization'] = f"Bearer {self.token}"
            kwargs['headers'] = headers
            response = requests.request(method, url, **kwargs)
            
        return response

    # Ví dụ hàm lấy Profile (Cần thay bằng endpoint thực tế)
    def get_profile(self):
        api_url = "https://lms-admin.rikkei.edu.vn/api/profile"
        res = self._make_request("GET", api_url)
        return res.json()

if __name__ == "__main__":
    print("--- KIỂM THỬ SDK ---")
    api = RikkeiPortalAPI()
    try:
        api._ensure_authenticated()
        print("Đã xác thực thành công! Token của bạn là:")
        print(api.token[:30] + "...(ẩn phần còn lại)")
    except Exception as e:
        print("Lỗi xác thực:", e)
