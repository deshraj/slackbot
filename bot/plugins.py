from slackbot.bot import respond_to
from slackbot.bot import listen_to

from querystring_parser import parser
from os.path import splitext, basename

import re
import json
import pika
import uuid
import requests
import os
import shutil

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')
slack_rpc = SlackRpcClient()

from django.conf import settings

class SlackRpcClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host='localhost'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='rpc_queue',
                                   properties=pika.BasicProperties(
                                         reply_to = self.callback_queue,
                                         correlation_id = self.corr_id,
                                         ),
                                   body=str(n))
        while self.response is None:
            self.connection.process_data_events()
        return int(self.response)


@respond_to('', re.IGNORECASE)
def hi(message):
    print message._body
    message.reply('Hey, how are you ?')
    # react with thumb up emoji
    message.react('smile')


@respond_to('I love you')
def love(message):
    message.reply('I love you too!')


@listen_to('question:', re.IGNORECASE)
def grad_cam_vqa(message):
    print message._body
    body = message._body
    # download image on server
    image_url = body['file']['thumb_480']
    img_name = basename(urlparse(image_url).path)
    r = requests.get(image_url, stream=True)

    if r.status_code == 200:
        save_dir = "/home/deshraj/Documents/slack_bot"
        with open(os.path.join(save_dir,img_name),'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
    abs_file_path = os.path.join("/home/deshraj/Documents/slack_bot", img_name)

    question = body['file']['initial_comment']['comment']

    request = {
        'question': question,
        'image_path': abs_file_path,
    }
    response = slack_rpc.call(request)
    print(" [x] Requesting the worker to finish the job")
    print(" [.] Got %r" % response)
    # message.send('Yes, I can!')
