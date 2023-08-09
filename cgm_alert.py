#!/usr/bin/python3
"""
"2023-08-07T19:28:49.000Z"      1691436529000   127     "Flat"  "share2"
"""
"""
0        1         2         3         4         5         6         7         8
12345678901234567890123456789012345678901234567890123456789012345678901234567890
"""

import datetime
import logging
import json
import mysql.connector
import requests
import smtplib
import ssl
import sys
import traceback
import uuid

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mysql.connector import Error


with open('config.json', 'r') as fp:
    config = json.load(fp)

LOGLEVEL = config.get('LOGLEVEL', 'WARNING')

LOW_THRESHOLD = config.get('LOW_THRESHOLD', 80)
HIGH_THRESHOLD = config.get('HIGH_THRESHOLD', 200)
URGENT_LOW_THRESHOLD = config.get('URGENT_LOW_THRESHOLD', 55)

UNACKED_DELAY = config.get('UNACKED_DELAY', 300)
ACKED_DELAY = config.get('ACKED_DELAY', 1800)

SENDER_EMAIL = config.get('SENDER_EMAIL')
RECIPIENT_EMAIL = config.get('RECIPIENT_EMAIL', SENDER_EMAIL)

SMTP_HOST = config.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = config.get('SMTP_PORT', 587)
SMTP_USER = config.get('SMTP_USER', SENDER_EMAIL)
SMTP_PASS = config.get('SMTP_PASS', '')

DB_HOST = config.get('DB_HOST', 'localhost')
DB_NAME = config.get('DB_NAME', 'cgm_alert')
DB_USER = config.get('DB_USER', 'cgm_alert')
DB_PASS = config.get('DB_PASS', '')

# statuses
OK = 0
HIGH = 1
LOW = 2
URGENT_LOW = 3
UNKNOWN = 4

statuses = [
    'Normal',
    'High',
    'Low',
    'Urgent Low',
    'Unknown',
]

logging.basicConfig(
    level=LOGLEVEL,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
)
log = logging.getLogger(__name__)


def init_db():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
        )
    except Error as e:
        log.exception(f'Failed to connect to db: {e}')
        conn = None
    return conn


def select(query):
    if not query:
        raise AttributeError('Parameter query must be provided')
    conn = init_db()
    if not conn:
        raise RuntimeError('Unable to connect to the database')
    cursor = conn.cursor()
    cursor.execute(query)
    records = cursor.fetchall()
    cursor.close()
    return records


def okay_to_send(status):
    now = datetime.datetime.now().timestamp()
    now_minus_unacked_delay = now - UNACKED_DELAY
    now_minus_acked_delay = now - ACKED_DELAY
    prev_alert = select(
        f'SELECT timestamp, status_id, is_acked FROM tbl_alert ' +
        'ORDER BY timestamp DESC LIMIT 1'
    )
    if prev_alert:
        log.debug(f'prev_alert: {json.dumps(prev_alert)}')
        prev_timestamp = prev_alert[0][0]
        prev_status = prev_alert[0][1]
        prev_is_acked = (prev_alert[0][2] > 0)
        prev_status_name = statuses[prev_status]
    else:
        prev_timestamp = 0
        prev_status = OK
        prev_is_acked = False
        prev_status_name = status[prev_status]
    log.debug(f'now - prev_timestamp = {now - prev_timestamp}')
    log.debug(f'prev_status = {prev_status}, status = {status}')
    log.debug(f'prev_is_acked = {prev_is_acked}')
    log.debug(f'prev_status_name = {prev_status_name}')

    if prev_status != status:
        log.debug(
            f'Status has changed from {prev_status} ({prev_status_name}) ' +
            f'to {status} ({statuses[status]})'
        )
        return True
    else:
        if status == OK:
            log.debug('Status is unchanged and is OK')
            return False
        else:
            if not prev_is_acked:
                if now - prev_timestamp > UNACKED_DELAY:
                    log.debug(
                        'Status is not OK, it has not been acked, and it has ' +
                        f'been longer than {UNACKED_DELAY} seconds since ' +
                        'last alert'
                    )
                    return True
                else:
                    log.debug(
                        'Status is not OK, it has not been acked, but it has ' +
                        f'been less than {UNACKED_DELAY} seconds since last ' +
                        'alert'
                    )
                    return False
            else:
                if now - prev_timestamp > ACKED_DELAY:
                    log.debug(
                        'Status is not OK, it has been acked, and it has '+
                        f' been more than {ACKED_DELAY} seconds since last alert'
                    )
                    return True
                else:
                    log.debug(
                        'Status is not OK, it has been acked, and it has ' +
                        f'been less than {ACKED_DELAY} since last alert'
                    )
                    return False


def store_timestamp(status):
    now = datetime.datetime.now().timestamp()
    alert_uuid = uuid.uuid4()
    conn = init_db()
    if not conn:
        raise RuntimeError('Unable to connect to the database')
    query = \
        'INSERT INTO tbl_alert(timestamp, status_id, uuid, is_acked) ' + \
        f'VALUES({now}, {status}, \'{alert_uuid}\', 0)'
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    cursor.close()
    return alert_uuid


def alert(bg, status):
    if not okay_to_send(status):
        return
    text = f'{statuses[status]} - {bg}'
    log.info(text)
    alert_uuid = store_timestamp(status)
    message = MIMEMultipart('alternative')
    message['Subject'] = text
    message['From'] = SENDER_EMAIL
    message['To'] = RECIPIENT_EMAIL
    html = \
        f'<html><body><a href=\'https://cgm.jonheese.com/ack/{alert_uuid}\'>' + \
        f'{text}</a></body></html>'

    message.attach(MIMEText(text, 'plain'))
    message.attach(MIMEText(html, 'html'))

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(
            SENDER_EMAIL,
            RECIPIENT_EMAIL,
            message.as_string()
        )

def get_cgm_data():
    try:
        data = requests.get(
            'https://nightscout.jonheese.com/api/v1/entries?count=1'
        ).text.split()
    except:
        log.error(f'Error getting BG: {traceback.format_exc()}')

    if not data:
        return

    bg = int(data[2])
    if not bg:
        log.error(f'BG not detected: {data}')
        return
    log.info(f'BG is {bg}')

    if bg <= URGENT_LOW_THRESHOLD:
        alert(bg=bg, status=URGENT_LOW)
    elif bg <= LOW_THRESHOLD:
        alert(bg=bg, status=LOW)
    elif bg >= HIGH_THRESHOLD:
        alert(bg=bg, status=HIGH)
    else:
        alert(bg=bg, status=OK)


if __name__ == '__main__':
    get_cgm_data()
