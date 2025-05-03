import os
import json
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


with open("faq.json", "r", encoding="utf-8") as f: #frequently asked questions
    faq = json.load(f)

#database maker
conn = sqlite3.connect("support_bot.db")
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS user_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    department TEXT,
    status TEXT,
    created_at TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS answer_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    rating TEXT,
    timestamp TEXT
)''')

conn.commit()

#find answers
def find_faq_answer(text):
    for item in faq:
        if item["question"].lower() in text.lower():
            return item["answer"]
    return None

#main part
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💬 Часто задаваемые вопросы")],
    [KeyboardButton(text="📩 Связаться со специалистом")]
], resize_keyboard=True)


def rating_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data="rate_good"),
            InlineKeyboardButton(text="👎", callback_data="rate_bad")
        ]
    ])


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    photo = FSInputFile("photo_bot.png")
    await message.answer_photo(photo, caption="Здравствуйте! Я бот поддержки магазина «Продаем всё на свете». Чем могу помочь?", reply_markup=main_kb)

@dp.message(lambda m: m.text == "💬 Часто задаваемые вопросы")
async def show_faq(message: types.Message):
    kb = ReplyKeyboardBuilder()
    for item in faq:  # shows all answers
        kb.button(text=item["question"])
    kb.button(text="🔙 Назад")
    kb.adjust(1)
    await message.answer("Вот популярные вопросы:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(lambda m: m.text == "🔙 Назад")
async def back_to_main(message: types.Message):
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_kb)

@dp.message(lambda m: m.text == "📩 Связаться со специалистом")
async def contact_specialist(message: types.Message):
    await message.answer("Опишите вашу проблему, и мы передадим её специалисту.")

@dp.message()
async def handle_message(message: types.Message):
    answer = find_faq_answer(message.text)
    if answer:
        await message.answer(answer, reply_markup=rating_kb())
    else:
        text = message.text.lower()
        department = "sales" if "товар" in text or "брак" in text else "tech"
        cursor.execute('''
            INSERT INTO user_requests (user_id, username, message, department, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            message.from_user.id,
            message.from_user.username,
            message.text,
            department,
            "new",
            datetime.now().isoformat()
        ))
        conn.commit()
        await message.answer("Ваш запрос передан специалисту. Мы свяжемся с вами в ближайшее время.", reply_markup=rating_kb())


@dp.callback_query(lambda c: c.data in ["rate_good", "rate_bad"])
async def handle_rating(callback: CallbackQuery):
    rating = "good" if callback.data == "rate_good" else "bad"

    cursor.execute('''
        INSERT INTO answer_ratings (user_id, username, rating, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (
        callback.from_user.id,
        callback.from_user.username,
        rating,
        datetime.now().isoformat()
    ))
    conn.commit()

    msg = "Спасибо за вашу оценку! 😊" if rating == "good" else "Жаль, что ответ не помог. Мы улучшимся!"
    await callback.answer(msg, show_alert=True)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
