import json
import sys
import os
import random
import string
import smtplib
import time
from datetime import datetime
from services import database
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from time import gmtime, strftime
from flask import Flask, request, jsonify, render_template, make_response, Markup

app = Flask(__name__)

@app.errorhandler(404)
def not_found(e):
    print("----------------- NOT FOUND: " + str(e))
    return jsonify({'status':'error'})


@app.route('/user/<username>/', methods=['GET'])
def user_info(username):
    user = database.getDoc('users', {'username':username})
    if user is None:
        return jsonify({'status':'error'})
    return jsonify({'status':'OK', 'user': {'email':user['email'], 'reputation':user['reputation']}})

@app.route('/user/<username>/questions/', methods=['GET'])
def user_questions(username):
    user = database.getDoc('users', {'username':username})
    if user is None:
        return jsonify({'status':'error'})
    matches = []
    db = database.getDB('questions')
    for q in db.find():
        if q['user']['username'] == username:
            matches.append(q['id'])
    return jsonify({'status':'OK', 'questions':matches})

@app.route('/user/<username>/answers/', methods=['GET'])
def user_answers(username):
    user = database.getDoc('users', {'username':username})
    if user is None:
        return jsonify({'status':'error'})
    matches = []
    db = database.getDB('answers')
    for a in db.find():
        if a['user'] == username:
            matches.append(a['id'])
    return jsonify({'status':'OK', 'answers':matches})

if __name__ == '__main__':
    app.run(debug=True)
