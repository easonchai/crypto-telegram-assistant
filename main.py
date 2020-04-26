# coding=utf-8
# === CRYPTO TELEGRAM BOT ===
# Author: Eason Chai
# Created: 20 April 2020
# Version: V1.0
# Github repo: https://github.com/easonchai/crypto-telegram-assistant

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, BaseFilter, CallbackQueryHandler, \
    ConversationHandler
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove
import requests
import re
import json
import requests
import datetime
import traceback
import os
import random
from datetime import datetime
import subprocess
import glob
import codecs
import datetime
from bs4 import BeautifulSoup
import logging
from functools import wraps
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
admin_id = [512004133]

CHOOSING = range(1)

# Global Variables
address = ""
mn_status = 0
prev_balance = 0
earned = 0
last_reward = ""
reward_block = 0
stake_block = 0
cmc_id = []
cmc_ticker = []


# =========================== GET DATA ===========================
def get_energi_info(bot, update):
    try:
        global address, mn_status, prev_balance, earned, last_reward

        message = "\U00002747 ENERGI MASTERNODE \U00002747\n"
        message += "Status: "
        if mn_status == 1:
            message += "\U0001F3BE *[ACTIVE]*\n\n"
        else:
            message += "\U0001F534 *[INACTIVE]*\n\n"

        message += ("\U0001F4B0 Current Balance: *" + str(round(prev_balance, 5)) + " NRG*\n")
        message += ("\U0001F4B5 Total earned today: *" + str(round(earned, 3)) + " NRG*\n")
        message += ("\U0001F4E5 _Last reward time: " + last_reward + "_\n\n")
        message += ("Address: `%s`\n" % address)
        message += ("[Block Explorer](https://explorer.energi.network/address/%s/transactions)" % address)

        chat_id = update.message.chat_id

        button_list = ["\U000026CF Miner", "\U00002747 Energi", "\U00002699 Settings", "\U0001F4CA Market Data",
                       "\U00002753 Help"]
        bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=2), one_time_keyboard=True)
        update.message.reply_text('_What else can I do for you?_', reply_markup=markup,
                                  parse_mode="markdown")
        return CHOOSING
    except Exception as e:
        error_handler(bot, update, e)


def get_mn_status():
    global address, mn_status, prev_balance, earned, last_reward
    return


def get_mn_reward(bot, update):
    global address, mn_status, prev_balance, earned, last_reward, reward_block

    url = "https://explorer.energi.network/api?module=account&action=txlistinternal&address" \
          "=%s&startblock=%s " % (address, reward_block + 1)

    response = requests.post(url)  # Get latest tx
    data = json.loads(response.text)
    result_set = data['result']
    desired_data = []  # Stores all the blocks after the last reward block
    earned_since_call = 0;

    for x in result_set:
        if int(x['blockNumber']) > reward_block:
            desired_data.append(x)

    if desired_data:
        for x in desired_data:
            if int(x['blockNumber']) > reward_block:
                reward_block = int(x['blockNumber'])
                epoch = float(x['timeStamp'])
                last_reward = time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(epoch))
                print("last reward in mn reward" + last_reward)
                # Update data
            nrg_earned = float(int(x['value']) / 10 ** 18)

            message = ("\U0000303D *New Reward Received!* \U0000303D\n"
                       "\U0001F4B5 > Masternode Reward of Amount *0.914* NRG.\n")
            earned += nrg_earned
            earned_since_call += nrg_earned

            bot.send_message(chat_id=512004133, text=message, parse_mode='Markdown')

    return earned_since_call


def get_stake_reward(bot, update):
    global address, mn_status, prev_balance, earned, last_reward, reward_block, stake_block

    url = "https://explorer.energi.network/api?module=account&action=getminedblocks&address=%s" % address

    response = requests.post(url)  # Get latest tx
    data = json.loads(response.text)
    result_set = data['result']
    desired_data = []  # Stores all the blocks after the last reward block
    earned_since_call = 0;

    for x in result_set:
        if int(x['blockNumber']) > stake_block:
            desired_data.append(x)

    if desired_data:
        for x in desired_data:
            if int(x['blockNumber']) > stake_block:
                stake_block = int(x['blockNumber'])
                if stake_block > reward_block:
                    last_reward = x['timeStamp']
                    print("last reward in stake reward" + last_reward)
            message = ("\U0001F4E5 *New Block Mined!* \U0001F4B5\n"
                       "\U000026A1 > Processed Stake Reward of Amount *2.28* NRG.\n")
            earned += 2.28
            earned_since_call += 2.28

            bot.send_message(chat_id=512004133, text=message, parse_mode='Markdown')

    return earned_since_call


