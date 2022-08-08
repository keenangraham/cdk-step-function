import os

import requests


SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']


def handler(event, context):
    print(SLACK_WEBHOOK_URL)
    print(event)
    print(context)
    r = requests.post(
        SLACK_WEBHOOK_URL,
        json={
            'text': event['details']['text']
        }
    )
    print(r)
