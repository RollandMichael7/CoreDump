import json
import sys
import os
import random
import string
import smtplib
import time
from services import database
from email.mime.text import MIMEText
from time import gmtime, strftime
from flask import Flask, request, jsonify, render_template, make_response

app = Flask(__name__)

@app.route('/', methods=['GET'])
def default():
    try:
        username = request.cookies['cse356user']
        user = database.getDoc('users', {'username':username, 'enabled':True})
        if user is not None:
            return render_template('main.html', loggedIn=True, username=username)
    except KeyError:
        pass
    return render_template('main.html', loggedIn=False, username="")

@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/adduser', methods=['POST'])
def adduser():
    uname = request.get_json(force=True)['username']
    pwd = request.get_json(force=True)['password']
    email = request.get_json(force=True)['email']
    users = database.getDB('users')

    doc = database.getDoc('users', {'username':uname})
    if doc is not None:
        return jsonify({'status':'error', 'error':'That username is already in use.'})
    doc = database.getDoc('users', {'email':email})
    if doc is not None:
        return jsonify({'status':'error', 'error':'That email is already in use.'})

    key = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
    userObject = { 'username':uname, 'password':pwd, 'email':email, 'key':key, 'enabled':False, 'reputation':0}
    #'gamestate':[], 'gameID':[], 'gameStartDate':"", 'completedGameStates':[], 'completedGameList':[], 'wins':0, 'losses':0, 'ties':0}
    users.insert(userObject)

    verify = "http://130.245.170.46/verify?key=" + key + "&email=" + email
    msg = MIMEText("Hi " + uname + "! Please use this link to verify your account: " + verify + "\n\nvalidation key: <" + key + ">")
    #me = os.environ['MAIL_USER']
    me = "flaskbot356@gmail.com"
    to = email

    msg['Subject'] = 'Hello there!'
    msg['To'] = to
    msg['From'] = me
    s = smtplib.SMTP_SSL('smtp.gmail.com')
    #s.login(me, os.environ['MAIL_PASSWORD'])
    s.login(me, REDACTED)
    s.sendmail(me, [to], msg.as_string())
    return jsonify({"status": "OK"})

@app.route('/verify', methods=['GET'])
def verify_get():
    email = request.args.get('email')
    key = request.args.get('key')
    status = database.verify(email, key)
    if status['status'] == 'OK':
        return render_template('register_success.html')
    else:
        return render_template('register_fail.html', error=status['error'])

@app.route('/verify', methods=['POST'])
def verify_post():
    email = request.get_json(force=True)['email']
    key = request.get_json(force=True)['key']
    return jsonify(database.verify(email, key))

@app.route('/login', methods=['GET'])
def display_login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    uname = request.get_json(force=True)['username']
    pwd = request.get_json(force=True)['password']
    user = database.getDoc('users', {'username':uname, 'password':pwd, 'enabled':True})
    if user is not None:
        resp = make_response(jsonify({'status':'OK'}))
        resp.set_cookie('cse356user', str(user['username']))
        return resp
    return jsonify({'status':'error', 'error':'Invalid credentials.'})

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    if request.method == 'POST':
        resp = make_response(jsonify({'status':'OK'}))
    else:
        resp = make_response(render_template('logout.html'))
    resp.set_cookie('cse356user', "")
    return resp

############### q & a ###############

@app.route('/questions/<qID>/view', methods=['GET'])
def view_question(qID):
    print("GET to questions/" + qID + "/view")
    question = database.getDoc('questions', {'id':qID})
    if question is None:
        return render_template('notfound.html')
    return render_template('question.html', username=question['user']['username'], title=question['title'], body=question['body'])

@app.route('/questions/add', methods=['POST'])
def add_question():
    try:
        username = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'error', 'error':'You are not logged in.'})
    user = database.getDoc('users', {'username':username, 'enabled':True})
    if user is None:
        return jsonify({'status':'error', 'error':'Invalid credentials.'})
    try:
        title = request.get_json(force=True)['title']
        body = request.get_json(force=True)['body']
        tags = request.get_json(force=True)['tags']
    except KeyError:
        return jsonify({'status':'error', 'error':'Title, body and tags required.'})

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
    question = database.getDoc('questions', {'id':qID})
    if question is None:
        return jsonify({'status':'error','error':'Invalid question ID.'})
    try:
        username = request.cookies['cse356user']
    except KeyError:
        username = None
    user = None
    loggedIn = False
    if username is not None and username != '':
        user = database.getDoc('users', {'username':username, 'enabled':True})
        if user is not None:
            loggedIn = True
    if loggedIn:
        if user['username'] not in question['viewer_usernames']:
            question['view_count'] = question['view_count'] + 1
            question['viewer_usernames'].append(user['username'])
    else:
        if request.remote_addr not in question['viewer_IPs']:
            question['view_count'] = question['view_count'] + 1
            question['viewer_IPs'].append(request.remote_addr)
    db = database.getDB('questions')
    db.save(question)

    question.pop('_id', None)
    question.pop('viewer_usernames', None)
    question.pop('viewer_IPs', None)
    return jsonify({'status':'OK','question':question})


@app.route('/questions/<qID>/answers/add', methods=['POST'])
def add_answer(qID):
    question = database.getDoc('questions', {'id':qID})
    if question is None:
        return jsonify({'status':'error','error':'Invalid question ID.'})
    try:
        username = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'error', 'error':'You are not logged in.'})
    user = database.getDoc('users', {'username':username, 'enabled':True})
    if user is None:
        return jsonify({'status':'error','error':'Invalid credentials.'})

    try:
        body = request.get_json(force=True)['body']
    except KeyError:
        return jsonify({'status':'error', 'error':'Body required.'})
    try:
        media = request.get_json(force=True)['media']
    except KeyError:
        media = []
    aID = database.getID()
    answer = {'id':aID, 'user':username, 'body':body, 'score':0, 'is_accepted':False,
              'timestamp':time.time(), 'media':media, 'qID':qID}
    db = database.getDB('answers')
    db.insert(answer)
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


@app.route('/search', methods=['POST'])
def search_questions():
    try:
        timestamp = request.get_json(force=True)['timestamp']
    except KeyError:
        timestamp = time.time()
    try:
        limit = request.get_json(force=True)['limit']
    except KeyError:
        limit = 25
    if limit > 100:
        limit = 100
    questions = database.searchQuestions(timestamp, limit)
    for q in questions:
        q.pop('_id', None)
        q.pop('viewer_usernames', None)
        q.pop('viewer_IPs', None)
    return jsonify({'status':'OK', 'questions':questions})

@app.route('/topQuestions', methods=['POST'])
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


@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

if __name__ == '__main__':
    app.run(debug=True)
