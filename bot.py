#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

from telegram import InlineQueryResultPhoto, InlineQueryResultArticle, ParseMode
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, MessageHandler, Filters
from telegram.utils.helpers import escape_markdown
import logging
import requests
from functools import wraps
import paho.mqtt.publish as publish
from tinydb import TinyDB, Query
from random import randint
from bot_config import API_KEY
from time import localtime, strftime
import datetime as dt

DB = TinyDB('db.json')

# A simple database to store imformation persistently
def setup_db():
    """ initialize a new database """
    db = TinyDB('db.json')
    chats = db.table('chats')
    members = db.table('members')
    chats.insert({'id': -231128423}) # Kolab chat group
    members.insert({'id': 235493361})

def get_member_ids(db):
    table = db.table('members')
    return [e['id'] for e in table.all()]

def get_chat_ids(db):
    table = db.table('chats')
    return [e['id'] for e in table.all()]

def add_member_id(db, id):
    members = db.table('members')
    Member = Query()
    if members.get(Member.id == id) is None:
        members.insert({'id': id})
        return True
    else:
        return False



def restricted(func):
    """ 
    This decorator allows to restrict the access of a handler 
    to only KOLAB users and chat groups 
    """
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id  = update.effective_user.id
        chat_id  = update.effective_chat.id
        members  = get_member_ids(DB)
        chats    = get_chat_ids(DB)

        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        print("Request from {} {} ({}) in chat {}."
            .format(first_name, last_name, user_id, chat_id))

        if user_id not in members and chat_id not in chats:
            # Log unauthorized attempt to console and return
            first_name = update.effective_user.first_name
            last_name = update.effective_user.last_name
            print("Unauthorized request from {} {} ({}) in chat {}."
                .format(first_name, last_name, user_id, chat_id))
            return
        return func(update, context, *args, **kwargs)
    return wrapped


@restricted
def inlinequery(update: 'Update', context: 'Context'):
    """Handle inline queries."""
    query = update.inline_query.query
    results = [
        InlineQueryResultArticle(
            id=uuid4(),
            title="Caps",
            input_message_content=InputTextMessageContent(
                query.upper())),
        InlineQueryResultArticle(
            id=uuid4(),
            title="Bold",
            input_message_content=InputTextMessageContent(
                "*{}*".format(escape_markdown(query)),
                parse_mode=ParseMode.MARKDOWN)),
        InlineQueryResultArticle(
            id=uuid4(),
            title="Italic",
            input_message_content=InputTextMessageContent(
                "_{}_".format(escape_markdown(query)),
                parse_mode=ParseMode.MARKDOWN))]



def get_cat_url():
    contents = requests.get('https://aws.random.cat/meow').json()
    url = contents['file']
    return url

def get_cat_image():
    allowed_extension = ['jpg','jpeg','png']
    file_extension = ''
    while file_extension not in allowed_extension:
        url = get_cat_url()
        file_extension = re.search("([^.]*)$",url).group(1).lower()
    return url


@restricted
def meow(update: 'Update', context: 'CallbackContext'):
    bot = context.bot
    chat_id = update.message.chat_id
    url = get_cat_url()
    bot.send_photo(chat_id=chat_id, photo=url)


@restricted
def energy_use(update: 'Update', context: 'CallbackContext'):
    """ Send picture of current energy use """
    bot = context.bot
    chat_id = update.message.chat_id
    url = "https://vloer.ko-lab.space/verbruikdag.png?random=" + str(randint(1,9999))

    try:
        bot.send_photo(chat_id=chat_id, photo=url)
    except Exception as err:
        msg = "Oops...something went wrong: {}".format(err)
        print(msg)
        update.message.reply_text(msg)


@restricted
def pixelpaint(update: 'Update', context: 'CallbackContext'):
    """ start pixelpaint app """
    args = context.args
    message = " ".join(args)

    # send "/paint start" to start the mqtt client on the floor-pi
    # do this if another program is running on the led floor.
    if message == "start":
        print("Trying to start LED floor...")
        try:
            publish.single("vloer/startscript", "paint", hostname="10.94.176.100", 
                auth={'username': 'vloer', 'password': 'ko-lab'}, 
                port=1883, client_id="kolabbot")
            print("LED floor...")
        except (ConnectionRefusedError, TimeoutError) as err:
            msg = "Could not start Pixel Paint: {}".format(err)
            print(msg)
            update.message.reply_text(msg)

    # send a link to the pixel paint app
    try:
        # TODO: try to open pixel paint url
        url = "http://10.90.154.80/"
        #response = requests.get(url)
        update.message.reply_text("To paint the floor, go to {}".format(url))
    except (ConnectionRefusedError, TimeoutError) as err:
        msg = "Could not start Pixel Paint: ".format(err)
        print(msg)
        update.message.reply_text(msg)


