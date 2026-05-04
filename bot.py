import sqlite3
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import TELEGRAM_TOKEN
from mpesa import stk_push

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# DATABASE
# =========================
conn = sqlite3.connect('database.db', check_same_thread=False, timeout=10)
cursor = conn.cursor()

# =========================
# USER STATES
# =========================
user_state = {}

# =========================
# START COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user = update.message.from_user

    try:
        cursor.execute("""
        INSERT OR IGNORE INTO users (telegram_id, username)
        VALUES (?, ?)
        """, (chat_id, user.username))
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")

    keyboard = [
        [InlineKeyboardButton("💰 Make Payment", callback_data="pay")],
        [InlineKeyboardButton("📜 My Payments", callback_data="history")]
    ]

    await update.message.reply_text(
        "🚀 Welcome to Genesis Payment Bot\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# BUTTON HANDLER
# =========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    if query.data == "pay":
        user_state[chat_id] = "awaiting_amount"
        await query.message.reply_text("💰 Enter amount (KES):")

    elif query.data == "history":
        cursor.execute("""
        SELECT amount, status, created_at
        FROM payments
        WHERE user_id=?
        ORDER BY id DESC LIMIT 5
        """, (chat_id,))
        rows = cursor.fetchall()

        if not rows:
            await query.message.reply_text("📭 No payments found.")
            return

        msg = "📜 Last Payments:\n\n"
        for r in rows:
            msg += f"KES {r[0]} - {r[1]} - {r[2]}\n"

        await query.message.reply_text(msg)

# =========================
# MESSAGE HANDLER
# =========================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    state = user_state.get(chat_id)

    # STEP 1: AMOUNT
    if state == "awaiting_amount":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter a valid number.")
            return

        context.user_data["amount"] = int(text)
        user_state[chat_id] = "awaiting_phone"

        await update.message.reply_text(
            "📱 Enter phone number (format: 2547XXXXXXXX):"
        )

    # STEP 2: PHONE
    elif state == "awaiting_phone":
        phone = text

        if not phone.startswith("254") or len(phone) != 12:
            await update.message.reply_text("❌ Invalid phone format.")
            return

        amount = context.user_data.get("amount")

        await update.message.reply_text("⏳ Sending STK push...")

        response = stk_push(phone, amount)

        if response["success"]:
            checkout_id = response["CheckoutRequestID"]

            try:
                cursor.execute("""
                INSERT INTO payments (user_id, phone, amount, status, checkout_request_id)
                VALUES (?, ?, ?, ?, ?)
                """, (chat_id, phone, amount, "pending", checkout_id))
                conn.commit()

                logging.info(f"💾 Saved payment: {checkout_id}")

            except Exception as e:
                logging.error(f"DB Insert Error: {e}")

            await update.message.reply_text(
                f"📲 STK Push sent to {phone}\n"
                "👉 Check your phone and enter PIN.\n\n"
                "⏳ Waiting for confirmation..."
            )

        else:
            await update.message.reply_text(
                f"❌ Payment failed:\n{response['error']}"
            )

        user_state.pop(chat_id, None)

    else:
        await update.message.reply_text("Use /start to begin.")

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🚀 Bot is running...")
    app.run_polling()

# =========================
# RUN
# =========================
if __name__ == "__main__":
    main()