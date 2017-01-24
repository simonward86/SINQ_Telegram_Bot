import sys

from datetime import datetime, timedelta

if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3.")

from telegram.ext import Updater, Job, CommandHandler, InlineQueryHandler, MessageHandler, Filters
from telegram import Bot, InlineQueryResultPhoto, InputTextMessageContent, ChatAction
import logging
import os
import json
import threading
import random

import Whitelist
import Preferences
import Locales
import DataSource

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

import urllib.request

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

prefs = Preferences.UserPreferences()
lang  = Locales.Locales()
connections = dict()
connections_blocked = dict()

jobs = dict()
locks = dict()

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def cmd_help(bot, update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (help).' % (user_name, chat_id))
        return

    logger.info('[%s@%s] Sending help text.' % (user_name, chat_id))

    text = lang.get_string(prefs.get(chat_id).get('language'), 3)
    bot.sendMessage(chat_id, text)
    bot.sendMessage(chat_id, text='/lang [%s]' % ', '.join(lang.locales))


def cmd_start(bot, update, args):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return

    pref = prefs.get(chat_id)
    r = pref.load()

    if r & len(args)==0:
        args = pref.get('connection')
        if args is not None:
            args = args.split('.')
            args = [args[0]] # This should give computer name
    cmd_connect(bot,update,args)
    cmd_help(bot, update)


def cmd_save(bot, update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (save).' % (user_name, chat_id))
        return

    pref = prefs.get(chat_id)

    logger.info('[%s@%s] Save.' % (user_name, chat_id))
    pref.set_preferences()
    bot.sendMessage(chat_id, text='Preferences have been saved.')

def cmd_plot_current(bot,update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return

    pref = prefs.get(chat_id)

    # if not connections[pref.get('connection')].is_connected:
    #     connections[pref.get('connection')] = DataSource.TelnetSICS(pref.get('connection'))
    #     connections[pref.get('connection')].connect()
    #     connections[pref.get('connection')].login()
    #     if not connections[pref.get('connection')].is_connected:
    #         bot.sendMessage(chat_id, text=lang.get_string(prefs.get(chat_id).get('language'), 2) % pref.get('connection'))

    bot.sendChatAction(chat_id,ChatAction.UPLOAD_PHOTO)
    allOK = make_figure(pref)
    if allOK:
        bot.sendPhoto(chat_id,photo=open(os.path.join(os.path.dirname(sys.argv[0]), "%s.png" % pref.get('connection')),'rb'))
    else:
        bot.sendMessage(chat_id,text="Something has gone wrong. Possibly unsuported machine :-(")

def make_figure(pref,machine = None):

    if machine is not None:
        machine = '%s.psi.ch' % machine
        if machine not in connections:
            connections[machine] = DataSource.TelnetSICS(machine)
            connections[machine].connect()
            connections[machine].login()
            if pref is None:
                pref = prefs.get('TEMP')
            pref.set('connection', machine)

    if (('rita2' in pref.get('connection')) and pref.get('is2d')) or (('sans' in pref.get('connection')) or ('sans2' in pref.get('connection'))):
        # We make a 2D Plot
        zdata =  connections[pref.get('connection')].uu_val_comp('hmframe 0')
        nrows, ncols = zdata[0], zdata[1]
        grid = np.array(zdata[2:]).reshape((nrows, ncols))
        fig, ax = plt.subplots(nrows=1, ncols=1)  # create figure & 1 axis
        cax = ax.imshow(grid, extent=(0, ncols, 0, nrows),
                   interpolation='nearest', cmap=cm.inferno)
        cbar = fig.colorbar(cax)
        title = connections[pref.get('connection')].val('sample')
        ax.set_title(title)
        fig.savefig(os.path.join(
            os.path.dirname(sys.argv[0]), "%s.png" % pref.get('connection')))  # save the figure to file
        plt.close(fig)  # close the figure
        return True

    if ('hrpt' in pref.get('connection')) or ('dmc' in pref.get('connection')):
        # We have the special powder case......
        ydata = connections[pref.get('connection')].uu_val('gethm')
        xdata = connections[pref.get('connection')].get_powder_x(len(ydata))
        fig, ax = plt.subplots(nrows=1, ncols=1)  # create figure & 1 axis
        ax.plot(xdata, ydata)
        title = connections[pref.get('connection')].val('sample')
        ax.set_title(title)
        ax.set_xlabel('a4')
        ax.set_ylabel('Counts')
        fig.savefig(os.path.join(
        os.path.dirname(sys.argv[0]), "%s.png" % pref.get('connection')))  # save the figure to file
        plt.close(fig)  # close the figure
        return True

    scan_var = 'iscan'
    try:
        ydata = connections[pref.get('connection')].uu_val(' '.join([scan_var,'uucounts']))
    except:
        scan_var = 'xxxscan'
        ydata = connections[pref.get('connection')].uu_val(' '.join([scan_var,'uucounts']))

    scanvars = connections[pref.get('connection')].transact(' '.join([scan_var,'noscanvar']))
    scanvars = scanvars.split('=')
    scanvars = int(scanvars[1])

    xdata = []
    for i in range(0,scanvars,1):
        scan_ch = connections[pref.get('connection')].transact(' '.join([scan_var, 'getvarpar', str(i)]))
        scan_ch = scan_ch.split(' = ')
        if float(scan_ch[2]) > 0:
            xdata_s = connections[pref.get('connection')].transact(' '.join([scan_var, 'getvardata', str(i)]))
            xdata_s = xdata_s.split('{ ')
            xdata_s = xdata_s[1:]
            xdata = list(map(lambda x: float(x[:-3]), xdata_s))
            break

    fig, ax = plt.subplots( nrows=1, ncols=1 )  # create figure & 1 axis
    ax.errorbar(xdata, ydata,yerr=np.sqrt(ydata))
    title = connections[pref.get('connection')].transact(' '.join(['lastcommand']))
    if 'ERROR' in title:
        title = connections[pref.get('connection')].transact(' '.join(['scaninfo']))
        title = title.split(',')
        title = title[len(title) - 1][1:]
    else:
        title = title.split('=')
        title = title[1]
    ax.set_title(title)
    ax.set_xlabel(scan_ch[0].split('%s.'%scan_var)[1])
    ax.set_ylabel('Counts')
    fig.savefig(os.path.join(
        os.path.dirname(sys.argv[0]), "%s.png" % pref.get('connection')))   # save the figure to file
    plt.close(fig)    # close the figure
    return True

def cmd_send(bot, update, args):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return

    pref = prefs.get(chat_id)

    if len(args) <= 0:
        bot.sendMessage(chat_id, text="Send me a command!")
    # if not connections[pref.get('connection')].is_connected:
    #     connections[pref.get('connection')] = DataSource.TelnetSICS(pref.get('connection'))
    #     connections[pref.get('connection')].connect()
    #     connections[pref.get('connection')].login()
    #     if not connections[pref.get('connection')].is_connected:
    #         bot.sendMessage(chat_id, text=lang.get_string(prefs.get(chat_id).get('language'), 2) % pref.get('connection'))

    r = connections[pref.get('connection')].transact(' '.join(args))
    bot.sendMessage(chat_id, text=r)
    logger.info('[%s@%s] Message Sent.' % (user_name, chat_id))


def cmd_status(bot,update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return
    pref = prefs.get(chat_id)
    bot.sendChatAction(chat_id,ChatAction.TYPING)
    try:
        with urllib.request.urlopen("http://lns00.psi.ch/cgi-bin/hipatext.cgi") as response:
            html = response.read()
        with urllib.request.urlopen("http://lns00.psi.ch/cgi-bin/hipaflux.cgi") as response:
            html += response.read()
    except urllib.request.URLError as e:
        html = b'Can not get SINQ status\n'
    # if not connections[pref.get('connection')].is_connected:
    #     connections[pref.get('connection')] = DataSource.TelnetSICS(pref.get('connection'))
    #     connections[pref.get('connection')].connect()
    #     connections[pref.get('connection')].login()
    #     if not connections[pref.get('connection')].is_connected:
    #         bot.sendMessage(chat_id, text=lang.get_string(prefs.get(chat_id).get('language'), 2) % pref.get('connection'))
    html += str.encode('%s is: %s\n' % (pref.get('connection'), connections[pref.get('connection')].val('status')))
    bot.sendMessage(chat_id,text=html.decode("utf-8"))

def cmd_ask_updates(bot,update,args,job_queue):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return

    if chat_id in locks:
        bot.sendMessage(chat_id,'You already have an update. Use the clear command')
        return

    if len(args) == 0:
        bot.sendMessage(chat_id,'You need to supply an object to be interested in')
        return

    pref = prefs.get(chat_id)
    connect_locked(chat_id,pref.get('connection'))
    connections_blocked[chat_id][pref.get('connection')].writeline(' '.join([args[0],'interest']))
    if len(args)>1:
        add_job(bot, update, job_queue, int(args[1]))
    else:
        add_job(bot, update, job_queue)

def cmd_send_erros(bot,update,job_queue):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return

    if chat_id in locks:
        bot.sendMessage(chat_id,'You already have an update. Use the clear command')
        return

    pref = prefs.get(chat_id)
    connect_locked(chat_id,pref.get('connection'))
    try:
        if chat_id not in jobs:
            job = Job(alarm_error, 5, repeat=True, context=(chat_id, "Other"))
            # Add to jobs
            jobs[chat_id] = job
            job_queue.put(job)

            # User dependant
            # if chat_id not in sent:
            #     sent[chat_id] = dict()
            if chat_id not in locks:
                locks[chat_id] = threading.Lock()
            text = 'Set-up Error updates :-)'
            bot.sendMessage(chat_id, text)
    except Exception as e:
        logger.error('[%s@%s] %s' % (user_name, chat_id, repr(e)))

def cmd_stop_send_errors(bot, update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (clear).' % (user_name, chat_id))
        return

    pref = prefs.get(chat_id)

    if chat_id not in jobs:
        bot.sendMessage(chat_id, text='You do not have a running error listner')
        return

    # Remove from jobs
    job = jobs[chat_id]
    job.schedule_removal()
    del jobs[chat_id]
    # Remove from locks
    del locks[chat_id]

    connections_blocked[chat_id][pref.get('connection')].writeline('quit')
    connections_blocked[chat_id][pref.get('connection')].disconnect()
    del connections_blocked[chat_id][pref.get('connection')]

def alarm_error(bot, job):
    chat_id = job.context[0]
    logger.info('[%s] Checking error alarm.' % chat_id)
    pref = prefs.get(chat_id)
    start_date = datetime.now() + timedelta(seconds=-4.9)
    text = connections_blocked[chat_id][pref.get('connection')].transact('showlog -c error -f "%s"' % str(start_date))
    if len(text) > 0:
        if text[0] is not '' and text is not '\n': # For some reason we get an empty response
            bot.sendMessage(chat_id, text=text)

def cmd_clear_updates(bot, update,args):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (clear).' % (user_name, chat_id))
        return

    pref = prefs.get(chat_id)

    if chat_id not in jobs:
        bot.sendMessage(chat_id, text='You do not have a running interest')
        return

    # Remove from jobs
    job = jobs[chat_id]
    job.schedule_removal()
    del jobs[chat_id]
    # Remove from locks
    del locks[chat_id]

    connections_blocked[chat_id][pref.get('connection')].writeline(' '.join([args[0], 'uninterest']))
    connections_blocked[chat_id][pref.get('connection')].writeline('quit')
    connections_blocked[chat_id][pref.get('connection')].disconnect()
    del connections_blocked[chat_id][pref.get('connection')]

def cmd_connect(bot,update,args):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return

    pref = prefs.get(chat_id)
    if len(args) <= 0:
        args = ['tasp']
    machine = '%s.psi.ch' % args[0]
    if machine not in connections:
        connections[machine] = DataSource.TelnetSICS(machine)
    else:
        if not connections[machine].is_connected:
            connections[machine] = DataSource.TelnetSICS(machine)

    connections[machine].connect()
    connections[machine].login()
    pref.set('connection', machine)

    if not connections[machine].is_connected:
        bot.sendMessage(chat_id, text=lang.get_string(prefs.get(chat_id).get('language'), 2) % machine)
        return
    else:
        bot.sendMessage(chat_id, text=lang.get_string(prefs.get(chat_id).get('language'), 1) % machine)
    logger.info('[%s@%s] Starting.' % (user_name, chat_id))

def connect_locked(chat_id,machine):
    if chat_id not in connections_blocked:
        connections_blocked[chat_id] = dict()
    if machine not in connections_blocked[chat_id]:
        connections_blocked[chat_id][machine] = DataSource.TelnetSICS(machine)
        connections_blocked[chat_id][machine].connect()
        connections_blocked[chat_id][machine].login()
    else:
        if not connections_blocked[chat_id][machine].is_connected:
            connections_blocked[chat_id][machine] = DataSource.TelnetSICS(machine)
            connections_blocked[chat_id][machine].connect()
            connections_blocked[chat_id][machine].login()

def cmd_beam_status(bot,update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return
    bot.sendPhoto(chat_id,photo='http://gfa-status.web.psi.ch/hipa-info-1024x768.png')

def cmd_2d(bot,update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return
    pref = prefs.get(chat_id)
    if pref.get('is2d'):
        bot.sendMessage(chat_id, text='Sending 2d images is: OFF')
        pref.set('is2d',False)
    else:
        bot.sendMessage(chat_id, text='Sending 2d images is: ON')
        pref.set('is2d', True)

def cmd_sea(bot,update):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return
    pref = prefs.get(chat_id)
    sea = DataSource.SEA(connections[pref.get('connection')])
    text = sea.makeStatement()
    bot.sendMessage(chat_id,text=text)

def cmd_getlogs(bot,update,args):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    if not whitelist.is_whitelisted(user_name):
        logger.info('[%s@%s] User blocked (start).' % (user_name, chat_id))
        return
    pref = prefs.get(chat_id)
    text = connections_blocked[chat_id][pref.get('connection')].transact('showlog -c error -f "%s"' % str(start_date))


# Functions
def error(bot, update, errors):
    logger.warn('Update "%s" caused error "%s"' % (update, errors))

def alarm(bot, job):
    chat_id = job.context[0]
    logger.info('[%s] Checking alarm.' % chat_id)
    pref = prefs.get(chat_id)
    text = connections_blocked[chat_id][pref.get('connection')].getline()
    if len(text) > 0 and text is not 'OK\n' and text is not '\n':
        bot.sendMessage(chat_id, text=text)

def add_job(bot, update, job_queue,timestep = 30):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.username
    logger.info('[%s@%s] Adding job.' % (user_name, chat_id))

    try:
        if chat_id not in jobs:
            job = Job(alarm, timestep, repeat=True, context=(chat_id, "Other"))
            # Add to jobs
            jobs[chat_id] = job
            job_queue.put(job)

            # User dependant
            # if chat_id not in sent:
            #     sent[chat_id] = dict()
            if chat_id not in locks:
                locks[chat_id] = threading.Lock()
            text = 'Set-up updates :-)'
            bot.sendMessage(chat_id, text)
    except Exception as e:
        logger.error('[%s@%s] %s' % (user_name, chat_id, repr(e)))

def read_config():
    config_path = os.path.join(
        os.path.dirname(sys.argv[0]), "config-bot.json")
    logger.info('Reading config: <%s>' % config_path)
    global config
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            config = json.loads(f.read())
    except Exception as e:
        logger.error('%s' % (repr(e)))
        config = {}
    report_config()

def report_config():
    admins_list = config.get('LIST_OF_ADMINS', [])
    tmp = ''
    for admin in admins_list:
        tmp = '%s, %s' % (tmp, admin)
    tmp = tmp[2:]
    logger.info('LIST_OF_ADMINS: <%s>' % tmp)
    logger.info('TELEGRAM_TOKEN: <%s>' % (config.get('TELEGRAM_TOKEN', None)))

def inline_beam_status(bot, update):
    query = update.inline_query.query
    if not query:
        return
    results = list()
    results.append(
        InlineQueryResultPhoto(
            id=random.randint(0, 1E4),
            title='Current beam status',
            photo_url= 'http://gfa-status.web.psi.ch/hipa-info-1024x768.png',
            thumb_url = 'http://gfa-status.web.psi.ch/hipa-info-1024x768.png'
        )
    )
    bot.answerInlineQuery(update.inline_query.id, results)

def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")

def main():
    logger.info('Starting...')
    read_config()

    global whitelist
    whitelist = Whitelist.Whitelist(config)

    global dataSource
    dataSource = DataSource.TelnetSICS(None)

    # ask it to the bot father in telegram
    token = config.get('TELEGRAM_TOKEN', '')
    updater = Updater(token)
    b = Bot(token)
    logger.info("BotName: <%s>" % b.name)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", cmd_start, pass_args=True))
    dp.add_handler(CommandHandler("cmd", cmd_send, pass_args=True))
    dp.add_handler(CommandHandler("help", cmd_help))
    dp.add_handler(CommandHandler("save", cmd_save))
    dp.add_handler(CommandHandler("beam", cmd_beam_status))
    dp.add_handler(CommandHandler("interest", cmd_ask_updates, pass_args=True, pass_job_queue=True))
    dp.add_handler(CommandHandler("send_errors", cmd_send_erros, pass_job_queue=True))
    dp.add_handler(CommandHandler("stop_errors", cmd_stop_send_errors))
    dp.add_handler(CommandHandler("uninterested", cmd_clear_updates, pass_args=True))
    dp.add_handler(CommandHandler("connect", cmd_connect, pass_args=True))
    dp.add_handler(CommandHandler("current", cmd_plot_current))
    dp.add_handler(CommandHandler("log",cmd_getlogs,pass_args=True))
    dp.add_handler(CommandHandler('2d',cmd_2d))
    dp.add_handler(CommandHandler('status',cmd_status))
    dp.add_handler(CommandHandler('sea',cmd_sea))
    dp.add_handler(InlineQueryHandler(inline_beam_status))
    dp.add_handler(MessageHandler([Filters.command], unknown))

    # log all errors
    dp.add_error_handler(error)

    # add the configuration to the preferences
    prefs.add_config(config)

    # Start the Bot
    updater.start_polling()

    logger.info('Started!')
    # Block until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

    # t = DataSource.TelnetConn('tasp.psi.ch')
    # r = t.send_cmd('LS')
    #
    # print('\n'.join(r))