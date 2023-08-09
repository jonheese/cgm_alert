#!/usr/bin/python3

import json
import mysql.connector
import sys
import uuid

from flask import Flask
from mysql.connector import Error

try:
    with open('config.json', 'r') as fp:
        config = json.load(fp)
except:
    print(
        'File config.json is missing. ' +
        'Did you copy config-dist.json to config.json?'
    )
    sys.exit(0)

LOGLEVEL = config.get('LOGLEVEL', 'WARN')
DB_HOST = config.get('DB_HOST', 'localhost')
DB_NAME = config.get('DB_NAME', 'cgm_alert')
DB_USER = config.get('DB_USER', 'cgm_alert')
DB_PASS = config.get('DB_PASS', '')

app = Flask(__name__)
mysql_params = {
    'host': DB_HOST,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASS,
}


@app.route('/ack/<alert_uuid>', methods=['GET'])
def ack(alert_uuid):
    if not alert_uuid:
        raise AttributeError('Parameter alert_uuid must be provided')
    html = 'Unknown'
    query = f'SELECT COUNT(id) from tbl_alert WHERE uuid = \'{alert_uuid}\''
    conn = mysql.connector.connect(**mysql_params)
    cursor = conn.cursor()
    app.logger.info(f'Query: {query}')
    cursor.execute(query)
    count = int(cursor.fetchall()[0][0])
    if count > 0:
        query = f'UPDATE tbl_alert SET is_acked = 1 WHERE uuid = \'{alert_uuid}\''
        cursor = conn.cursor()
        app.logger.info(f'Query: {query}')
        cursor.execute(query)
        conn.commit()
        html = 'Acked.'
    else:
        html = 'Error'
    return html


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5003')
