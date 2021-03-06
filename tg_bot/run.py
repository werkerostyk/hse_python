import re
import logging
import requests
from time import time
from gpt import conversation
from threading import Thread
from datetime import datetime
from dostoevsky.tokenization import RegexTokenizer
from dostoevsky.models import FastTextSocialNetworkModel
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters

BOT_TOKEN = ...
WEATHER_TOKEN = ...
CONVERSATION = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def start(update, context):
    greeting_message = 'Привет. Я бот, который может говорить погоду в Москве и Санкт-Петербурге (если вы спросите текстом) или погоду в вашем текущем местоположении (вам нужно отправить координаты). Напишите мне что-нибудь.'
    update.effective_chat.send_message(greeting_message)
    user_data = context.user_data
    if update.effective_message and update.effective_message.text:
        user_data['history'] = 'Сообщение: ' + update.effective_message.text + '\n'
        user_data['history'] += 'Ответ: ' + greeting_message + '\n'
    else:
        user_data['history'] = 'Сообщение: Привет.\n'
        user_data['history'] += 'Ответ: ' + greeting_message + '\n'

    return CONVERSATION


def say_hi(update, context):
    user_data = context.user_data
    if 'last_greeting' in user_data.keys() and time() - user_data['last_greeting'] < 60*60:
        update.effective_chat.send_message('Недавно же здоровались.')
        user_data['history'] += 'Недавно же здоровались.\n'
    else:
        update.effective_chat.send_message('Привет-привет.')
        user_data['history'] += 'Привет-привет.\n'
        user_data['last_greeting'] = time()

    return CONVERSATION


def end_conversation(update, context):
    # после выхода бот будет реагировать только на приветствие или /start
    update.effective_chat.send_message('До свидания.')
    user_data = context.user_data
    user_data.clear()

    return ConversationHandler.END


def print_weather(update, context, weather=None, city_id=0, use_old=False, location=False):
    if use_old:
        update.effective_chat.send_message(context.bot_data['message' + str(city_id)])
    else:
        message = ''
        for cast in weather:
            message += cast['dt_txt'] + ': ' + str(cast['main']['temp']) + ' °C, давление ' + str(cast['main']['pressure']) + ' мм рт. ст, влажность ' + str(cast['main']['humidity']) + '%, ' + cast['weather'][0]['description'] + '\n'
        update.effective_chat.send_message(message)
        if not location:
            context.bot_data['message' + str(city_id)] = message


def get_weather(update, context, city_id=0, location=False):
    user_data = context.user_data
    user_data['history'] += '*погода*\n'

    if location:
        pos = (update.effective_message.location.latitude, update.effective_message.location.longitude)
        ans = requests.get('http://api.openweathermap.org/data/2.5/forecast',
                           params={'lat': pos[0], 'lon': pos[1], 'cnt': 24, 'units': 'metric', 'lang': 'ru', 'appid': WEATHER_TOKEN})
        weather = ans.json()
        if weather['cod'] == '200':
            print_weather(update, context, weather['list'], location=True)
        else:
            update.effective_chat.send_message('Что-то не так с сервером погоды, попробуйте спросить меня позже.')

        return

    bot_data = context.bot_data
    if city_id in bot_data.keys() and time() - bot_data[city_id][0]['dt'] < 0:
        print_weather(update, context, city_id=city_id, use_old=True)
    else:
        ans = requests.get('http://api.openweathermap.org/data/2.5/forecast',
                           params={'id': city_id, 'cnt': 24, 'units': 'metric', 'lang': 'ru', 'appid': WEATHER_TOKEN})
        weather = ans.json()
        if weather['cod'] == '200':
            bot_data[city_id] = weather['list']
            print_weather(update, context, bot_data[city_id], city_id)
        else:
            update.effective_chat.send_message('Что-то не так с сервером погоды, попробуйте спросить меня позже.')


