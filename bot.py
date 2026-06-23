import logging
import os
from datetime import datetime, date, timedelta
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
DATA_FILE = "events.json"

# Conversation states
ASK_NAME, ASK_DATE, ASK_TYPE, ASK_NOTE, ASK_REPEAT = range(5)

TYPES = {
    "🎂 День рождения": "birthday",
    "🏢 Годовщина заведения": "anniversary",
    "🎉 Праздник": "holiday",
    "🍽️ HoReCa событие": "horeca",
    "⚽ Спорт / Ивент": "sport",
}

TYPE_LABELS = {v: k for k, v in TYPES.items()}

PRESET_EVENTS = [
    {"id": "p1", "name": "Новый год", "date": "01-01", "type": "holiday", "note": "Новогоднее меню, декор", "repeat": True},
    {"id": "p2", "name": "Рамадан 2026", "date": "2026-02-18", "type": "holiday", "note": "Ифтар-меню, спецусловия", "repeat": False},
    {"id": "p3", "name": "Курбан Байрам", "date": "05-27", "type": "holiday", "note": "Праздничное меню, акции", "repeat": True},
    {"id": "p4", "name": "FIFA World Cup 2026 — старт", "date": "2026-06-11", "type": "sport", "note": "FIFA COLLECTION меню, трансляции", "repeat": False},
    {"id": "p5", "name": "FIFA World Cup 2026 — финал", "date": "2026-07-19", "type": "sport", "note": "Финальная вечеринка", "repeat": False},
    {"id": "p6", "name": "Формула 1 Абу-Даби", "date": "11-29", "type": "sport", "note": "F1-тематика, спецпредложения", "repeat": True},
    {"id": "p7", "name": "День всех влюблённых", "date": "02-14", "type": "holiday", "note": "Романтическое меню, декор", "repeat": True},
    {"id": "p8", "name": "Хэллоуин", "date": "10-31", "type": "holiday", "note": "Тематический декор и меню", "repeat": True},
    {"id": "p9", "name": "Национальный день ОАЭ", "date": "12-02", "type": "holiday", "note": "Оформление в духе ОАЭ", "repeat": True},
    {"id": "p10", "name": "День кальяна (14 апр)", "date": "04-14", "type": "horeca", "note": "Акции, новые миксы, соцсети", "repeat": True},
    {"id": "p11", "name": "Dubai Food Festival", "date": "02-26", "type": "horeca", "note": "Участие, специальное меню", "repeat": True},
    {"id": "p12", "name": "Мировой день шеф-повара", "date": "10-20", "type": "horeca", "note": "Контент для соцсетей", "repeat": True},
    {"id": "p13", "name": "Рамадан Карим (конец)", "date": "03-20", "type": "holiday", "note": "Итоговые акции месяца", "repeat": True},
    {"id": "p14", "name": "Международный женский день", "date": "03-08", "type": "holiday", "note": "Спецменю, подарки гостьям", "repeat": True},
]

def load_events():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_events(events):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def get_all_events():
    return PRESET_EVENTS + load_events()

def days_until(date_str, repeat):
    today = date.today()
    try:
        if len(date_str) == 5:  # MM-DD
            month, day = int(date_str[:2]), int(date_str[3:])
            d = date(today.year, month, day)
            if d < today:
                d = date(today.year + 1, month, day)
        elif repeat:
            parts = date_str.split("-")
            month, day = int(parts[1]), int(parts[2])
            d = date(today.year, month, day)
            if d < today:
                d = date(today.year + 1, month, day)
        else:
            parts = date_str.split("-")
            d = date(int(parts[0]), int(parts[1]), int(parts[2]))
        return (d - today).days
    except:
        return 999

