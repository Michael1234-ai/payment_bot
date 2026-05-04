# callback.py
import sqlite3
import requests
import logging
from flask import Flask, request
from config import TELEGRAM_TOKEN

app = Flask(__name__)

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# TELEGRAM MESSAGE SENDER (IMPROVED)
# =========================
def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url, json=payload, timeout=15)

        logging.info(f"📩 Telegram response: {res.status_code} {res.text}")

        if res.status_code != 200:
            logging.error("❌ Telegram failed to send message")

    except Exception as e:
        logging.error(f"🔥 Telegram send error: {e}")


# =========================
# CALLBACK ROUTE
# =========================
@app.route('/callback', methods=['POST'])
def mpesa_callback():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        data = request.get_json(force=True, silent=True)

        logging.info(f"🔥 CALLBACK RECEIVED: {data}")

        stk = data.get('Body', {}).get('stkCallback', {})
        result_code = stk.get('ResultCode')
        checkout_id = stk.get('CheckoutRequestID')

        if not checkout_id:
            logging.warning("⚠ Missing CheckoutRequestID")
            return {"ResultCode": 0, "ResultDesc": "Missing CheckoutRequestID"}

        logging.info(f"🔍 Checkout ID: {checkout_id}")

        # =========================
        # FIND PAYMENT
        # =========================
        cursor.execute("""
            SELECT user_id, amount, phone
            FROM payments
            WHERE checkout_request_id=?
        """, (checkout_id,))

        record = cursor.fetchone()

        if not record:
            logging.error(f"❌ No DB match for CheckoutID: {checkout_id}")
            return {"ResultCode": 0, "ResultDesc": "Not found"}

        user_id, amount, phone = record

        # =========================
        # SUCCESS PAYMENT
        # =========================
        if result_code == 0:

            items = stk.get('CallbackMetadata', {}).get('Item', [])

            receipt = None
            for item in items:
                if item.get("Name") == "MpesaReceiptNumber":
                    receipt = item.get("Value")

            cursor.execute("""
                UPDATE payments
                SET status='success', mpesa_receipt=?
                WHERE checkout_request_id=?
            """, (receipt, checkout_id))

            conn.commit()

            logging.info(f"✅ PAYMENT SUCCESS: {receipt}")

            send_telegram_message(
                user_id,
                "✅ <b>Payment Successful</b>\n\n"
                f"💰 Amount: KES {amount}\n"
                f"📱 Phone: {phone}\n"
                f"🧾 Receipt: {receipt}\n\n"
                "🚀 Thank you!"
            )

        # =========================
        # FAILED PAYMENT
        # =========================
        else:

            cursor.execute("""
                UPDATE payments
                SET status='failed'
                WHERE checkout_request_id=?
            """, (checkout_id,))

            conn.commit()

            logging.warning(f"❌ PAYMENT FAILED: {checkout_id}")

            send_telegram_message(
                user_id,
                "❌ <b>Payment Failed</b>\n\n"
                f"💰 Amount: KES {amount}\n"
                f"📱 Phone: {phone}\n\n"
                "Try again."
            )

    except Exception as e:
        logging.error(f"🔥 Callback crash: {e}")

    finally:
        conn.close()

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    logging.info("🚀 Callback server running on port 5000")
    app.run(host="0.0.0.0", port=5000)