def background_process(bot, update):
    global address, mn_status, prev_balance, earned, last_reward, reward_block, stake_block
    try:
        get_balance_url = "https://explorer.energi.network/api?module=account&action=eth_get_balance&address=%s" % address

        response = requests.post(get_balance_url)  # Get balance
        data = json.loads(response.text)
        hex_balance = data['result']
        balance = float(int(hex_balance, 16) / 10 ** 18)

        # ======== GET STATUS ========#
        earned_since_call = get_mn_reward(bot, update) + get_stake_reward(bot, update)

        change = balance - earned_since_call - prev_balance
        if change > 0.01:
            message = ("\U0001F45D *New Transaction Detected!*\n"
                       "Amount transferred: \n*%.2f* NRG\n"
                       "New wallet balance: \n_%.2f_ NRG" % (change, balance))
            bot.send_message(chat_id=512004133, text=message, parse_mode='Markdown')

        prev_balance = balance
        # Write new data to file
        f = open("./data/energi.txt", "w")
        data = "Address:%s\n" \
               "MN Status:%d\n" \
               "Balance:%f\n" \
               "Earned:%f\n" \
               "Last Reward Time:%s\n" \
               "Reward Block:%d\n" \
               "Stake Block:%d" % (address, mn_status, prev_balance, earned, last_reward, reward_block, stake_block)
        f.write(data)
        f.close()
        print("last reward in bg process" + last_reward)
        miner_background(bot, update)
        print("Background process complete")
    except Exception as e:
        error_handler(bot, update, e)


def get_miner_info(bot, update):
    try:
        chat_id = update.message.chat_id
        message = "_Obtaining info..._"
        bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        data = retrieve("./data/", "miner.txt").split(" - ")
        address = data[1]
        name = data[0].upper()

        url = "https://api.ethermine.org/miner/%s/currentStats" % address
        print(url)
        response = requests.get(url)
        print(response)

        if response.status_code == 200:
            miner_info = json.loads(response.text)
            current_stats = miner_info['data']

            # Getting data
            latest_status = current_stats['activeWorkers']
            reported = current_stats['reportedHashrate'] / 10 ** 6  # Convert H to MH
            average = current_stats['averageHashrate'] / 10 ** 6  # Convert H to MH
            current = current_stats['currentHashrate'] / 10 ** 6  # Convert H to MH
            unpaid = (current_stats['unpaid']) / 10 ** 18  # Conversion
            eth_per_day = (current_stats['coinsPerMin']) * 1440  # Convert per min to day
            last_seen = datetime.datetime.fromtimestamp(current_stats['lastSeen'])

            message = "=== \U000026CF %s MINER \U000026CF ===\n" % name
            message += ("_Last Seen: " + last_seen.strftime('%d/%m/%y') + " [" +
                        last_seen.strftime('%H:%M:%S') + "]_\n")  # Format is DD/MM/YYYY [HH:MM:SS]
            message += "Miner Status: "
            if latest_status == 1:
                message += "\U0001F3BE *[ACTIVE]*\n\n"
            else:
                message += "\U0001F534 *[INACTIVE]*\n\n"

            message += ("\U0001F4B0 Current Balance: *" + str(round(unpaid, 5)) + " ETH*\n")
            message += ("Current Hashrate: *" + str(round(current, 2)) + " MH/s*\n")
            message += ("\U0001F4C8 Average Hashrate: *" + str(round(average, 2)) + " MH/s*\n")
            message += ("\U0001F4CA Reported Hashrate: *" + str(round(reported, 2)) + " MH/s*\n")
            message += ("\U0001F4B5 Estimated: *" + str(round(eth_per_day, 5)) + " ETH/day*\n\n")
            days_till_pay = (0.01 - unpaid) / eth_per_day
            message += ("_\U000023F3 Days Till Payout: " + str(round(days_till_pay, 1)) + " day(s)_\n\n")
        else:
            message = "_Error connecting to server!_"
        bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

        button_list = ["\U000026CF Miner", "\U00002747 Energi", "\U00002699 Settings", "\U0001F4CA Market Data",
                       "\U00002753 Help"]
        markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=2), one_time_keyboard=True)
        update.message.reply_text('_Anything else?_', reply_markup=markup,
                                  parse_mode="markdown")
        return CHOOSING
    except Exception as e:
        error_handler(bot, update, e)


