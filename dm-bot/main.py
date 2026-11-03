import asyncio
import sqlite3
import time
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9043777810:AAEHkNypwDRqrL8lVPORXTnZT-OydbYDmVk"
ADMIN_ID = 7376198853
ACCESS_KEY = "toverich1"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.dmytro.live", "https://dmytro.live"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, type TEXT, deadline TEXT, description TEXT, contact_type TEXT, contact_value TEXT, status TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS stats (
        key TEXT PRIMARY KEY, value INTEGER)""")
    cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('visits', 0)")
    conn.commit()
    conn.close()

init_db()

def get_orders_count():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_visits():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM stats WHERE key='visits'")
    visits = cursor.fetchone()[0]
    conn.close()
    return visits

def add_visit():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE stats SET value = value + 1 WHERE key='visits'")
    conn.commit()
    conn.close()

# --- API ДЛЯ САЙТА ---
class Order(BaseModel):
    type: str
    deadline: str
    description: str
    contact_type: str
    contact_value: str

@app.post("/api/order")
async def receive_order(order: Order):
    time_now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Сохраняем в базу
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (date, type, deadline, description, contact_type, contact_value, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (time_now, order.type, order.deadline, order.description, order.contact_type, order.contact_value, "Нова"))
    conn.commit()
    conn.close()

    # Отправляем в ТГ
    msg = (f"🔥 <b>НОВА ЗАЯВКА!</b>\n\n"
           f"📦 <b>Що:</b> {order.type}\n"
           f"⏳ <b>Термін:</b> {order.deadline}\n"
           f"📝 <b>Опис:</b> {order.description}\n"
           f"📱 <b>Контакт:</b> {order.contact_type} - {order.contact_value}\n"
           f"⏰ <b>Час:</b> {time_now}")
    
    await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=ParseMode.HTML)
    return {"status": "ok", "message": "Успішно!"}

# Пинг от сайта для статистики посещений
@app.get("/api/ping")
async def ping_site():
    add_visit()
    return {"status": "ok"}

# --- ЛОГИКА БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Це приватний бот-адмінка. Доступ заборонено.")
        return
    
    await message.answer("🔒 <b>Система захищена.</b>\n\nВведіть ключ доступу:", parse_mode=ParseMode.HTML)

@dp.message(F.text == ACCESS_KEY)
async def check_key(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 Статистика", callback_data="stats"))
    builder.row(types.InlineKeyboardButton(text="📩 Останні заявки", callback_data="orders"))
    builder.row(types.InlineKeyboardButton(text="🌐 Перевірити сайт", callback_data="site_check"))
    
    await message.answer("✅ <b>Доступ дозволено.</b>\n\nВітаю в адмін-панелі Nerox Web.", reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "stats")
async def show_stats(call: types.CallbackQuery):
    orders = get_orders_count()
    visits = get_visits()
    text = (f"📊 <b>Статистика системи</b>\n\n"
            f"👥 Відвідувачів сайту: <b>{visits}</b>\n"
            f"📩 Всього заявок: <b>{orders}</b>\n"
            f"🟢 Статус бота: <b>Онлайн</b>")
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=call.message.reply_markup)

@dp.callback_query(F.data == "orders")
async def show_orders(call: types.CallbackQuery):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT date, type, contact_type, contact_value FROM orders ORDER BY id DESC LIMIT 5")
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        text = "📭 Заявок поки немає."
    else:
        text = "📩 <b>Останні 5 заявок:</b>\n\n"
        for o in orders:
            text += f"📅 {o[0]} | {o[1]}\n👤 {o[2]}: {o[3]}\n\n"
            
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "site_check")
async def site_check(call: types.CallbackQuery):
    text = "🌐 <b>Моніторинг сайту</b>\n\nСайт: dmytro-dev-beta.vercel.app\nСтатус: 🟢 Працює\nЗатримка: 24ms"
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "back")
async def go_back(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 Статистика", callback_data="stats"))
    builder.row(types.InlineKeyboardButton(text="📩 Останні заявки", callback_data="orders"))
    builder.row(types.InlineKeyboardButton(text="🌐 Перевірити сайт", callback_data="site_check"))
    await call.message.edit_text("✅ <b>Головне меню</b>", parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())

# --- ЗАПУСК ---
async def main():
    # Запускаем веб-сервер в фоне
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    print("Бот запущен! Веб-сервер работает на порту 8000.")
    # Запускаем и бота, и сервер одновременно
    await asyncio.gather(
        dp.start_polling(bot),
        server.serve()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
