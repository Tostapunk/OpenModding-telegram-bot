#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging, sqlite3, pytz, re
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, \
    InlineQueryHandler, RegexHandler, ConversationHandler
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, \
    InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardHide
from datetime import datetime
from uuid import uuid4

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

"""
### CLASSES
"""
class DBHandler:
    def __init__(self, path):
        self._dbpath = path

    def get_links(self, device_id):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        result = ()
        db_query = cursor.execute("SELECT link,name FROM roms WHERE device_id=?", (device_id,)).fetchall()
        if db_query:
            for query in db_query:
                result += ({"name": query["name"],
                            "link": query["link"],
                            },)
        else:
            result = {"error": "not_found"}
        return result

    def get_privs(self, telegram_id):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = cursor.execute("SELECT privs FROM users WHERE id=?", (telegram_id,)).fetchone()
        if not query:
            result = -2
        else:
            result = query["privs"]
        return result

    def update_user(self, from_user): # Update the user list (db)
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        check = cursor.execute("SELECT id,time_used FROM users WHERE id=?", (from_user.id,)).fetchone()
        used = 0
        if check:
            if check["time_used"]:
                used = check["time_used"]
        query = (from_user.first_name,
                 from_user.last_name,
                 from_user.username,
                 datetime.now(pytz.timezone('Europe/Rome')),
                 used + 1,
                 from_user.id)
        if check:
            cursor.execute("UPDATE users SET name_first=?,name_last=?,username=?,last_use=?,time_used=? WHERE id=?",
                           query)
        else:
            cursor.execute("INSERT INTO users(name_first,name_last,username,last_use,time_used,id) VALUES(?,?,?,?,?,?)",
                           query)
        handle.commit()

    def add_link(self, device_id, link, name):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = (device_id,
                 link,
                 name)
        cursor.execute("INSERT INTO roms(device_id,link,name) VALUES(?,?,?)", query)
        handle.commit()

    def get_device(self, name):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = cursor.execute("SELECT id,name,codename FROM devices WHERE name=?", (name + "_roms",)).fetchone()
        if not query:
            query = cursor.execute("SELECT id,name,codename FROM devices WHERE codename=?", (name,)).fetchone()
            if not query:
                result = {"error": "not_found"}
                return result
        result = {"id": query["id"],
                  "db_name": query["name"][:-6],
                  "name": query["codename"], }
        return result

    def get_all_devices_roms(self):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        result = ()
        query_db = cursor.execute("SELECT id,name,codename FROM devices WHERE name LIKE '%_roms'")
        for query in query_db:
            result += ({"id": query["id"],
                        "db_name": query["name"][:-5],
                        "name": query["codename"], },)
        return result

    def link_search(self, name, dicted=False):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query_db = cursor.execute(
            "SELECT devices.codename,roms.link,roms.name FROM roms JOIN devices ON devices.id=roms.device_id "
            "WHERE roms.name LIKE ?",
            ("%%%s%%" % name,)).fetchall()
        if dicted:
            result = {}
            for query in query_db:
                if query["codename"] not in result:
                    result[query["codename"]] = ()
                result[query["codename"]] += ({"name": query["name"],
                                                    "link": query["link"], },)
        else:
            result = ()
            for query in query_db:
                result += ({"name": query["name"],
                            "link": query["link"],
                            "type": query["codename"], },)
        return (result)

    def feedback_submit(self, user_id, feedback):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query_db = cursor.execute("INSERT INTO feedback(user_id,text) VALUES(?,?)", (user_id, feedback))
        print(query_db, user_id, feedback)
        handle.commit()

    def feedback_get(self, id):
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        feedback = cursor.execute(
            "SELECT users.id,feedback.text,users.name_first,users.name_last,users.username FROM feedback JOIN users "
            "ON feedback.user_id=users.id WHERE feedback.id=?",
            (id,)).fetchone()
        result = {"feedback": feedback["text"],
                  "first_name": feedback["name_first"],
                  "last_name": feedback["name_last"],
                  "username": feedback["username"],
                  "user_id": feedback["id"]}
        return (result)

    def feedback_get_unread(self, all=False): # Set unread feedbacks
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        result = ()
        if all == True:
            query = cursor.execute("SELECT * FROM feedback").fetchall()
        else:
            query = cursor.execute("SELECT * FROM feedback WHERE read=0").fetchall()
        for feedback in query:
            result += ({"id": feedback["id"],
                        "text": feedback["text"]},)
        return (result)

    def feedback_set_read(self, id): # Set read feedbacks
        handle = sqlite3.connect(self._dbpath)
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query = cursor.execute("UPDATE feedback SET read=1 WHERE id=?", (id,))
        print(query)
        handle.commit()

