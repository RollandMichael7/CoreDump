import json
import sys
import os
import random
import string
import smtplib
import time
import requests
from datetime import datetime
from services import database
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from time import gmtime, strftime
from flask import Flask, request, jsonify, render_template, make_response, Markup

usersIP =  'http://192.168.122.13'
questionsIP = 'http://192.168.122.14'

app = Flask(__name__)

#@app.errorhandler(404)
#def not_found(e):
#    print("----------------- NOT FOUND: " + str(e))
#    return jsonify({'status':'error'})

@app.route('/', methods=['GET'])
def splash():
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
    userObject = { 'username':uname, 'password':pwd, 'email':email, 'key':key, 'enabled':False, 'reputation':1}
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
    s.login(me, [REDACTED])
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

@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response


############### cassandra ###############

@app.route('/deposit', methods=['POST'])
def deposit():
    filename = request.form.get('filename')
    contents = request.files['contents']
    print("--------------call to /deposit with " + filename)
    database.cassandraInsert(filename, bytearray(contents.read()))
    return jsonify({'status':'OK'})

@app.route('/retrieve', methods=['GET'])
def retrieve():
    filename = request.args.get('filename')
    content = database.cassandraSelect(filename)
    if content is None:
        return jsonify({'status':'error'})
    response = make_response(content)
    filetype = filename.split(".")[1]
    response.headers.set('Content-Type', 'image/'+filetype)
    return response


############### q & a ###############

##### questions #####
@app.route('/questions/<qID>/view', methods=['GET'])
def view_question(qID):
    #print('------------GET to view question ' + str(qID))
    try:
        username = request.cookies['cse356user']
    except KeyError:
        username = ""
    params = {'username':username}
    r = requests.get(questionsIP+'/questions/'+str(qID), params=params)
    if r.json()['status'] == 'error':
        return render_template('q_notfound.html')
    #print("--------------received " + str(r.json()))
    question = r.json()['question']
    question['body'] = Markup(question['body'])
    timestamp = datetime.utcfromtimestamp(question['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    answers = database.getMatchingAnswers(qID)
    accepted = None
    for a in answers:
        a['body'] = Markup(a['body'])
	a['timestamp'] = datetime.utcfromtimestamp(a['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        if accepted is None and a['is_accepted']:
            accepted = a
            break
    return render_template('question.html', question=question, answers=answers, accepted=accepted, timestamp=timestamp, id=qID)

@app.route('/questions/add', methods=['POST'])
def add_question():
    try:
        username = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'error', 'error':'You must be logged in to ask a question.'})
    if username == "":
        return jsonify({'status':'error', 'error':'You must be logged in to ask a question.'})
    try:
        title = request.get_json(force=True)['title']
        body = request.get_json(force=True)['body']
        tags = request.get_json(force=True)['tags']
    except KeyError:
        return jsonify({'status':'error', 'error':'Title, body and tags required.'})
    params = {'title':title, 'body':body, 'tags':tags, 'username':username}
    r = requests.post(questionsIP+'/questions/add', json=params)
    return jsonify(r.json())

@app.route('/questions/<qID>', methods=['GET'])
def question_content(qID):
    print('-------------GET to /questions/' + str(qID))
    try:
        username = request.cookies['cse356user']
    except KeyError:
        username = None
    params = {'username':username}
    r = requests.get(questionsIP+'/questions/'+str(qID), params=params)
    return jsonify(r.json())

@app.route('/questions/<qID>', methods=['DELETE'])
def delete_question(qID):
    question = database.getDoc('questions', {'id':qID})
    if question is None:
        return jsonify({'status':'error', 'error':'Invalid question ID'}), 400
    try:
        username = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'error', 'error':'You\'re not logged in'}), 400
    if question['user']['username'] != username:
        return jsonify({'status':'error', 'error':'You can not delete another user\'s question'}), 400
    user = database.getDoc('users', {'username':username, 'enabled':True})
    if user is None:
        return jsonify({'status':'error', 'error':'Invalid credentials'}), 400
    db = database.getDB('questions')
    db.delete_one(question)
    return jsonify({'status':'ok'}), 200

@app.route('/questions/<qID>/answers/add', methods=['POST'])
def add_answer(qID):
    print("-----add answer to " + str(qID))
    try:
        username = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'error', 'error':'You are not logged in.'})
    try:
        body = request.get_json(force=True)['body']
    except KeyError:
        return jsonify({'status':'error', 'error':'Body required.'})
    try:
        media = request.get_json(force=True)['media']
    except KeyError:
        media = []
    params = {'username':username, 'body':body, 'media':media}
    r = requests.post(questionsIP+'/questions/'+str(qID)+'/answers/add', json=params)
    return jsonify(r.json())

@app.route('/questions/<qID>/answers', methods=['GET'])
def get_answers(qID):
    r = requests.get(questionsIP+'/questions/'+str(qID)+'/answers')
    return jsonify(r.json())

@app.route('/questions/tagged/<tag>', methods=['POST', 'GET'])
def tagged_questions(tag):
    db = database.getDB('questions')
    questions = []
    for q in db.find():
        if tag in q['tags']:
            questions.append({'title':q['title'], 'id':q['id']})
    if request.method == 'POST':
        return jsonify({'questions':questions})
    elif request.method == 'GET':
        return render_template('tagged.html', questions=questions, tag=tag)

@app.route('/questions/top', methods=['POST'])
def top_questions():
    r = requests.post(questionsIP+'/questions/top')
    return jsonify(r.json())

##### search #####
@app.route('/search', methods=['POST'])
def search_post():
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
    try:
        query = request.get_json(force=True)['q']
    except KeyError:
        query = ""
    print("---------------- query: " + str(query))
    questions = database.searchQuestions(timestamp, limit, query)
    for q in questions:
        q.pop('_id', None)
        q.pop('viewer_usernames', None)
        q.pop('viewer_IPs', None)
    return jsonify({'status':'OK', 'questions':questions})

@app.route('/search', methods=['GET'])
def search_get():
    try:
        timestamp = request.args['timestamp']
    except KeyError:
        timestamp = time.time()
    try:
        limit = request.args['limit']
    except KeyError:
        limit = 10
    if limit > 100:
        limit = 100
    try:
        query = request.args['query']
    except KeyError:
        query = ""
    questions = database.searchQuestions(timestamp, limit, query)
    return render_template('tagged.html', questions=questions, tag=query)

##### users #####
@app.route('/user/<username>/view', methods=['GET'])
def view_user(username):
    user = database.getDoc('users', {'username':username})
    if user is None:
        return render_template('u_notfound.html')
    return render_template('user.html', user=user)

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
