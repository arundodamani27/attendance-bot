import os
import psycopg2
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Get tokens/DB from Railway environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # Railway gives this when you add PostgreSQL

# Connect to DB
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# Setup table
def setup_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            username TEXT,
            date DATE,
            status TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Save attendance
def save_attendance(username, date, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (username, date, status) VALUES (%s, %s, %s)",
        (username, date, status)
    )
    conn.commit()
    cur.close()
    conn.close()

# Get user attendance
def get_user_attendance(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT date, status FROM attendance WHERE username=%s ORDER BY date DESC", (username,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# Get all attendance
def get_all_attendance():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, date, status FROM attendance ORDER BY date DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# Make date buttons
def get_date_buttons():
    today = datetime.now().date()
    buttons = []
    for i in range(5):  # last 5 days
        day = today - timedelta(days=i)
        buttons.append([InlineKeyboardButton(day.strftime("%Y-%m-%d"), callback_data=f"date:{day}")])
    return buttons

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = get_date_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📅 Choose a date to mark attendance:", reply_markup=reply_markup)

# Handle buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    if data.startswith("date:"):
        date = data.split(":")[1]
        context.user_data["selected_date"] = date

        keyboard = [
            [InlineKeyboardButton("✅ Present", callback_data="present")],
            [InlineKeyboardButton("❌ Absent", callback_data="absent")],
            [InlineKeyboardButton("📌 My Status", callback_data="status")],
            [InlineKeyboardButton("📋 Show All", callback_data="show")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"📅 Date selected: {date}\n\nMark attendance:", reply_markup=reply_markup)

    elif data in ["present", "absent"]:
        date = context.user_data.get("selected_date")
        if not date:
            await query.edit_message_text("⚠️ Select a date first using /start")
            return

        status = "Present ✅" if data == "present" else "Absent ❌"
        save_attendance(user.username, date, status)
        await query.edit_message_text(f"{user.first_name}, your attendance on {date} is marked as {status}")

    elif data == "status":
        records = get_user_attendance(user.username)
        if records:
            text = f"📌 {user.first_name}, your attendance:\n"
            for d, s in records:
                text += f"{d} → {s}\n"
        else:
            text = "❓ You have no records yet."
        await query.edit_message_text(text)

    elif data == "show":
        records = get_all_attendance()
        if records:
            text = "📋 Attendance Records:\n"
            for u, d, s in records:
                text += f"@{u} | {d} → {s}\n"
        else:
            text = "❓ No attendance records yet."
        await query.edit_message_text(text)

def main():
    setup_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