"""
### UTILITY
"""
def group(lst, n):
    result = ()
    temp = ()
    x = 1
    for i, item in enumerate(lst):
        temp += (item,)
        if x % n == 0:
            x = 1
            result += (temp,)
            temp = ()
        else:
            x += 1
        if i == len(lst) - 1 and temp:
            result += (temp,)
    return (result)

def group_links(links, name):
    text = "<b>%s:</b>\n" % (name)
    for link in links:
        text += "  <a href=\"%s\">%s</a>\n" % (link["link"], link["name"])
    return text

def do_keyboard(lst):
    keyboard = []
    temp = []
    groups = group(lst, 2)
    for grouped in groups:
        for device in grouped:
            temp += [KeyboardButton(device["name"])]
        keyboard += [temp]
        temp = []
    keyboard += [[KeyboardButton("Leave a Feedback!")]]
    keyboard += [[KeyboardButton("Close Keyboard")]]
    return (keyboard)

"""
### GLOBALS
"""
def setGlobals():
    global db
    db = DBHandler("modding.sqlite")

"""
### INLINE QUERY
"""
def inline_query(bot, update):
    query = update.inline_query
    db.update_user(query.from_user)
    results = list()
    if query.query == "":
        devices = db.get_all_devices_roms()
    else:
        devices = (db.get_device(query.query),)
        links_db = db.link_search(query.query, True)
        if links_db:
            text = "Here are all links containing \"%s\" word.\n\n" % (query.query)
            for key in links_db.keys():
                text += "<b>%s</b>\n" % (key)
                for rom in links_db[key]:
                    text += "<a href=\"%s\">%s</a>\n" % (rom["link"], rom["name"])
                text += "\n"
            results.append(InlineQueryResultArticle(id=uuid4(),
                                                    title="All links containing \"%s\" word." % (query.query),
                                                    input_message_content=InputTextMessageContent(text,
                                                                                    parse_mode=ParseMode.HTML,
                                                                                    disable_web_page_preview=True), ))
    for device in devices:
        if "error" not in device:
            links = db.get_links(device["id"])
            if "error" not in links:
                text = group_links(links, device["name"])
                results.append(InlineQueryResultArticle(id=uuid4(),
                                                        title=device["name"],
                                                        input_message_content=InputTextMessageContent(text,
                                                                                    parse_mode=ParseMode.HTML,
                                                                                    disable_web_page_preview=True), ))
    bot.answerInlineQuery(query.id, results=results)