def spell_check(text):
    ans = requests.get('https://speller.yandex.net/services/spellservice.json/checkText',
                       params={'text': text, 'options': 512})
    if ans.status_code != 200:
        print('Что-то с сервером проверки правописания, возвращаю без проверки.')
        return text

    correction = ans.json()
    if correction:
        for d in correction:
            if d['code'] == 1:
                text = ''.join((text[:d['pos']], d['s'][0], text[d['pos']+d['len']:]))
            elif d['code'] == 2:
                pass
                # повтор слов почему-то не работает на стороне яндекса
            else:
                print('Слишком много ошибок.')

    return text


def user_message(update, context):
    print('{}: new user message'.format(datetime.now()))
    user_data = context.user_data

    if not update.effective_message or not update.effective_message.text:
        if update.effective_message.location:
            get_weather(update, context, location=True)
            return CONVERSATION
        print('We caught None')
        update.effective_chat.send_message('Я не понимаю, о чём вы говорите.')
        return CONVERSATION
    else:
        text = update.effective_message.text
        text = text.lower()
        text = spell_check(text)
        user_data['history'] += 'Сообщение: ' + text + '\n' + 'Ответ: '

    tokenizer = RegexTokenizer()
    model = FastTextSocialNetworkModel(tokenizer=tokenizer)
    sentiment = model.predict([text], k=2)

    if 'negative' in sentiment[0].keys() and sentiment[0]['negative'] > 0.3:
        update.effective_chat.send_message('Попробуйте быть повежливее.')
        user_data['history'] += 'Попробуйте быть повежливее.\n'
    elif re.search(r'(^|\s)погод(а|у)(\s|\,\s|\.|\?|\!|$)', text):
        msc = re.search(r'(\s|^)мск(\s|\,\s|\.|\?|\!|$)|(\s|^)москв(а|е)(\s|\,\s|\.|\?|\!|$)', text)
        spb = re.search(r'(\s|^)спб(\s|\,\s|\.|\?|\!|$)|(\s|^)питер(е|\s|\,\s|\.|\?|\!|$)|(\s|^)петербург(е|\s|\,\s|\.|\?|\!|$)|(\s|^)петроград(е|\s|\,\s|\.|\?|\!|$)|(\s|^)санкт(\s|\-)петербург(е|\s|\,\s|\.|\?|\!|$)', text)
        # "какая сегодня погода на улицах питерА/москвЫ?"
        if spb and not msc:
            get_weather(update, context, 498817)
        elif msc and not spb:
            get_weather(update, context, 524901)
        else:
            update.effective_chat.send_message('Не понимаю о чём вы, пишите конкретнее.')
            user_data['history'] += 'Не понимаю о чём вы, пишите конкретнее.\n'
    elif re.search(r'((\s|^)прив(\,\s|\.|\!|\s|$|ет*)|((\s|^)зд(о|а)ров(\,\s|\.|\!|\s|$|о|а|енько))|(здравствуй(\,\s|\.|\!|\s|$|те))|((\s|^)добр(ый\s|ое\s|ой\s|ого\s)(день|ночи|дня|утро|времени)))', text):
        # "здорово у тебя получается"
        # цитаты с приветствием
        return say_hi(update, context)
    elif re.search(r'((\s|^)пок(а|еда))|((\s|^)до(\s)(свидания|встречи))', text):
        # "покажет"
        return end_conversation(update, context)
    else:
        update.effective_chat.send_message('Я не понимаю, о чём вы говорите.')
        # update.effective_chat.send_message('Подождите примерно 30 секунд, пока я сгенерирую ответ.')
        # ans = conversation(user_data['history'])
        # update.effective_chat.send_message(ans)
        # user_data['history'] += ans + '\n'

    return CONVERSATION


if __name__ == '__main__':
    print('{}: script started'.format(datetime.now()))
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), MessageHandler(Filters.regex(re.compile(r'((\s|^)прив(\s|$|ет*)|((\s|^)зд(о|а)ров(\s|$|о|а|енько))|(здравствуй(\s|$|те))|((\s|^)добр(ый\s|ое\s|ой\s|ого\s)(день|ночи|дня|утро|времени)))', re.IGNORECASE)), start)],
        states={CONVERSATION: [MessageHandler(Filters.text, user_message), MessageHandler(Filters.location, user_message)]},
        fallbacks=[CommandHandler('end', end_conversation)])
    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    print('{}: bot started'.format(datetime.now()))
    updater.idle()