def format_date_display(date_str, repeat):
    months = ["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
    try:
        if len(date_str) == 5:
            month, day = int(date_str[:2]), int(date_str[3:])
            return f"{day} {months[month-1]} (ежегодно)"
        parts = date_str.split("-")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        if repeat:
            return f"{day} {months[month-1]} (ежегодно)"
        return f"{day} {months[month-1]} {year}"
    except:
        return date_str

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📅 Ближайшие события", "➕ Добавить дату"],
        ["📋 Все даты", "🔔 Что через 30 дней"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Привет, Парвиз!\n\n"
        "Я твой личный помощник по важным датам для заведений Black Ji.\n\n"
        "Уже загружены все ключевые события:\n"
        "FIFA, Курбан Байрам, Формула 1, Dubai Food Festival и другие.\n\n"
        "Выбери действие 👇",
        reply_markup=reply_markup
    )

async def show_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = get_all_events()
    upcoming = []
    for ev in events:
        d = days_until(ev["date"], ev.get("repeat", True))
        if 0 <= d <= 60:
            upcoming.append((d, ev))
    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        await update.message.reply_text("✅ В ближайшие 60 дней событий нет. Можно расслабиться!")
        return

    text = "📅 *Ближайшие 60 дней:*\n\n"
    for days, ev in upcoming:
        icon = TYPE_LABELS.get(ev["type"], "📌").split()[0]
        if days == 0:
            when = "🔴 *СЕГОДНЯ*"
        elif days == 1:
            when = "🔴 *ЗАВТРА*"
        elif days <= 7:
            when = f"🔴 через {days} дн."
        elif days <= 30:
            when = f"🟡 через {days} дн."
        else:
            when = f"🟢 через {days} дн."
        text += f"{when} — *{ev['name']}*\n"
        text += f"   📆 {format_date_display(ev['date'], ev.get('repeat', True))}\n"
        if ev.get("note"):
            text += f"   💡 {ev['note']}\n"
        text += "\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def show_30days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = get_all_events()
    upcoming = []
    for ev in events:
        d = days_until(ev["date"], ev.get("repeat", True))
        if 0 <= d <= 30:
            upcoming.append((d, ev))
    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        await update.message.reply_text("✅ В ближайшие 30 дней ничего срочного нет.")
        return

    text = "🔔 *Срочно — до 30 дней:*\n\n"
    for days, ev in upcoming:
        if days == 0:
            when = "🔴 СЕГОДНЯ"
        elif days == 1:
            when = "🔴 ЗАВТРА"
        else:
            when = f"🔴 через {days} дн."
        text += f"{when} — *{ev['name']}*\n"
        if ev.get("note"):
            text += f"   💡 {ev['note']}\n"
        text += "\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = get_all_events()
    with_days = [(days_until(ev["date"], ev.get("repeat", True)), ev) for ev in events]
    with_days.sort(key=lambda x: x[0])

    text = "📋 *Все даты:*\n\n"
    for days, ev in with_days:
        icon = TYPE_LABELS.get(ev["type"], "📌").split()[0]
        text += f"{icon} *{ev['name']}*\n"
        text += f"   📆 {format_date_display(ev['date'], ev.get('repeat', True))} | через {days} дн.\n"
        if ev.get("note"):
            text += f"   💡 {ev['note']}\n"
        text += "\n"
        if len(text) > 3500:
            await update.message.reply_text(text, parse_mode="Markdown")
            text = ""

    if text:
        await update.message.reply_text(text, parse_mode="Markdown")

# --- ADD EVENT CONVERSATION ---
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "➕ *Добавляем новую дату*\n\nНапиши название события:\n_(например: День рождения Ахмед, Годовщина Black Ji Abu Dhabi)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)
    )
    return ASK_NAME

async def ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    context.user_data["new_name"] = update.message.text
    await update.message.reply_text(
        "📆 Введи дату в формате:\n"
        "• `15.07` — для ежегодных событий\n"
        "• `15.07.2026` — для разового события",
        parse_mode="Markdown"
    )
    return ASK_DATE

