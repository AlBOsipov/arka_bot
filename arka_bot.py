import os
import requests
import xmltodict
import logging

from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          CallbackContext, Filters)

from dotenv import load_dotenv
from yandex_errors_dict import ya_error_lib

load_dotenv()

logging.basicConfig(
    filename='app.log',  # Имя файла для записи логов
    level=logging.INFO,  # Уровень логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

GREEN_CHECKMARK = "✅"
RED_CROSS = "❌"

TELEGRAM_TOKEN_AVITO = os.getenv('TELEGRAM_TOKEN_AVITO')

AVITO_CLIENT_ID = os.getenv('AVITO_CLIENT_ID')
AVITO_CLIENT_SECRET = os.getenv('AVITO_CLIENT_SECRET')
AVITO_ID_COMPANY = os.getenv('AVITO_ID_COMPANY')

TOKEN_CIAN = os.getenv('TOKEN_CIAN')

TOKEN_DOMCLICK = os.getenv('TOKEN_DOMCLICK')
DOMCLICK_ID_COMPANY = os.getenv('DOMCLICK_ID_COMPANY')

YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')
YANDEX_X_TOKEN = os.getenv('YANDEX_X_TOKEN')
YANDEX_FEED_ID = os.getenv('YANDEX_FEED_ID')


URL_GET_AVITO_TOKEN = 'https://api.avito.ru/token/'
URL_GET_AVITO_ID_LISTING = 'https://api.avito.ru/autoload/v2/items/avito_ids?query='
URL_GET_AVITO_URL = f'https://api.avito.ru/core/v1/accounts/{AVITO_ID_COMPANY}/items/'
URL_GET_YANDEX_FEED = 'https://api.realty.yandex.net/2.0/crm/offers'
URL_GET_CIAN_FEED = 'https://public-api.cian.ru/v1/get-order'
URL_GET_DOMCLICK_REPORT = f'https://my.domclick.ru/api/v1/company/{DOMCLICK_ID_COMPANY}/report/'

# Глобальная переменная для хранения токена
global_token = None
global_id_avito = None


def get_new_token():
    """Обновление токена авито."""
    global global_token
    payload = {
        'grant_type': 'client_credentials',
        'client_id': AVITO_CLIENT_ID,
        'client_secret': AVITO_CLIENT_SECRET
    }
    response = requests.post(URL_GET_AVITO_TOKEN, data=payload)
    if response.status_code == 200:
        data = response.json()
        global_token = data.get('access_token')
        return True
    return False


def get_id_avito(user_input):
    """Получение id объекта авито по листингу."""
    global global_token, global_id_avito
    url = f'{URL_GET_AVITO_ID_LISTING}{user_input}'
    headers = {'Authorization': f'Bearer {global_token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        items = data.get('items')
        if items:
            global_id_avito = items[0].get('avito_id')
    else:
        logging.warning(
            "Ошибка при выполнении запроса на стороне Авито. Код ответа: %s",
            response.status_code)


def get_item_avito_status(global_avito_id):
    """Получаение статуса на авито."""
    global global_token
    url = f'{URL_GET_AVITO_URL}{global_avito_id}/'
    headers = {'Authorization': f'Bearer {global_token}'}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        status = data.get('status')
        if status == "active":
            return data.get('url')
        else:
            return None
    else:
        logging.warning(
            "Ошибка при выполнении запроса на стороне Авито. Код ответа: %s",
            response.status_code)
        return None


def handle_avito_input(
        update: Update, context: CallbackContext, user_input: str):
    """Получени ссылки с Авито."""
    global global_token
    if global_token is None:
        if not get_new_token():
            send_message(
                update, context,
                "Не удалось получить токен Avito. Попробуйте позже.")
            return

    get_id_avito(user_input)

    if global_id_avito:
        url = get_item_avito_status(global_id_avito)
        if url:
            send_message(
                update, context,
                f"{GREEN_CHECKMARK} Ваше объявление на Avito успешно "
                f"публикуется: {url}")
    else:
        send_message(
            update, context, f"{RED_CROSS} Объявление на Avito не найдено.")


def handle_cian_input(
        update: Update, context: CallbackContext, user_input: str):
    """Получени ссылки с Циан."""
    cian_headers = {'Authorization': f'Bearer {TOKEN_CIAN}'}
    cian_params = {"externalId": user_input}

    response_cian = requests.get(
        URL_GET_CIAN_FEED, headers=cian_headers, params=cian_params)
    data = response_cian.json()

    if (response_cian.status_code == 200 and
            "result" in data and "offers" in data["result"]):
        offers = data["result"]["offers"]

        found_cian_offer = False
        for offer in offers:
            if offer["externalId"] == user_input:
                found_cian_offer = True
                if offer["status"] == "Published":
                    url = offer["url"]
                    send_message(
                        update, context,
                        f"{GREEN_CHECKMARK} Ваше объявление на CIAN успешно "
                        f"публикуется: {url}")
                else:
                    error = offer.get("errors", "Неизвестная ошибка.")
                    send_message(
                        update, context, f"Есть ошибка на CIAN: {error}")
        if not found_cian_offer:
            send_message(
                update, context, f"{RED_CROSS} Объект не найден ЦИАН!")
    else:
        logging.warning(
            "Ошибка при выполнении запроса на стороне Циан. Код ответа: %s",
            response_cian.status_code)


def handle_yandex_input(
        update: Update, context: CallbackContext, user_input: str):
    """Получени ссылки с Яндекс."""
    yandex_headers = {
        'Authorization': f'OAuth {YANDEX_TOKEN}',
        'X-Authorization': f'Vertis {YANDEX_X_TOKEN}'
    }
    yandex_params = {"feedId": YANDEX_FEED_ID}

    response_yandex = requests.get(
        URL_GET_YANDEX_FEED, headers=yandex_headers, params=yandex_params)

    if response_yandex.status_code == 200:
        try:
            data = response_yandex.json()
            listing_snippets = data.get("listing", {}).get("snippets", [])
            found_ya_offer = False
            for snippet in listing_snippets:
                offer = snippet.get("offer", {})
                internal_id = offer.get("internalId")
                if internal_id == user_input and not offer.get("state"):
                    found_ya_offer = True
                    url = offer.get("url")
                    send_message(
                        update, context,
                        f"{GREEN_CHECKMARK} Ваше объявление "
                        f"на Яндекс успешно публикуется: {url}")
                elif internal_id == user_input and offer.get("state"):
                    state_errors = offer.get("state")
                    get_errors = state_errors.get("errors")
                    erros_list = []
                    for error in get_errors:
                        error_type = error["type"]
                        if ya_error_lib.get(error_type):
                            error_text = ya_error_lib[error_type]
                            erros_list.append(error_text)
                        else:
                            new_error = 'Неизвестная ошибка'
                            erros_list.append(new_error)
                    send_message(
                        update, context,
                        f"{RED_CROSS} Объект не публикуется на Яндекс! \n"
                        f"Причина: {', '.join(erros_list)}"
                    )
            if not found_ya_offer:
                send_message(
                    update, context, f"{RED_CROSS} Объект не найден Яндекс!")
        except ValueError:
            send_message(
                update, context, "Некорректный JSON-ответ от эндпоинта.")
    else:
        logging.warning(
            "Ошибка при выполнении запроса на стороне Циан. Код ответа: %s",
            response_yandex.status_code)
        send_message(
            update, context, "Ошибка при выполнении запроса на эндпоинт.")


def handle_domclick_input(
        update: Update, context: CallbackContext, user_input: str):
    """Получени ссылки с ДомКлик."""
    domclick_headers = {'Authorization': f'Token {TOKEN_DOMCLICK}'}

    domclick_response = requests.get(
        URL_GET_DOMCLICK_REPORT, headers=domclick_headers)

    if domclick_response.status_code == 200:
        xml_data = domclick_response.content
        data_dict = xmltodict.parse(xml_data)
        found_dom_offer = False

        for offer in data_dict['Report']['OfferList']['Offer']:
            external_id_node = offer.get('ExternalId')
            if (external_id_node == user_input and
                    offer['Status']['Code'] == 'published'):
                domclick_url_node = offer['Publication']['DomclickURL']
                discount_status = offer['DiscountStatus']['Code']
                if discount_status == 'rejected':
                    found_dom_offer = True
                    reason_discount_rejection = offer['DiscountStatus']['RejectionReasons']['Reason']['Descr']
                    send_message(
                        update, context,
                        f"ВНИМАНИЕ! Объект публикуется на ДомКлик, "
                        f"но нет скидки!\n"
                        f"Причина: {reason_discount_rejection}"
                    )
                else:
                    found_dom_offer = True
                    send_message(
                        update, context,
                        f"{GREEN_CHECKMARK} Объект успешно публикуется на "
                        f"Домклик: {domclick_url_node}"
                    )
        if not found_dom_offer:
            send_message(
                update, context, f"{RED_CROSS} Объект не найден ДомКлик!")
    else:
        logging.warning(
            "Ошибка при выполнении запроса на стороне ДомКлик. Код ответа: %s",
            domclick_response.status_code)
        send_message(
            update, context, f"Системная ошибка на стороне ДомКлик. \n"
            f"Держите код: {domclick_response.status_code} \n"
            f"Он вряд ли вам что-то скажет, но пусть будет."
        )


def start(update: Update, context: CallbackContext):
    send_message(update, context, "Введите номер листинга.")


def send_message(update: Update, context: CallbackContext, text: str):
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def is_valid_user_input(user_input: str) -> bool:
    """Проверка вводимого значения."""
    return user_input.isdigit() and len(user_input) == 5


def handle_user_input(update: Update, context: CallbackContext):
    """Менеджер проврки ссылок на площадках."""
    user_input = update.message.text.strip()
    logging.info("Пользователь ввел: %s", user_input)
    # logging.debug("Ответ от API: %s", data)

    if not is_valid_user_input(user_input):
        send_message(update, context, "Введите ровно 5 цифр листинга.")

    else:
        # Handle CIAN input
        handle_cian_input(update, context, user_input)

        # Handle Yandex input
        handle_yandex_input(update, context, user_input)

        # Handle DomClick input
        handle_domclick_input(update, context, user_input)

        # Handle Avito input
        handle_avito_input(update, context, user_input)


def main():
    updater = Updater(token=TELEGRAM_TOKEN_AVITO)

    updater.dispatcher.add_handler(CommandHandler('start', start))

    message_handler = MessageHandler(
        Filters.text & ~Filters.command, handle_user_input
    )
    updater.dispatcher.add_handler(message_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
