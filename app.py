import telebot
from telebot import types
import sqlite3
import datetime
import schedule
import threading
import time

TOKEN = "7133010913:AAEI7HxeF0UHRt6a_TbmWCgc3rnGJyiyvxs"
OWNER_ID = ["1145036551"]
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect("banned_words.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS banned_words (word TEXT)")


def get_banned_words():
    cursor.execute("SELECT word FROM banned_words")
    return [row[0] for row in cursor.fetchall()]


def add_banned_word(word):
    cursor.execute("INSERT INTO banned_words (word) VALUES (?)", (word,))
    conn.commit()


def remove_banned_word(word):
    cursor.execute("DELETE FROM banned_words WHERE word = ?", (word,))
    conn.commit()


@bot.message_handler(commands=["start"])
def send_welcome(message):
    if str(message.from_user.id) in OWNER_ID:
        markup = types.InlineKeyboardMarkup()
        button_show = types.InlineKeyboardButton(
            "إظهار الرسائل المحذوفة", callback_data="show_deleted"
        )
        button_add = types.InlineKeyboardButton(
            "إضافة كلمة محظورة", callback_data="add_multiple_banned_words"
        )
        button_remove = types.InlineKeyboardButton(
            "حذف كلمة محظورة", callback_data="remove_word"
        )
        button_list = types.InlineKeyboardButton(
            "عرض الكلمات المحظورة", callback_data="list_words"
        )
        button_clear_all = types.InlineKeyboardButton(
            "مسح جميع الكلمات", callback_data="clear_all_banned_words"
        )
        markup.add(button_show)
        markup.add(button_add, button_remove)
        markup.add(button_list, button_clear_all)
        bot.send_message(
            message.chat.id,
            "مرحبًا بك في DevGuardBot! يمكنك هنا إدارة قائمة الكلمات المحظورة:",
            reply_markup=markup,
        )
    else:
        bot.send_message(message.chat.id, "ليس لديك الصلاحية لاستخدام هذه الأوامر.")


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    if call.data == "show_deleted":
        show_deleted_messages(chat_id)
    elif call.data == "add_multiple_banned_words":
        msg = bot.send_message(chat_id, "أرسل الكلمات التي تريد إضافتها مفصولة بفاصلة:")
        bot.register_next_step_handler(msg, command_add_multiple_banned_words)
    elif call.data == "remove_word":
        msg = bot.send_message(chat_id, "أرسل الكلمة التي تريد حذفها:")
        bot.register_next_step_handler(msg, remove_word)
    elif call.data == "list_words":
        list_banned_words(chat_id)
    elif call.data == "clear_all_banned_words":
        clear_all_banned_words(chat_id)


def command_add_multiple_banned_words(message):
    if str(message.from_user.id) in OWNER_ID:
        words_to_add = message.text.split(",")
        if words_to_add:
            added_words = []
            for word in words_to_add:
                word = word.strip().lower()
                if word and word not in get_banned_words():
                    add_banned_word(word)
                    added_words.append(word)
            if added_words:
                bot.reply_to(
                    message,
                    f"تم إضافة الكلمات {', '.join(added_words)} إلى قائمة الكلمات المحظورة.",
                )
            else:
                bot.reply_to(
                    message,
                    "جميع الكلمات المرسلة موجودة بالفعل في القائمة أو لم تقم بإرسال كلمات صحيحة.",
                )
        else:
            bot.reply_to(
                message,
                "يرجى تحديد الكلمات التي تريد إضافتها مفصولة بفاصلة. مثال: /add_multiple_banned_words كلمة1, كلمة2, كلمة3",
            )
    else:
        bot.reply_to(message, "ليس لديك الصلاحية لإضافة كلمات محظورة.")


def clear_all_banned_words(chat_id):
    if str(chat_id) in OWNER_ID:
        cursor.execute("DELETE FROM banned_words")
        conn.commit()
        bot.send_message(chat_id, "تم مسح جميع الكلمات المحظورة بنجاح.")
    else:
        bot.send_message(chat_id, "ليس لديك الصلاحية لمسح الكلمات المحظورة.")


def remove_word(message):
    if str(message.from_user.id) in OWNER_ID:
        word_to_remove = message.text.strip()
        if word_to_remove.lower() in get_banned_words():
            remove_banned_word(word_to_remove.lower())
            bot.reply_to(
                message, f"تم حذف الكلمة '{word_to_remove}' من قائمة الكلمات المحظورة."
            )
        else:
            bot.reply_to(message, f"الكلمة '{word_to_remove}' غير موجودة في القائمة.")
    else:
        bot.send_message(message.chat.id, "ليس لديك الصلاحية لاستخدام هذه الأوامر.")


