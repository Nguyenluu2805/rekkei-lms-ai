import os
from dotenv import load_dotenv

# Tải cấu hình từ file .env
load_dotenv()

# Cấu hình LMS
RIKKEI_USERNAME = os.getenv("RIKKEI_USERNAME")
RIKKEI_PASSWORD = os.getenv("RIKKEI_PASSWORD")

# Cấu hình Lark IMAP
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
IMAP_SERVER = "imap.larksuite.com"
IMAP_PORT = 993

# Đường dẫn dữ liệu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUTH_CACHE_DIR = os.path.join(DATA_DIR, "auth_cache")
BROWSER_PROFILE_DIR = os.path.join(DATA_DIR, "browser_profile")
TOKEN_CACHE_FILE = os.path.join(AUTH_CACHE_DIR, "token_cache.json")

# URL Đăng nhập
LOGIN_URL = "https://lms-admin.rikkei.edu.vn/login"

# Cấu hình NoCaptcha AI giải reCAPTCHA
NOCAPTCHA_API_KEY = os.getenv("NOCAPTCHA_API_KEY", "nocap_HOHGrY7iyQXhfAynG8zsIxVl")
NOCAPTCHA_EXT_DIR = os.path.join(DATA_DIR, "nocaptchaai_extension")
