
import os
import telebot
from telebot import types
from threading import Thread
import time
import json
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))

bot = telebot.TeleBot(TOKEN)
DATA_FILE = "players.json"

# --- Утилиты для хранения данных ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def register_user(user_id, nickname):
    data = load_data()
    for entry in data:
        if entry["id"] == user_id:
            entry["nickname"] = nickname
            entry["status"] = "in"
            save_data(data)
            return
    data.append({
        "id": user_id,
        "nickname": nickname,
        "joined": datetime.utcnow().strftime("%Y-%m-%d"),
        "status": "in"
    })
    save_data(data)

def set_status(user_id, status):
    data = load_data()
    for entry in data:
        if entry["id"] == user_id:
            entry["status"] = status
            break
    save_data(data)

# --- Данные по кораблям ---
ships_by_class = {
    "быстроходный": ["Стрела", "Молния"],
    "боевые": ["Гроза", "Вихрь"],
    "торговые": ["Каравелла", "Галеон"],
    "мортирные": ["Ураган", "Песчаник"],
    "тяжёлые": ["Цитадель", "Бастион"],
    "имперские": ["Император", "Титан"]
}

ship_builds = {
    "Стрела": ["Агрессор", "Разведчик"],
    "Император": ["Штурм", "Оборона"]
}

build_details = {
    "Агрессор": "Быстрая атака с лёгкой бронёй.",
    "Разведчик": "Скорость и уклонение.",
    "Штурм": "Пробивной урон, высокая защита.",
    "Оборона": "Максимальный урон и броня."
}

# --- Обработчики ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Привет! Какой у вас игровой ник в SEA Battles?")
    bot.register_next_step_handler(message, get_nickname)

def get_nickname(message):
    register_user(message.chat.id, message.text)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cls in ships_by_class:
        markup.add(cls)
    if message.chat.id == ADMIN_ID:
        markup.add("📣 Рассылка")
        markup.add("👥 Игроки")
    bot.send_message(message.chat.id, "Выбери класс кораблей:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ships_by_class)
def handle_class(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for ship in ships_by_class[message.text]:
        markup.add(ship)
    markup.add("⬅ Назад")
    bot.send_message(message.chat.id, f"Корабли класса {message.text}:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ship_builds)
def handle_ship(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for build in ship_builds[message.text]:
        markup.add(build)
    markup.add("⬅ Назад")
    bot.send_message(message.chat.id, f"Сборки для корабля {message.text}:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in build_details)
def handle_build(message):
    bot.send_message(message.chat.id, build_details[message.text])

@bot.message_handler(func=lambda msg: msg.text == "📣 Рассылка")
def ask_broadcast(message):
    if message.chat.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "Введите сообщение для рассылки:")
        bot.register_next_step_handler(msg, broadcast)

def broadcast(message):
    data = load_data()
    sent = 0
    for entry in data:
        if entry["status"] == "in":
            try:
                member = bot.get_chat_member(GROUP_ID, entry["id"])
                if member.status in ["member", "administrator", "creator"]:
                    bot.send_message(entry["id"], message.text)
                    sent += 1
            except:
                continue
    bot.send_message(ADMIN_ID, f"Отправлено {sent} сообщений.")

@bot.message_handler(func=lambda msg: msg.text == "👥 Игроки")
def show_players(message):
    if message.chat.id != ADMIN_ID:
        return
    data = load_data()
    active = [f"- {u['nickname']} ({u['id']}), с {u['joined']}" for u in data if u["status"] == "in"]
    left = [f"- {u['nickname']} ({u['id']}), с {u['joined']}" for u in data if u["status"] == "left"]
    msg = "✅ В группе:\n" + ("\n".join(active) or "—") + "\n\n❌ Вышли:\n" + ("\n".join(left) or "—")

@bot.message_handler(func=lambda msg: msg.text == "⬅ Назад")
def go_back(message):
    start(message)

# --- Ежедневная проверка участников группы ---
def check_membership():
    while True:
        try:
            data = load_data()
            for entry in data:
                try:
                    member = bot.get_chat_member(GROUP_ID, entry["id"])
                    if member.status == "left":
                        set_status(entry["id"], "left")
                except:
                    continue
        except:
            pass
        time.sleep(86400)

Thread(target=check_membership, daemon=True).start()

bot.polling()
