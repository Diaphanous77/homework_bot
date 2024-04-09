import logging
import sys
import os
import time

import requests
from http import HTTPStatus
import telegram

from dotenv import load_dotenv
import exceptions


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler('main.log', encoding='UTF-8'),
              logging.StreamHandler(sys.stdout)]
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов."""
    message = 'Отсутствует обязательная переменная окружения:'
    token_dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for name, value in token_dict.items():
        if value is None:
            logging.critical(f'{message} {name}')
            raise exceptions.TokensIsNoneException(f'{message} {name}')
    return True


def send_message(bot, message):
    """Отправка сообщения в чат."""
    try:
        logging.info('Отправка сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except exceptions.TelegramErrorException as error:
        raise exceptions.TelegramErrorException('Ошибка отправки '
                                                f'сообщения {error}')
    else:
        logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Получение статуса домашней работы."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.IncorrectResponseCodeException(
                f'Нет ответа от сервера. Код ответа {response.status_code}'
            )
        return response.json()
    except Exception:
        raise exceptions.IncorrectResponseCodeException(
            'Сбой в работе программы: '
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}')


def check_response(response):
    """Проверка правильности ответа."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в ответе от API')
    if 'homeworks' not in response or 'current_date' not in response:
        raise ValueError('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    return homeworks


def parse_status(homework):
    """Парсинг статуса."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name"')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise ValueError('Неожиданный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    prev_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            new_homework = check_response(response)
            if new_homework:
                message = parse_status(new_homework[0])
            else:
                message = 'Статус работы не изменился'
            if message != prev_message:
                send_message(bot, message)
                prev_message = message
            else:
                logging.info(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
