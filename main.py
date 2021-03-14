import sys
import yaml
import json
import requests
import logging

from datetime import datetime, timedelta


def setup_logger():
    logger = logging.getLogger('Lotto')

    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


class LottoTransaction:
    def __init__(self, id, product, amount, time_local, time_utc, type):
        self.id = id
        self.product = product
        self.amount = amount
        self.time_local = time_local
        self.time_utc = time_utc
        self.type = type


def request_get(uri):
    while True:
        try:
            cookies = {'GK_AUTHE': config['cookies']['gk_authe'],
                       'GK_SERV_gk_GMSDefaultService': config['cookies']['gk_serv']}

            logger.debug("Requesting URI `{}`".format(uri))
            response = requests.get(uri, cookies=cookies)
            logger.debug("Response status codes `{}`".format(response.status_code))

            return response
        except Exception as err:
            logger.error("Request failed with error: {}".format(err))
            continue


def get_transactions(bod_timestamp, eod_timestamp):
    dates_arguments = "date-from={}&date-to={}".format(bod_timestamp, eod_timestamp)
    logger.debug("Date range request arguments, {}".format(dates_arguments))

    uri = "{0}?{1}&{2}".format(config['api']['v1']['transactions'], config['api']['v1']['searchTerms'], dates_arguments)
    logger.debug("Prepared request URI, {}".format(uri))

    response = request_get(uri)

    return response


def validate_json(data):
    try:
        logger.debug("Trying validate data as `json`".format(data))
        return json.loads(data)
    except Exception as err:
        logger.error("Failed validate as `json`, {}".format(err))
        return False


def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(int(timestamp) / 1000).strftime("%Y-%m-%d %H:%M:%S")


def parse_lotto_transactions(json_data):
    list = []
    i = 1

    try:
        for t in json_data['transactions']:
            logger.debug("Parsing lotto transaction `#{}`".format(i))
            list.append(LottoTransaction(t['id'], t['product'], t['transactionAmount'], t['transactionTimeLocal'],
                                         t['transactionTimeUTC'], t['lotteryTransactionType']))
            i += 1

        return list
    except Exception as err:
        logger.error("Failed parse transactions, `{}`".format(err))
        return False


def parse_transactions(data):
    parsed_data = validate_json(data)

    if parsed_data != False:
        logger.debug("Data validated as `json`")
        return parse_lotto_transactions(parsed_data)
    else:
        return False


def setup_bod(date):
    return date.replace(hour=0, minute=0, second=0, microsecond=0)


def setup_eod(date):
    return date.replace(hour=23, minute=59, second=59, microsecond=999999)


config = yaml.safe_load(open("config.yml"))
logger = setup_logger()

transactions = []

start_date = setup_bod(datetime(2020, 1, 1))
end_date = setup_bod(datetime.now()) # setup_bod(datetime(2020, 7, 1))

logger.debug("Start date is `{}`".format(start_date))
logger.debug("End date is `{}`".format(end_date))

while True:
    bod_date = setup_bod(start_date)
    logger.debug("Begin of day is `{}`".format(bod_date))
    eod_date = setup_eod(start_date)
    logger.debug("End of day is `{}`".format(eod_date))

    bod_timestamp = int(datetime.timestamp(bod_date)) * 1000
    logger.debug("Begin of day timestamp is `{}`".format(bod_timestamp))
    eod_timestamp = int(datetime.timestamp(eod_date)) * 1000
    logger.debug("End of day timestamp is `{}`".format(eod_timestamp))

    response = get_transactions(bod_timestamp, eod_timestamp)

    if response.status_code == 200:
        transactions += parse_transactions(response.text)
    else:
        print("Response != 200: {}".format(response.status_code))

    if start_date == end_date:
        break

    start_date += timedelta(days=1)

wager_amount = 0
validation_amount = 0

print("\n")
print("ID\t\tProduct\t\tAmount\tDate\t\t\tType")
print("-----------------------------------------------------------------------------")

for t in transactions:
    if t.type == "WAGER":
        wager_amount += t.amount
    elif t.type == "VALIDATION":
        validation_amount += t.amount

    print("{}\t{}\t\t{}\t{}\t{}".format(t.id, t.product, t.amount, timestamp_to_date(t.time_local), t.type))

print("\n")
print("Validation: {}".format(validation_amount / 100))
print("Wager\t: {}".format(wager_amount / 100))