def miner_background(bot, update):
    try:
        message = ""
        data = retrieve("./data/", "miner.txt").split(" - ")
        address = data[1]

        url = "https://api.ethermine.org/miner/%s/currentStats" % address
        print(url)
        response = requests.get(url)
        print(response)

        if response.status_code == 200:
            miner_info = json.loads(response.text)
            current_stats = miner_info['data']
            # Getting data
            latest_status = current_stats['activeWorkers']
            reported = current_stats['reportedHashrate'] / 10 ** 6  # Convert H to MH
            average = current_stats['averageHashrate'] / 10 ** 6  # Convert H to MH
            if latest_status == 1:
                if reported < 0.8*21.2:
                    message = "\U000026A0 _Reported hashrate has dipped below threshold!\U000026A0\nReported Hashrate: %f_" % reported
                if average < 0.8*21.2:
                    message = "\U000026A0 _Average hashrate has dipped below threshold!\U000026A0\nAverage Hashrate: %f_" % average
            else:
                message = "\U000026A0 _Miner has shut down!\U000026A0_"

            if message:
                bot.send_message(chat_id=512004133, text=message, parse_mode='Markdown')
    except Exception as e:
        error_handler(bot, update, e)


def get_cmc_id(bot, update):
    global cmc_ticker, cmc_id
    cmc_api_key = retrieve("./data/api_keys/", "cmc.txt")
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/map'
    parameters = {
        'symbol': cmc_ticker
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': cmc_api_key,
    }

    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        dataset = data['data']
        for x in dataset:
            cmc_id.append(x['id'])
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
        error_handler(bot, update, e)


def market_data(bot, update):
    global cmc_id
    get_cmc_id(bot, update)
    try:
        cmc_api_key = retrieve("./data/api_keys/", "cmc.txt")
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
        parameters = {}
        headers = {}
        message = "*=== \U0001F4CA Market Data ===*\n"
        for x in range(len(cmc_id)):
            parameters = {
                'id': cmc_id[x],
            }
            headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': cmc_api_key,
            }

            session = Session()
            session.headers.update(headers)
            response = session.get(url, params=parameters)
            data = json.loads(response.text)
            current_id = str(cmc_id[x])
            dataset = data['data'][current_id]
            name = dataset['name']
            ticker = dataset['symbol']
            rank = dataset['cmc_rank']
            price = dataset['quote']['USD']['price']
            change = dataset['quote']['USD']['percent_change_24h']

            message += "%s [%s]\nRank: %d\nPrice: %.2f\nPercent Change (24 Hrs): %.2f%%\n" % (name, ticker, rank, price, change)
        bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')

        button_list = ["\U000026CF Miner", "\U00002747 Energi", "\U00002699 Settings", "\U0001F4CA Market Data",
                       "\U00002753 Help"]
        markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=2), one_time_keyboard=True)
        update.message.reply_text('_Is there anything else?_', reply_markup=markup,
                                  parse_mode="markdown")
        return CHOOSING
    except Exception as e:
        error_handler(bot, update, e)


# =========================== END OF GET DATA ===========================

