import json
import sys
import os
import random
import smtplib
import pika
from base64 impoty b64encode
from email.mime.text import MIMEText
from pymongo import MongoClient
from time import gmtime, strftime
from flask import Flask, request, jsonify, render_template, make_response

app = Flask(__name__)

@app.route('/listen', methods=['POST'])
def listen():
    keys = request.get_json(force=True)['keys']
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    result = channel.queue_declare(exclusive=True)
    for key in keys:        
        channel.queue_bind(exchange='hw3', queue=result.method.queue, routing_key=key)
    while True:
        method, properties, msg = channel.basic_get(queue=result.method.queue)
        if msg is not None:
            channel.close()
            connection.close()
            return jsonify({'msg':msg})

@app.route('/speak', methods=['POST'])
def speak():
    key = request.get_json(force=True)['key']
    msg = request.get_json(force=True)['msg']
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.basic_publish(exchange='hw3', routing_key=key, body=msg)
    channel.close()
    connection.close()
    return jsonify({'status':'OK'})
