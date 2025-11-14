import telebot
import sqlite3
from datetime import date, timedelta
from datetime import datetime

TOKEN = '8546652004:AAHMjptAlVN6dmMZiaPdzzJ3h8VIEdayOwc'
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('WorkoutsDataBase.sql')
    cur = conn.cursor()


    cur.execute('''
                CREATE TABLE IF NOT EXISTS Workouts
                (
                    workout_id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    workout_date
                    TEXT,
                    workout_type
                    TEXT
                )
                ''')

    conn.commit()
    cur.close()
    conn.close()

    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("Вчера", callback_data="add_yesterday")
    btn2 = telebot.types.InlineKeyboardButton("Другая дата", callback_data="add_other_date")
    markup.row(btn1, btn2)
    bot.send_message(message.chat.id, '👋 Что качал сегодня?', reply_markup=markup)

@bot.message_handler(commands=['workouts'])
def workouts_info(message):
    import locale
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

    conn = sqlite3.connect('WorkoutsDataBase.sql')
    cur = conn.cursor()

    cur.execute('SELECT * FROM Workouts ORDER BY workout_date ASC')
    workouts = cur.fetchall()

    if not workouts:
        info = 'Пока нет записей тренировок.'
    else:
        info = ''
        for el in workouts:
            date_str = el[1]  # например '2025-11-11'
            workout_type = el[2]

            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day = date_obj.strftime("%d.%m")
            weekday = date_obj.strftime("%a")

            days = {'Mon': 'Пн', 'Tue': 'Вт', 'Wed': 'Ср', 'Thu': 'Чт', 'Fri': 'Пт', 'Sat': 'Сб', 'Sun': 'Вс'}

            weekday_ru = days.get(weekday, weekday)
            info += f"{day} - ({weekday_ru}) {workout_type}\n"

    cur.close()
    conn.close()
    bot.send_message(message.chat.id, info)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == 'add_workout':
        # Если выбрана запись тренировки — спрашиваем, что делал
        bot.send_message(call.message.chat.id, 'Что делал сегодня?🏋️‍♂️')
        bot.register_next_step_handler(call.message, log_workout)

    elif call.data == 'add_yesterday':
        save_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        bot.send_message(call.message.chat.id, "Что делал вчера?")
        bot.register_next_step_handler(call.message, lambda msg: log_workout_on_date(msg, save_date))

    elif call.data == 'add_other_date':
        bot.send_message(call.message.chat.id, "Введи дату в формате ГГГГ-ММ-ДД (например 2025-02-13)")
        bot.register_next_step_handler(call.message, ask_custom_date)

    elif call.data == 'workouts':
        import locale
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

        conn = sqlite3.connect('WorkoutsDataBase.sql')
        cur = conn.cursor()

        cur.execute('SELECT * FROM Workouts ORDER BY workout_date ASC')
        workouts = cur.fetchall()

        if not workouts:
            info = 'Пока нет записей тренировок.'
        else:
            info = ''
            for el in workouts:
                date_str = el[1]  # например '2025-11-11'
                workout_type = el[2]

                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                day = date_obj.strftime("%d.%m")
                weekday = date_obj.strftime("%a")

                days = {'Mon': 'Пн', 'Tue': 'Вт', 'Wed': 'Ср', 'Thu': 'Чт','Fri': 'Пт', 'Sat': 'Сб', 'Sun': 'Вс' }

                weekday_ru = days.get(weekday, weekday)
                info += f"{day} - ({weekday_ru}) {workout_type}\n"

        cur.close()
        conn.close()
        bot.send_message(call.message.chat.id, info)

def ask_custom_date(message):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        save_date = message.text
        bot.send_message(message.chat.id, f"Что делал {save_date}?")
        bot.register_next_step_handler(message, lambda msg: log_workout_on_date(msg, save_date))
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат. Попробуй снова: ГГГГ-ММ-ДД")
        bot.register_next_step_handler(message, ask_custom_date)

def log_workout_on_date(message, workout_date):
    conn = sqlite3.connect('WorkoutsDataBase.sql')
    cur = conn.cursor()

    workout_type = message.text

    cur.execute('SELECT * FROM Workouts WHERE workout_date = ?', (workout_date,))
    existing = cur.fetchone()

    if existing:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton('Список тренировок', callback_data='workouts'))
        bot.send_message(
            message.chat.id,
            f'На дату {workout_date} уже есть запись ❗',
            reply_markup=markup
        )
    else:
        cur.execute(
            'INSERT INTO Workouts (workout_date, workout_type) VALUES (?, ?)',
            (workout_date, workout_type)
        )
        conn.commit()

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton('Список тренировок', callback_data='workouts'))
        bot.send_message(
            message.chat.id,
            f"Записал: {workout_type} ({workout_date}) ✅",
            reply_markup=markup
        )

    cur.close()
    conn.close()

@bot.message_handler(func=lambda message: True)
def log_workout(message):
    conn = sqlite3.connect('WorkoutsDataBase.sql')
    cur = conn.cursor()

    today = date.today().strftime('%Y-%m-%d')
    workout_type = message.text.capitalize()

    # Проверяем, есть ли уже запись за сегодня
    cur.execute('SELECT * FROM Workouts WHERE workout_date = ?', (today,))
    existing_workout = cur.fetchone()

    if existing_workout:
        # Если запись уже есть — сообщаем пользователю
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton('Список тренировок', callback_data='workouts'))
        bot.send_message(message.chat.id, f'Ты уже записывал тренировку сегодня ({today}) ✅', reply_markup=markup)
    else:
        # Если нет — добавляем новую запись
        cur.execute('INSERT INTO Workouts (workout_date, workout_type) VALUES (?, ?)', (today, workout_type))
        conn.commit()

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton('Список тренировок', callback_data='workouts'))
        bot.send_message(message.chat.id, f"Записал тренировку: {workout_type} ({today}) ✅", reply_markup=markup)

    cur.close()
    conn.close()

bot.polling(none_stop=True)