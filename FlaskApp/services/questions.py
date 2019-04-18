import json
import sys
import os
import random
import string
import time
from datetime import datetime
from services import database
from time import gmtime, strftime
from flask import Flask, request, jsonify, render_template, make_response, Markup

app = Flask(__name__)

@app.route('/questions/add', methods=['POST'])
def add_question():
    username = request.get_json(force=True)['username']
    user = database.getDoc('users', {'username':username, 'enabled':True})
    if user is None:
        return jsonify({'status':'error', 'error':'Invalid credentials.'})
    title = request.get_json(force=True)['title']
    body = request.get_json(force=True)['body']
    tags = request.get_json(force=True)['tags']
    db = database.getDB('questions')
    qID = database.getID()
    qObject = {'id':qID, 'user':{'username':username, 'reputation':user['reputation']},
                'title':title, 'body':body, 'score':0, 'view_count':0, 'answer_count':0,
                'timestamp':time.time(), 'media':[], 'tags':tags, 'accepted_answer_id':None,
                'viewer_usernames':[], 'viewer_IPs':[]}
    db.insert(qObject)
    return jsonify({'status':'OK', 'id':qID})

@app.route('/questions/<qID>', methods=['GET'])
def show_question(qID):
    print("GET to /questions/" + str(qID))
    question = database.getDoc('questions', {'id':qID})
    if question is None:
	print("--------error!")
        return jsonify({'status':'error','error':'Invalid question ID.'})
    username = request.args['username']
    user = None
    loggedIn = False
    if username is not None and username != '':
        user = database.getDoc('users', {'username':username, 'enabled':True})
        if user is not None:
            loggedIn = True
    if loggedIn:
        print('-------------- logged in')
        increment_view(question, user=username)
    else:
        print('-------------- not logged in')
        increment_view(question, ip=request.remote_addr)

    question.pop('_id', None)
    question.pop('viewer_usernames', None)
    question.pop('viewer_IPs', None)
    return jsonify({'status':'OK','question':question})

@app.route('/questions/<qID>/answers/add', methods=['POST'])
def add_answer(qID):
    print("add answer to " + str(qID))
    question = database.getDoc('questions', {'id':qID})
    if question is None:
        print("Invalid question")
        return jsonify({'status':'error','error':'Invalid question ID.'})
    username = request.get_json(force=True)['username']
    user = database.getDoc('users', {'username':username, 'enabled':True})
    if user is None:
        print("Invalid user")
        return jsonify({'status':'error','error':'Invalid credentials.'})
    body = request.get_json(force=True)['body']
    media = request.get_json(force=True)['media']
    aID = database.getID()
    answer = {'id':aID, 'user':username, 'body':body, 'score':0, 'is_accepted':False,
              'timestamp':time.time(), 'media':media, 'qID':qID}
    db = database.getDB('answers')
    db.insert(answer)
    print("answer added")
    return jsonify({'status':'OK', 'id':aID})

@app.route('/questions/<qID>/answers', methods=['GET'])
def get_answers(qID):
    question = database.getDoc('questions', {'id':qID})
    if question is None:
        return jsonify({'status':'error', 'error':'Invalid question ID.'})
    answers = database.getMatchingAnswers(qID)
    for a in answers:
        a.pop('_id', None)
        a.pop('qID', None)
    return jsonify({'status':'OK', 'answers':answers})

@app.route('/questions/top', methods=['POST'])
def top_questions():
    #try:
    #    limit = request.get_json(force=True)['limit']
    #except KeyError:
    #    limit = 10
    questions = database.getTopQuestions(10)
    if questions is None:
        return jsonify({'questions':[]})
    for q in questions:
        q.pop('_id', None)
        q.pop('viewer_IPs', None)
        q.pop('viewer_usernames', None)
    return jsonify({'questions':questions})


def increment_view(question, user=None, ip=None):
    db = database.getDB('questions')
    print('views: ' + str(question['view_count']))
    if user is not None:
        if user not in question['viewer_usernames']:
            print('-------------- registered user ' + str(user))
            newViews = question['view_count'] + 1
            newUsers = question['viewer_usernames']
            newUsers.append(user)
            db.update_one({'_id':question['_id']}, {'$set': {'view_count':newViews, 'viewer_usernames':newUsers}})
    elif ip is not None:
        if ip not in question['viewer_IPs']:
            print('-------------- registered IP ' + str(ip))
            newViews = question['view_count'] + 1
            newIPs = question['viewer_IPs']
            newIPs.append(ip)
            db.update_one({'_id':question['_id']}, {'$set': {'view_count':newViews, 'viewer_IPs':newIPs}})
    return

if __name__ == '__main__':
    app.run(debug=True)
