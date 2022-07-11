import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция для отправки сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        message = f'Не могу отправить сообщение в telegram: {error}'
        logger.error(message)
    else:
        logger.info('Успешная отправка сообщения в telegram')


def get_api_answer(current_timestamp):
    """Функция получающая ответ от api."""
    params = {'from_date': current_timestamp}
    try:
        homework_response = requests.get(
            url=ENDPOINT, headers=HEADERS, params=params
        )
    except requests.ConnectionError as error:
        message = f'Ошибка подключения: {error}'
        logger.error(message)
    if homework_response.status_code != HTTPStatus.OK.value:
        logger.error(homework_response.status_code)
        raise requests.HTTPError('Http ответ не равен 200')
    try:
        serialized_response = homework_response.json()
    except json.decoder.JSONDecodeError as error:
        message = f'Не могу сериализовать в json: {error}'
        logger.error(message)
    return serialized_response


def check_response(response):
    """Ответ на проверку функции."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        message = f'Ответ не содержит необходимых ключей: {error}'
        logger.error(message)
        raise KeyError(message)
    if not isinstance(homeworks, list):
        logger.error('Домашнее задание неправильного типа')
        raise TypeError('Домашнее задание неправильного типа')
    if not homeworks:
        logger.error(homeworks)
        raise KeyError('Домашнее задание пусто')
    return homeworks


def parse_status(homework):
    """Проверьте статус домашнего задания."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        message = f'Ответ не содержит необходимых ключей: {error}'
        logger.error(message)
        raise KeyError('Ответ не содержит необходимых ключей')
    else:
        if homework_status in HOMEWORK_STATUSES:
            verdict = HOMEWORK_STATUSES[homework_status]
            return (
                f'Изменился статус проверки работы'
                f' "{homework_name}". {verdict}'
            )
        else:
            logger.error(homework_status)
            raise Exception('Статус домашнего задания не определен')


def check_tokens():
    """Проверьте доступность токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
    current_timestamp = int(time.time())
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except Exception as error:
        message = f'БОТ не инициализирован: {error}'
        logger.error(message)
    else:
        return
    last_result = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            verdict = parse_status(homeworks[0])
            logger.info(verdict)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        else:
            if last_result == verdict:
                logger.info('Не изменится')
            else:
                last_result = verdict
                send_message(bot, verdict)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
