import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, [%(levelname)s], %(message)s'
)
handler.setFormatter(formatter)


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
    """Отправка сообщения в телеграм."""
    logger.info('Сообщение будет отправлено в телеграм')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise (
            f'При отправке сообщения возникла ошибка: {error}'
        )
    else:
        logger.info('Сообщение успешно отправлено')


def get_api_answer(current_timestamp):
    """Отправляем get-запрос к эндпоинту и получаем ответ."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise (
            f'При отправке сообщения возникла ошибка: {error}'
        )
    if response.status_code == requests.codes.ok:
        logger.info(f'Запрос к адресу {ENDPOINT} успешно отправлен')
        return response.json()
    elif response.status_code != requests.codes.ok:
        raise (f'Запрос по адресу {ENDPOINT} недоступен. '
               f'Код ошибки: {response.status_code}')


def check_response(response):
    """Проверяем что полученный ответ приведен к типам данных Python."""
    if not (isinstance(response, dict)):
        raise TypeError(
            f"Тип данных не соответсвует ожидаемым. "
            f"Ожидается тип данных: {dict}. Получен: {type(response)} ")
    elif len(response['homeworks']) == 0:
        raise IndexError('Пустой список домашних работ')
    elif not (isinstance(response['homeworks'], list)):
        raise TypeError(f'Тип данных не соответсвует ожидаемым. '
                        f'Ожидается тип данных: {list}. '
                        f'Получен: {type(response["homeworks"])}')
    else:
        return response['homeworks'][0]


def parse_status(homework):
    """Получаем название и статус домашней работы."""
    if ('homework_name' or 'status') not in homework:
        raise KeyError("homework_name или status отсутствуют в homework")

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise (f'Статус домашней работы {homework_status} не определен.')


def check_tokens():
    """Проверяем доступность токенов."""
    token_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if all(token_list):
        logger.info('Необходимые токены доступны')
        return all(token_list)
    else:
        if PRACTICUM_TOKEN is None:
            logger.critical(
                f'Отсутсвует токен: '
                f'{PRACTICUM_TOKEN}. Работы программы остановлена')
        if TELEGRAM_TOKEN is None:
            logger.critical(
                f'Отсутсвует токен: '
                f'{TELEGRAM_TOKEN}. Работы программы остановлена')
        if TELEGRAM_CHAT_ID is None:
            logger.critical(
                f'Отсутсвует токен: '
                f'{TELEGRAM_CHAT_ID}. Работы программы остановлена')
        return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Ошибка при проверке токенов')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_error = ''
    message_bot = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            if len(response['homeworks']) != 0:
                message = parse_status((check_response(response)))
                if message != message_bot:
                    send_message(bot=bot, message=message)
                    message_bot = message
                logger.debug('Статус домашней работы не изменился')
            check_response(response)
        except Exception as error:
            logger.error(f'В работе бота выявлена ошибка {error}')
            message = f'Сбой в работе программы: {error}'
            if message != message_error:
                send_message(bot, message)
                message_error = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='botlog.log',
        format='%(asctime)s, [%(levelname)s], %(message)s'
    )

    main()
