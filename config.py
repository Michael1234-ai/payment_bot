import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def get_env(key, required=True, default=None):
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"❌ Missing required environment variable: {key}")
    return value

# =========================
# TELEGRAM CONFIG
# =========================
TELEGRAM_TOKEN = get_env("TELEGRAM_TOKEN")

# =========================
# M-PESA CONFIG
# =========================
MPESA_CONSUMER_KEY = get_env("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = get_env("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = get_env("MPESA_SHORTCODE")
MPESA_PASSKEY = get_env("MPESA_PASSKEY")

# =========================
# CALLBACK CONFIG
# =========================
CALLBACK_URL = get_env("CALLBACK_URL")

# =========================
# ENVIRONMENT SETTINGS
# =========================
ENVIRONMENT = os.getenv("ENVIRONMENT", "sandbox").lower()  # sandbox / production
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# =========================
# M-PESA ENDPOINTS
# =========================
if ENVIRONMENT == "production":
    MPESA_BASE_URL = "https://api.safaricom.co.ke"
else:
    MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"

# =========================
# OPTIONAL SETTINGS
# =========================
APP_NAME = os.getenv("APP_NAME", "Telegram Payment Bot")
CURRENCY = os.getenv("CURRENCY", "KES")

# =========================
# VALIDATION CHECK (RUN ON START)
# =========================
def validate_config():
    print("🔍 Validating configuration...")

    required_vars = [
        TELEGRAM_TOKEN,
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_SHORTCODE,
        MPESA_PASSKEY,
        CALLBACK_URL
    ]

    if not all(required_vars):
        raise Exception("❌ Some required environment variables are missing.")

    print("✅ Configuration loaded successfully!")
    print(f"🌍 Environment: {ENVIRONMENT}")
    print(f"🐞 Debug Mode: {DEBUG}")
    print(f"🔗 Callback URL: {CALLBACK_URL}")
    print(f"💰 Currency: {CURRENCY}")

# Run validation automatically
validate_config()