def main():
    try:
        global address, mn_status, prev_balance, earned, last_reward, reward_block, stake_block, cmc_ticker, cmc_id
        updater = Updater(open("./data/api_keys/telegram.txt", "r").read())
        dp = updater.dispatcher
        # dp.add_handler(CommandHandler('start', start))
        dp.add_handler(CommandHandler('help', help))
        dp.add_handler(CommandHandler('miner', get_miner_info))
        dp.add_handler(CommandHandler('energi', get_energi_info))
        # dp.add_handler(CommandHandler('portfolio', get_price_list))
        # dp.add_handler(CommandHandler('settings', get_energi_price, pass_args=True))
        # dp.add_handler(CommandHandler('lending', resetminer))

        # Conversation Handlers
        start_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],

            states={
                CHOOSING: [MessageHandler(Filters.regex('Miner$'), get_miner_info),
                           MessageHandler(Filters.regex('Energi$'), get_energi_info),
                           MessageHandler(Filters.regex('Settings$'), help),
                           MessageHandler(Filters.regex('Market Data$'), market_data),
                           MessageHandler(Filters.regex('Help$'), help)],
            },
            fallbacks = [MessageHandler(Filters.regex('Help$'), help)]
        )
        dp.add_handler(start_handler)

        #  For unknown commands
        unknown_handler = MessageHandler(Filters.command, unknown)
        dp.add_handler(unknown_handler)

        # Threaded process
        j = updater.job_queue
        hourly_update = j.run_repeating(background_process, interval=3600, first=0)
        r = updater.job_queue
        reset_counter = r.run_daily(reset_earned, datetime.time(23, 43), days=(0, 1, 2, 3, 4, 5, 6))

        # m = updater.job_queue
        # morning_routine = m.run_daily(morning_update, datetime.time(9,0), days=(0, 1, 2, 3, 4, 5, 6))

        # Preliminary Load
        file_data = retrieve("./data/", "energi.txt", True)
        address = file_data[0].split(":")[1].strip('\n')
        mn_status = int(file_data[1].split(":")[1])
        prev_balance = float(file_data[2].split(":")[1])
        earned = float(file_data[3].split(":")[1])
        last_reward = file_data[4].split(":",1)[1].strip('\n') if file_data[4].split(":",1)[1].endswith('\n') else file_data[4].split(":",1)[1]
        reward_block = int(file_data[5].split(":")[1])
        stake_block = int(file_data[6].split(":")[1])
        print("last reward in main" + last_reward)
        cmc_ticker = retrieve("./data/", "ticker.txt")

        print("\n+===============================================+")
        print("|========== Telegram Bot is now LIVE! ==========|")
        print("+===============================================+")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        traceback.print_exc()


def start(bot, update):
    try:
        text = "_Hello, {user}!_".format(user=update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode='Markdown')

        button_list = ["\U000026CF Miner", "\U00002747 Energi", "\U00002699 Settings", "\U0001F4CA Market Data", "\U00002753 Help"]
        markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=2), one_time_keyboard=True)
        update.message.reply_text('_What would you like to do today?_', reply_markup=markup,
                                  parse_mode="markdown")
        return CHOOSING
    except Exception as e:
        error_handler(bot, update, e)


def help(bot, update):
    try:
        chat_id = update.message.chat_id
        message = retrieve("./data/", "help.txt")
        bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        button_list = ["\U000026CF Miner", "\U00002747 Energi", "\U00002699 Settings", "\U0001F4CA Market Data",
                       "\U00002753 Help"]
        markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=2), one_time_keyboard=True)
        update.message.reply_text('_What else can I help you with?_', reply_markup=markup,
                                  parse_mode="markdown")
        return CHOOSING
    except Exception as e:
        error_handler(bot, update, e)


def unknown(bot, update):
    try:
        bot.send_message(chat_id=update.message.chat_id, text="_Sorry, I didn't understand that command! Try typing "
                                                              "/help to see the list of commands available!_",
                         parse_mode='Markdown')
    except Exception as e:
        error_handler(bot, update, e)


def reset_earned(bot, update):
    try:
        print("RESET")
        global earned
        earned = 0;
    except Exception as e:
        error_handler(bot, update, e)


# =================== HELPERS ==================== #
def retrieve(directory, filename, split=False):
    try:
        text = ""
        path = os.path.join(directory, filename)
        print(path)
        if split:
            text = open(path, "r").readlines()
            for x in range(len(text)):
                text[x].encode("cp1252").decode("raw_unicode_escape").encode("utf-8").decode("utf-8")
        else:
            text = open(path, "r").read().encode("cp1252").decode("raw_unicode_escape").encode("utf-8").decode("utf-8")
    except:
        traceback.print_exc()

    return text


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


# ================ END OF HELPERS ================ #
def error_handler(bot, update, error):
    bot.send_message(chat_id=update.message.chat_id, text="_An error occured! Please try again!_",
                     parse_mode='Markdown')
    info = "User {user} sent {message}".format(user=update.message.from_user.username, message=update.message.text)
    logger.info(info)

    for id in admin_id:
        bot.send_message(chat_id=id, text="*\U00002757 Error occured! \U00002757    *", parse_mode='Markdown')
        bot.send_message(chat_id=id,
                         text="Cause: " + info + "\nError: " + str(error) + "\n***View logs for more details***")
    print("==================== ERROR ====================")
    traceback.print_exc()
    print("===============================================\n")


if __name__ == '__main__':
    main()