"""
### INLINE CALLBACK 
"""
def inline_button_callback(bot, update):
    query = update.callback_query
    text = ""
    keyboard = []
    query_data = query.data.split(".")
    if query_data[0] == "main":
        text = "Choose something."
        temp = []
        devices = db.get_all_devices_roms()
        groups = group(devices, 2)
        for grouped in groups:
            for device in grouped:
                temp += [InlineKeyboardButton(device["name"], callback_data="show.%s" % device["db_name"])]
            keyboard += [temp]
            temp = []
    elif query_data[0] == "show":
        device = db.get_device(query_data[1])
        text = group_links(db.get_links(device["id"]), device["name"])
        keyboard = [[InlineKeyboardButton("Main Menù", callback_data="main")]]
    elif query_data[0] == "feedback":
        if query_data[1] == "unread" or query_data[1] == "all":
            if query_data[1] == "unread":
                unread_db = db.feedback_get_unread()
            else:
                unread_db = db.feedback_get_unread(True)
            keyboard = []
            if unread_db:
                text = "Choose the feedback to read."
                unread_groups = group(group(unread_db, 2), 5)
                temp = []
                for groups in unread_groups[0]:
                    for grouped in groups:
                        lenght = 25
                        if len(grouped["text"]) > lenght:
                            button_text = "%s [...]" % (grouped["text"][:lenght].strip())
                        else:
                            button_text = "%s" % (grouped["text"][:lenght].strip())
                        temp += [InlineKeyboardButton(button_text, callback_data="feedback.read.%s" % grouped["id"])]
                    keyboard += [temp]
                    temp = []
            else:
                text = "Nothing to read."
            keyboard += [[InlineKeyboardButton("Go back", callback_data="feedback.menu")]]
        elif query_data[1] == "menu":
            text = "What do you want to read?"
            keyboard = [[InlineKeyboardButton("Unread feedbacks", callback_data="feedback.unread")],
                        [InlineKeyboardButton("All feedbacks", callback_data="feedback.all")]]
        elif query_data[1] == "read":
            feedback = db.feedback_get(query_data[2])
            db.feedback_set_read(query_data[2])
            name = ""
            username = ""
            if feedback["first_name"]:
                name += feedback["first_name"]
            if feedback["last_name"]:
                name += " %s" % feedback["last_name"]
            if feedback["username"]:
                username += " (@%s) " % feedback["username"]
            text += "From <b>%s</b>%s[ID: <i>%s</i>]\n\n%s" % (
            name.strip(), username, feedback["user_id"], feedback["feedback"])
            keyboard += [[InlineKeyboardButton("Go back", callback_data="feedback.unread")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if text:
        if query.message:
            bot.editMessageText(text=text, chat_id=query.message.chat_id, message_id=query.message.message_id,
                                reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        else:
            bot.editMessageText(text=text, inline_message_id=query.inline_message_id, reply_markup=reply_markup,
                                parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    elif keyboard:
        if query.message:
            bot.editMessageReplyMarkup(chat_id=query.message.chat_id, message_id=query.message.message_id,
                                       reply_markup=reply_markup)
        else:
            bot.editMessageReplyMarkup(inline_message_id=query.inline_message_id, reply_markup=reply_markup)


"""
### COMMANDS
"""
def start(bot, update):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    # The bot will automatically create the right db if it not exist
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS `devices` ( `id` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, `name` TEXT, `codename`"
        " TEXT )")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS `feedback` ( `id` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, `user_id` INTEGER,"
        " `text` TEXT, `read` INTEGER DEFAULT 0 )")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS `roms` ( `id` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, `device_id` INTEGER, `link`"
        " TEXT, `name` TEXT )")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS `users` ( `id` INTEGER UNIQUE, `name_first` TEXT, `name_last` TEXT, `username` TEXT,"
        " `privs` INTEGER, `last_use` INTEGER, `time_used` INTEGER, `notifications` INTEGER DEFAULT 1"
        ", PRIMARY KEY(`id`))")
    handle.commit()
    db.update_user(update.message.from_user)
    text = """Hello! In this bot you can find everything about your device modding, say /help if you want to know more!
Quick Tip: try /menu !
Use /yes if you want to receive notifications and /no if you don't want to receive them"""
    devices = db.get_all_devices_roms()
    keyboard = []
    temp = []

    groups = group(devices, 2)
    for grouped in groups:
        for device in grouped:
            temp += [KeyboardButton(device["name"])]
        keyboard += [temp]
        temp = []
    keyboard += [[KeyboardButton("Close Keyboard")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, selective=True)
    update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
                              disable_web_page_preview=True)

def yes(bot, update):
    db.update_user(update.message.from_user)
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    cursor.execute("UPDATE users SET notifications=1 WHERE id=?", (update.message.from_user.id,))
    handle.commit()
    text = "Notifications permissions has been updated"
    update.message.reply_text(text=text)

def no(bot, update):
    db.update_user(update.message.from_user)
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    cursor.execute("UPDATE users SET notifications=2 WHERE id=?", (update.message.from_user.id,))
    handle.commit()
    text = "Notifications permissions has been updated"
    update.message.reply_text(text=text)

def help(bot, update):
    db.update_user(update.message.from_user)
    text = """<b>Commands: </b>
/kb or /keyboard - Brings the normal keyboard up.
/nkb or /nokeyboard - Brings the annoying keyboard down!
/menu - Shows the inline menù! It's cool!
/credits - Shows who made this for you!
/help - Shows this help message.

I work <b>Inline</b> too! Just type <b>@the_username_of_this_bot</b> to see the complete list or put something after """ \
"""that to do a quick search, like <b>@the_username_of_this_bot nougat</b>.
           
<b>If you want to send a feedback: </b>
Just close the keyboard ( /nkb ) and reopen it ( /kb ), now you'll able to see the feedback button in the keyboard.
           
Use /yes to turn on notifications and /no if you don't want to receive them"""
    update.message.reply_text(text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

def credits(bot, update):
    db.update_user(update.message.from_user)
    text = "Made and maintained by @Tostapunk"
    update.message.reply_text(text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

def keyboard(bot, update):
    db.update_user(update.message.from_user)
    text = "Keyboard is up."
    devices = db.get_all_devices_roms()
    keyboard = do_keyboard(devices)
    reply_markup = ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True)
    update.message.reply_text(reply_markup=reply_markup, text=text, parse_mode=ParseMode.HTML,
                              disable_web_page_preview=True)

def nokeyboard(bot, update):
    db.update_user(update.message.from_user)
    text = "Keyboard is down."
    reply_markup = ReplyKeyboardHide()
    update.message.reply_text(reply_markup=reply_markup, text=text, parse_mode=ParseMode.HTML,
                              disable_web_page_preview=True)

def message_handler(bot, update):
    db.update_user(update.message.from_user)
    if update.message.text == "Close Keyboard":
        text = "Keyboard is down."
        reply_markup = ReplyKeyboardHide()
        update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
                                  disable_web_page_preview=True)
    else:
        device = db.get_device(update.message.text)
        if "error" not in device:
            links = db.get_links(device["id"])
            if "error" not in links:
                text = group_links(links, device["name"])
                update.message.reply_text(text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

def feedread(bot, update):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query = cursor.execute("SELECT privs FROM users WHERE id=?", (update.message.from_user.id,)).fetchone()
    if query["privs"] == -2:
        text = "What do you want to read?"
        keyboard = [[InlineKeyboardButton("Unread feedbacks", callback_data="feedback.unread")],
                    [InlineKeyboardButton("All feedbacks", callback_data="feedback.all")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.sendMessage(chat_id=update.message.chat.id, reply_markup=reply_markup, text=text, parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True)

def menu(bot, update):
    db.update_user(update.message.from_user)
    text = "Choose something."
    keyboard = []
    temp = []
    devices = db.get_all_devices_roms()
    groups = group(devices, 2)
    for grouped in groups:
        for device in grouped:
            temp += [InlineKeyboardButton(device["name"], callback_data="show.%s" % device["db_name"])]
        keyboard += [temp]
        temp = []
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.sendMessage(chat_id=update.message.chat.id, reply_markup=reply_markup, text=text, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)

def add_link(bot, update, args):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query = cursor.execute("SELECT privs FROM users WHERE id=?", (update.message.from_user.id,)).fetchone()
    if query["privs"] == -2:
        if len(args) > 2:
            link = args[0]
            device_name = args[1]
            name = " ".join(args[2:])
            pattern = (r'^(?:http|ftp)s?://'
                       r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                       r'localhost|'
                       r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                       r'(?::\d+)?'
                       r'(?:/?|[/?]\S+)$')
            link_check = re.compile(pattern, re.IGNORECASE)
            match = link_check.match(link)
            if match:
                devices = db.get_all_devices_roms()
                device_id = None
                for device in devices:
                    if device_name.lower() == device["db_name"]:
                        device_id = device["id"]
                if device_id:
                    db.add_link(device_id, link, name)
                    text = "Added <b>%s</b> successfully." % (name)
                else:
                    text = ""
                    text += "No device with that name.\n\n"
                    text += "Devices avaiable:"
                    for device in devices:
                        text += "\n  <b>%s</b>" % device["db_name"]
            else:
                text = "Invalid URL."
        else:
            text = ""
            text += "Too few arguments.\n\n"
            text += "Required arguments are, in this order:\n"
            text += "  <b>Link</b>\n"
            text += "  <b>Device name</b>\n"
            text += "  <b>Link name</b>"
    else:
        text = "You are not an admin."
    bot.sendMessage(chat_id=update.message.chat.id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

def ban(bot, update, args):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query = cursor.execute("SELECT privs FROM users WHERE id=?", (update.message.from_user.id,)).fetchone()
    if query["privs"] == -2:
        bot.kickChatMember(update.message.chat_id, update.message.reply_to_message.from_user.id)
        text = "Bye bye"
    else:
        text = "You are not an admin."
    bot.sendMessage(update.message.chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview="true")

def adminhelp(bot, update):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query = cursor.execute("SELECT privs FROM users WHERE id=?", (update.message.from_user.id,)).fetchone()
    if query["privs"] == -2:
        text = """<b>Admin commands:</b>
/feedread | to read the feedbacks
/add <b>Link Device name Link name</b> | to add something (rom, kernel, guide ecc..)
/check | to check if the bot is connected and fully working
/send <b>message</b> | to send a message to all the users that have started the bot and accepted to receive """ \
"""notifications(you can use HTML tags for the text)
/alertsend <b>message</b> | to send a message to all the users that have started the bot, no matter if they want""" \
"""notifications(you can use HTML tags for the text)
/ban | you know it."""
    else:
        text = "You are not an admin."
    bot.sendMessage(update.message.chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview="true")

def check(bot, update):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query = cursor.execute("SELECT privs FROM users WHERE id=?", (update.message.from_user.id,)).fetchone()
    if query["privs"] == -2:
        text = "Bot online."
    else:
        text = "You are not an admin."
    bot.sendMessage(update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

def msgtousr(bot, update, args):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query = cursor.execute("SELECT privs FROM users WHERE id=?", (update.message.from_user.id,)).fetchone()
    if query["privs"] == -2:
        text = update.message.text[6:]
        handle = sqlite3.connect('modding.sqlite')
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query_db = cursor.execute("SELECT id FROM users WHERE notifications=1")
        for chat_id in query_db:
            try:
                bot.sendMessage(chat_id=chat_id["id"], text=text, parse_mode=ParseMode.HTML
                                , disable_web_page_preview="true")
                print("Sent to [%s]" % chat_id["id"])
            except:
                print("[%s] failed" % chat_id["id"])
    else:
        text = "You are not an admin."
        bot.sendMessage(update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

def msgalert(bot, update, args):
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query = cursor.execute("SELECT privs FROM users WHERE id=?", (update.message.from_user.id,)).fetchone()
    if query["privs"] == -2:
        text = update.message.text[11:]
        handle = sqlite3.connect('modding.sqlite')
        handle.row_factory = sqlite3.Row
        cursor = handle.cursor()
        query_db = cursor.execute("SELECT id FROM users").fetchall()
        for chat_id in query_db:
            try:
                bot.sendMessage(chat_id=chat_id["id"], text=text, parse_mode=ParseMode.HTML
                                , disable_web_page_preview="true")
                print("Sent to [%s]" % chat_id["id"])
            except:
                print("[%s] failed" % chat_id["id"])
    else:
        text = "You are not an admin, go away."
        bot.sendMessage(update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

"""
### FEEDBACK ENGINE
"""
def feedback_leave_start(bot, update):
    text = "Have you got any suggestions to improve the bot? Have you got a problem, bug, " \
           "or your favourite ROM isn't there? Write it here with a reply to this message!"
    reply_markup = ReplyKeyboardMarkup([[KeyboardButton("Cancel")]], one_time_keyboard=True, selective=True,
                                       resize_keyboard=True)
    update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
                              disable_web_page_preview=True)
    return (0)

def feedback_leave_done(bot, update, user_data):
    feedback = update.message.text
    user_id = update.message.from_user.id
    db.feedback_submit(user_id, feedback)
    text = "Thank you for your feedback!"
    devices = db.get_all_devices_roms()
    keyboard = do_keyboard(devices)
    reply_markup = ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True)
    update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
                              disable_web_page_preview=True)
    text = "New feedback received."
    handle = sqlite3.connect('modding.sqlite')
    handle.row_factory = sqlite3.Row
    cursor = handle.cursor()
    query_db = cursor.execute("SELECT id FROM users WHERE privs=-2")
    for chat_id in query_db:
        try:
            bot.sendMessage(chat_id=chat_id["id"], text=text)
            print("Sent to [%s]" % chat_id["id"])
        except:
            print("[%s] failed" % chat_id["id"])
    return (ConversationHandler.END)

def feedback_leave_cancel(bot, update, user_data):
    text = "Action cancelled."
    devices = db.get_all_devices_roms()
    keyboard = do_keyboard(devices)
    reply_markup = ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True)
    update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
                              disable_web_page_preview=True)
    return (ConversationHandler.END)

"""
### MAIN
"""
def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater('INSERT YOUR TOKEN HERE')
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Set Database Handler as global class
    setGlobals()

    # Inline Query Handler
    dp.add_handler(InlineQueryHandler(inline_query))

    # Inline Callback
    dp.add_handler(CallbackQueryHandler(inline_button_callback))

    # Start
    dp.add_handler(CommandHandler("start", start))

    # Set that the user want to receive messages from the bot (/send function messages)
    dp.add_handler(CommandHandler('yes', yes))

    # Set that the user doesn't want to receive messages from the bot (/send function messages)
    dp.add_handler(CommandHandler('no', no))

    # Help
    dp.add_handler(CommandHandler("help", help))

    # Shows who made this bot
    dp.add_handler(CommandHandler("credits", credits))

    # Send keyboard up
    dp.add_handler(CommandHandler("keyboard", keyboard))
    dp.add_handler(CommandHandler("kb", keyboard))

    # Send keyboard down
    dp.add_handler(CommandHandler("nokeyboard", nokeyboard))
    dp.add_handler(CommandHandler("nkb", nokeyboard))

    # Show you the received feedbacks
    dp.add_handler(CommandHandler('feedread', feedread))

    # Inline Menù
    dp.add_handler(CommandHandler("menu", menu))

    # Add Link
    dp.add_handler(CommandHandler("add", add_link, pass_args=True))

    # Ban
    dp.add_handler(CommandHandler('ban', ban, pass_args=True))

    # Help commands for admins
    dp.add_handler(CommandHandler("adminhelp", adminhelp))

    # Connection test
    dp.add_handler(CommandHandler("check", check))

    # Send a message to all the users that have the value 1 on the notifications column
    dp.add_handler(CommandHandler("send", msgtousr, pass_args=True))

    # Send a message to all the users registered in the db, no matter if they doesn't want notifications from the bot
    dp.add_handler(CommandHandler("alertsend", msgalert, pass_args=True))

    # Leave Feedback
    dp.add_handler(ConversationHandler(entry_points=[RegexHandler("^Leave a Feedback!$", feedback_leave_start)],
                                       states={0: [
                                           RegexHandler("^(?!^Cancel$).*$", feedback_leave_done, pass_user_data=True)]},
                                       fallbacks=[
                                           RegexHandler("^Cancel$", feedback_leave_cancel, pass_user_data=True)]))
    
    # Keyboard Button Reply
    dp.add_handler(MessageHandler(Filters.text |
                                  Filters.status_update, message_handler))
       
    # Log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()