@restricted
def change_led_floor_color(update: 'Update', context: 'CallbackContext'):
    """ 
    Check if sender is member of Ko-Lab group chat. If yes,
    change the color of the LED floor. If not, tell them to go away 
    """
    args = context.args
    message = " ".join(args)

    try:
        publish.single("ledfloorupdates", message, hostname="10.90.154.80", port=1883, client_id="kolabbot")
        update.message.reply_text('Changing LED floor color to "{}".'.format(message))
    except (ConnectionRefusedError, TimeoutError) as err:
        msg = "Could not connect to LED-floor: {}".format(err)
        print(msg)
        update.message.reply_text(msg)


@restricted
def write_to_led_krant(update: 'Update', context: 'CallbackContext'):
    """ 
    show message on LED-krant
    """
    args = context.args
    message = " ".join(args)

    try:
        publish.single("ledkrant/write", message, hostname="10.94.176.100", port=1883, client_id="kolabbot",
            auth={'username': 'vloer', 'password': 'ko-lab'})
        update.message.reply_text('Writing "{}" to LED-krant.'.format(message))
    except (ConnectionRefusedError, TimeoutError) as err:
        msg = "Could not connect to LED-krant: {}".format(err)
        print(msg)
        update.message.reply_text(msg)


def show_time_on_krant(context: 'CallbackContext'):
    """ show time on LED-krant """
    print("Showing time on LED-Krant")
    message = strftime("%H:%M", localtime())

    try:
        publish.single("ledkrant/time", message, hostname="10.94.176.100", port=1883, 
            client_id="kolabbot", auth={'username': 'vloer', 'password': 'ko-lab'})
    except (ConnectionRefusedError, TimeoutError) as err:
        msg = "Could not connect to LED-krant: {}".format(err)
        print(msg)


def addme(update: 'Update', context: 'CallbackContext'):
    """ Add user to the whitelist. """
    user_id  = update.effective_user.id
    chat_id  = update.effective_chat.id
    chats    = get_chat_ids(DB)

    if chat_id not in chats:
        update.message.reply_text('Did not work. Run this command inside the Ko-Lab group.')
    else:
        if add_member_id(DB, user_id): 
            update.message.reply_text('I have added you to the whitelist. You can now send commands from outside the Ko-Lab chat.')
        else:
            update.message.reply_text('You are already on the whitelist.')


def start(update: 'Update', context: 'CallbackContext'):
    """ Send a message when the command /start is issued. """
    update.message.reply_text('I am Kolabbot. I pass butter.')


def help(update: 'Update', context: 'CallbackContext'):
    """ Send a message when the command /help is issued. """
    update.message.reply_text('Beep. Boop.')


def no_command(update: 'Update', context: 'CallbackContext'):
    """ What happens when you send a message to the bot with no command. """
    update.message.reply_text('Sorry, I am not very chatty. Type / to see a list of commands I understand.')


def error(update: 'Update', context: 'CallbackContext'):
    """ Log Errors caused by Updates. """
    logger.warning('Update "%s" caused error "%s"', update, context.error)



def main():
    # Updater checks for new events, then passes them on to the dispatcher.
    # Dispatcher sorts them and calls the handling functions.
    updater = Updater(API_KEY, use_context=True)
    dispatcher = updater.dispatcher
    jobs = updater.job_queue

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("krant", write_to_led_krant))
    dispatcher.add_handler(CommandHandler("floor", change_led_floor_color))
    dispatcher.add_handler(CommandHandler("paint", pixelpaint))
    dispatcher.add_handler(CommandHandler("addme", addme))
    dispatcher.add_handler(CommandHandler("verbruik", energy_use))
    dispatcher.add_handler(CommandHandler("meow", meow))
    dispatcher.add_handler(MessageHandler(Filters.text, no_command))
    dispatcher.add_handler(InlineQueryHandler(inlinequery))
    dispatcher.add_error_handler(error)

    
    current = dt.datetime.now()
    current_td = dt.timedelta(hours=current.hour, minutes=current.minute, seconds=current.second, microseconds=current.microsecond)
    # to_hour = dt.timedelta(hours=round(current_td.total_seconds()/3600))
    to_quarter = dt.timedelta(hours=round(current_td.total_seconds()/900))
    # to_min = dt.timedelta(minutes=round(current_td.total_seconds()/60))
    startdelta = dt.datetime.combine(current,dt.time(0))+to_quarter
    print(startdelta)

    jobs.run_repeating(show_time_on_krant, interval=900, first=startdelta)


    updater.start_polling()
    updater.idle()
    

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    main()