async def ask_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    raw = update.message.text.strip()
    try:
        if raw.count(".") == 1:
            parts = raw.split(".")
            day, month = int(parts[0]), int(parts[1])
            date_str = f"{month:02d}-{day:02d}"
            context.user_data["new_repeat"] = True
        elif raw.count(".") == 2:
            parts = raw.split(".")
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            date_str = f"{year}-{month:02d}-{day:02d}"
            context.user_data["new_repeat"] = False
        else:
            raise ValueError
        context.user_data["new_date"] = date_str
    except:
        await update.message.reply_text("❌ Неверный формат. Попробуй ещё раз: `15.07` или `15.07.2026`", parse_mode="Markdown")
        return ASK_DATE

    keyboard = [[k] for k in TYPES.keys()]
    keyboard.append(["❌ Отмена"])
    await update.message.reply_text(
        "Выбери тип события:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ASK_TYPE

async def ask_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    type_key = TYPES.get(update.message.text)
    if not type_key:
        await update.message.reply_text("Выбери тип из списка 👇")
        return ASK_TYPE
    context.user_data["new_type"] = type_key
    await update.message.reply_text(
        "💡 Добавь заметку (что подготовить, что сделать заранее):\n_или напиши_ *пропустить*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["пропустить"], ["❌ Отмена"]], resize_keyboard=True)
    )
    return ASK_NOTE

async def save_new_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    note = "" if update.message.text.lower() == "пропустить" else update.message.text
    events = load_events()
    new_ev = {
        "id": f"u{int(datetime.now().timestamp())}",
        "name": context.user_data["new_name"],
        "date": context.user_data["new_date"],
        "type": context.user_data["new_type"],
        "note": note,
        "repeat": context.user_data.get("new_repeat", True),
    }
    events.append(new_ev)
    save_events(events)

    days = days_until(new_ev["date"], new_ev["repeat"])
    icon = TYPE_LABELS.get(new_ev["type"], "📌").split()[0]

    keyboard = [
        ["📅 Ближайшие события", "➕ Добавить дату"],
        ["📋 Все даты", "🔔 Что через 30 дней"],
    ]
    await update.message.reply_text(
        f"✅ *Сохранено!*\n\n"
        f"{icon} *{new_ev['name']}*\n"
        f"📆 {format_date_display(new_ev['date'], new_ev['repeat'])}\n"
        f"⏳ Через {days} дней\n"
        + (f"💡 {note}\n" if note else ""),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📅 Ближайшие события", "➕ Добавить дату"],
        ["📋 Все даты", "🔔 Что через 30 дней"],
    ]
    await update.message.reply_text(
        "Отменено.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

async def daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    events = get_all_events()
    reminders = []
    for ev in events:
        d = days_until(ev["date"], ev.get("repeat", True))
        if d in [30, 14, 7, 1, 0]:
            reminders.append((d, ev))
    if not reminders:
        return
    text = "🔔 *Напоминание на сегодня:*\n\n"
    for days, ev in sorted(reminders, key=lambda x: x[0]):
        if days == 0:
            when = "🔴 СЕГОДНЯ"
        elif days == 1:
            when = "🔴 ЗАВТРА"
        else:
            when = f"🟡 Через {days} дней"
        text += f"{when} — *{ev['name']}*\n"
        if ev.get("note"):
            text += f"💡 {ev['note']}\n"
        text += "\n"
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

async def setup_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.job_queue.run_daily(
        daily_reminder,
        time=datetime.strptime("09:00", "%H:%M").time(),
        data=chat_id,
        name=str(chat_id)
    )
    await update.message.reply_text("✅ Ежедневные напоминания включены! Буду писать тебе в 9:00 если что-то срочное.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📅 Ближайшие события":
        await show_upcoming(update, context)
    elif text == "🔔 Что через 30 дней":
        await show_30days(update, context)
    elif text == "📋 Все даты":
        await show_all(update, context)
    else:
        await update.message.reply_text("Используй кнопки меню 👇")

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ Добавить дату$"), add_start),
            CommandHandler("add", add_start),
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date)],
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_type)],
            ASK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_note)],
            ASK_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_event)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upcoming", show_upcoming))
    app.add_handler(CommandHandler("all", show_all))
    app.add_handler(CommandHandler("remind", setup_reminders))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