def list_banned_words(chat_id):
    banned_words = get_banned_words()
    if banned_words:
        # ترتيب الكلمات ألفبائيًا
        banned_words.sort()
        # تقسيم الكلمات إلى صفحات
        words_per_page = 10
        pages = [
            banned_words[i : i + words_per_page]
            for i in range(0, len(banned_words), words_per_page)
        ]
        # إنشاء نص الرسالة باستخدام جدول
        message_text = "كلمات محظورة:\n\n"
        for page_num, page in enumerate(pages, start=1):
            message_text += (
                f"الصفحة {page_num}:\n"
                + "\n".join(f"- {word}" for word in page)
                + "\n\n"
            )
        bot.send_message(chat_id, message_text)
    else:
        bot.send_message(chat_id, "لا توجد كلمات محظورة حالياً.")


def show_deleted_messages(chat_id):
    file_name = f"deleted_messages_log.txt"
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            deleted_messages = file.read()
        bot.send_message(chat_id, "رسائل محذوفة:\n" + deleted_messages)
    except FileNotFoundError:
        bot.send_message(chat_id, "لا توجد رسائل محذوفة حالياً.")


@bot.message_handler(content_types=["document", "audio", "photo", "video"])
def handle_media_messages(message):
    banned_words = get_banned_words()
    caption = message.caption if message.caption else ""
    found_words = [word for word in banned_words if word in caption.lower()]

    if found_words:
        try:
            bot.delete_message(message.chat.id, message.message_id)
            found_words_str = ", ".join(found_words)
            user_mention = (
                f"@{message.from_user.username}"
                if message.from_user.username
                else "مستخدم"
            )
            notification_msg = f"تم حذف رسالة تحتوي على الكلمات المحظورة ({found_words_str}) من {user_mention}."
            bot.send_message(message.chat.id, notification_msg)
            # تسجيل تفاصيل الرسالة المحذوفة
            log_deleted_message_details(message, found_words_str)
        except Exception as e:
            print(f"Error deleting media message: {e}")


def log_deleted_message_details(message, found_words_str):
    log_filename = "deleted_messages_log.txt"
    with open(log_filename, "a", encoding="utf-8") as file:
        file.write(f"الرسالة: {message.text if message.text else message.caption}\n")
        file.write(f"الكلمات المحظورة: {found_words_str}\n")
        file.write(f"المستخدم: (@{message.from_user.username})\n")
        file.write(f"ايدي: {message.from_user.id}\n")
        file.write(
            f"تاريخ الحذف: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        file.write("------------------------------------------------\n")


def log_deleted_message_details(message, found_words_str):
    log_filename = "deleted_messages_log.txt"
    with open(log_filename, "a", encoding="utf-8") as file:
        file.write(f"الرسالة: {message.text}\n")
        file.write(f"الكلمات المحظورة: {found_words_str}\n")
        file.write(f"المستخدم: (@{message.from_user.username})\n")
        file.write(f"ايدي: {message.from_user.id}\n")
        file.write(
            f"تاريخ الحذف: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        file.write("------------------------------------------------\n")


@bot.message_handler(func=lambda message: message.chat.type in ["group", "supergroup"])
def filter_messages(message):
    if str(message.from_user.id) in OWNER_ID:
        banned_words = get_banned_words()
        # البحث عن الكلمة المحظورة في الرسالة
        found_words = [word for word in banned_words if word in message.text.lower()]
        if found_words:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                # تخزين الكلمات المحظورة الموجودة في الرسالة
                found_words_str = ", ".join(found_words)
                notification_msg = (
                    f"تم حذف رسالة تحتوي على الكلمات المحظورة ({found_words_str}) من @{message.from_user.username}"
                    if message.from_user.username
                    else f"تم حذف رسالة تحتوي على الكلمات المحظورة ({found_words_str}) من مستخدم."
                )
                bot.send_message(message.chat.id, notification_msg)
                # تسجيل تفاصيل الرسالة المحذوفة
                log_deleted_message_details(message, found_words_str)
            except Exception as e:
                print(f"Error deleting message: {e}")


def send_daily_deleted_messages_report(chat_id):
    log_filename = "deleted_messages_log.txt"
    try:
        with open(log_filename, "r", encoding="utf-8") as file:
            deleted_messages = file.read()
        report_message = (
            f"تقرير الرسائل المحذوفة للـ 24 ساعة الماضية:\n\n{deleted_messages}"
        )
        bot.send_message(chat_id, report_message)
    except FileNotFoundError:
        bot.send_message(chat_id, "لا توجد رسائل محذوفة للإبلاغ عنها.")


# جدولة إرسال التقرير اليومي في الساعة 00:00
schedule.every().day.at("00:00").do(
    send_daily_deleted_messages_report, chat_id=OWNER_ID[0]
)


# دالة لتشغيل الجدولة في خيط منفصل
def run_scheduled_tasks():
    while True:
        schedule.run_pending()
        time.sleep(1)


# بدء الجدولة في خيط منفصل
threading.Thread(target=run_scheduled_tasks).start()


bot.polling()
