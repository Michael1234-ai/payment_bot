# mpesa.py
import requests
import base64
import logging
from datetime import datetime, timedelta
from config import *

# =========================
# LOGGING SETUP
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# TOKEN CACHE
# =========================
_access_token = None
_token_expiry = None


# =========================
# GET ACCESS TOKEN
# =========================
def get_access_token():
    global _access_token, _token_expiry

    if _access_token and _token_expiry and datetime.now() < _token_expiry:
        return _access_token

    try:
        url = f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

        response = requests.get(
            url,
            auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET),
            timeout=15
        )

        # 🔥 IMPORTANT: show raw error if it fails
        if response.status_code != 200:
            logging.error(f"❌ Token Error Response: {response.text}")
            raise Exception("Failed to generate access token")

        data = response.json()

        _access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3599))

        _token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

        logging.info("✅ Access token generated successfully")
        return _access_token

    except Exception as e:
        logging.error(f"❌ Token generation failed: {e}")
        raise


# =========================
# GENERATE PASSWORD
# =========================
def generate_password(timestamp):
    data = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(data.encode()).decode()


# =========================
# STK PUSH
# =========================
def stk_push(phone, amount, account_reference="GenesisBot", description="Payment"):
    try:
        access_token = get_access_token()

        url = f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = generate_password(timestamp)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": account_reference,
            "TransactionDesc": description
        }

        logging.info(f"📤 STK Push -> {phone} | Amount: {amount}")

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=20
        )

        # 🔥 DEBUG RAW RESPONSE (VERY IMPORTANT)
        logging.info(f"📥 Raw Response: {response.text}")

        data = response.json()

        # =========================
        # SUCCESS CHECK
        # =========================
        if data.get("ResponseCode") == "0":
            logging.info("✅ STK Push sent successfully")

            return {
                "success": True,
                "CheckoutRequestID": data.get("CheckoutRequestID"),
                "MerchantRequestID": data.get("MerchantRequestID"),
                "message": data.get("CustomerMessage")
            }

        # =========================
        # FAILED REQUEST
        # =========================
        logging.error(f"❌ STK Failed: {data}")

        return {
            "success": False,
            "error": data.get("errorMessage") or data.get("ResponseDescription"),
            "response": data
        }

    except requests.exceptions.Timeout:
        logging.error("⏱️ STK request timeout")
        return {"success": False, "error": "Timeout error"}

    except requests.exceptions.RequestException as e:
        logging.error(f"🌐 Network error: {str(e)}")
        return {"success": False, "error": str(e)}

    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
        return {"success": False, "error": str(e)}