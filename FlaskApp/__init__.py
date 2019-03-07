import json
import sys
import os
import random
import smtplib
import pika
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

# list of indices that u can win with
indices = [
    [0,1,2], [3,4,5], [6,7,8],
    [0,3,6], [1,4,7], [2,5,8],
    [0,4,8], [2,4,6]
]

@app.route('/play', methods=['POST'])
def display_game_post():
    name = request.form['name']
    return render_template('ttt.html', name=name)

@app.route('/play', methods=['GET'])
def display_game_get():
    try:
        name = request.cookies['cse356user']
    except KeyError:
        return render_template('error.html')
    if name == "":
        return render_template('error.html')
    return render_template('ttt.html', name=name)

@app.route('/ttt/play', methods=['POST'])
def play():
    move = request.get_json(force=True)['move']
    try:
        user = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'ERROR'})
    userObject = getDoc(user)
    if userObject is None:
        return jsonify({'status':'ERROR'})
    grid = userObject['gamestate']
    if move is None:
        return jsonify({'grid':grid})
    else:
        move = int(move)
    grid[move] = 'X'
    gameover = False
    indices, winner = checkWin(grid)
    if winner == ' ':
        i = findSpot(grid)
        if i is None:
            gameover = True
        else:
            grid[i] = 'O'
            indices, winner = checkWin(grid)
    if winner != ' ' or gameover:
        gameID = userObject['gameID']
        start = userObject['gameStartDate']
        userObject['completedGameList'].append({"id":gameID, "start_date":start})
        userObject['completedGameStates'].append({"id":gameID, "grid":grid, "winner":winner})
        if winner == 'X':
            userObject['wins'] = userObject['wins'] + 1
        elif winner == 'O':
            userObject['losses'] = userObject['losses'] + 1
        else:
            userObject['ties'] = userObject['ties'] + 1
        userObject['gameID'] = gameID + 1
        userObject['gameStartDate'] = strftime("%Y-%m-%d", gmtime())
        userObject['gamestate'] = [' ',' ',' ',' ',' ',' ',' ',' ',' ']
        gameover = True
    else:
        userObject['gamestate'] = grid
    users = getDB('users')
    users.save(userObject)
    resp =  make_response(jsonify({"grid": grid, "winner": winner}))
    resp.set_cookie("cse356game", arr2string(grid))
    if gameover:
        resp.set_cookie("cse356gameover", "true")
    else:
        resp.set_cookie("cse356gameover", "false")
    return resp

@app.route('/listgames', methods=['POST'])
def listGames():
    try:
        user = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'ERROR'})
    userObject = getDoc(user)
    if userObject is None:
        return jsonify({'status':'ERROR'})
    return jsonify({'status':'OK', 'games':userObject['completedGameList']})

@app.route('/getgame', methods=['POST'])
def getGame():
    try:
        user = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'ERROR'})
    gameID = request.get_json(force=True)['id']
    userObject = getDoc(user)
    if userObject is None:
        return jsonify({'status':'ERROR'})
    for game in userObject['completedGameStates']:
        if game['id'] == gameID:
            return jsonify({"status":"OK","grid":game['grid'],"winner":game['winner']})
    return jsonify({'status':'ERROR'})

@app.route('/getscore', methods=['POST'])
def getScore():
    try:
        user = request.cookies['cse356user']
    except KeyError:
        return jsonify({'status':'ERROR'})
    userObject = getDoc(user)
    if userObject is None:
        return jsonify({'status':'ERROR'})
    return jsonify({'status':'OK', 'human':userObject['wins'], 'wopr':userObject['losses'], 'tie':userObject['ties']})

@app.route('/', methods=['GET'])
def default():
    return render_template('splash.html')

@app.route('/register', methods=['GET'])
def register():
    return render_template('splash.html')

@app.route('/adduser', methods=['POST'])
def adduser():
    uname = request.get_json(force=True)['username']
    pwd = request.get_json(force=True)['password']
    email = request.get_json(force=True)['email']
    users = getDB('users')

    userObject = { 'name':uname, 'password':pwd, 'email':email, 'key':'abracadabra', 'enabled':False, 'gamestate':[], 'gameID':[], 'gameStartDate':"", 'completedGameStates':[], 'completedGameList':[], 'wins':0, 'losses':0, 'ties':0}
    users.insert(userObject)

    verify = "http://130.245.170.46/verify?key=abracadabra&email=" + email
    msg = MIMEText("Hi " + uname + "! Please use this link to verify your account: " + verify)
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
    status = verify(email, key)
    if status['status'] == 'OK':
        return render_template('register_success.html')
    else:
        return render_template('register_fail.html')

@app.route('/verify', methods=['POST'])
def verify_post():
    email = request.get_json(force=True)['email']
    key = request.get_json(force=True)['key']
    return jsonify(verify(email, key))

@app.route('/login', methods=['GET'])
def display_login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    uname = request.get_json(force=True)['username']
    pwd = request.get_json(force=True)['password']
    user = getDoc(uname, password=pwd)
    if user is not None:
        resp = make_response(jsonify({'status':'OK'}))
        resp.set_cookie('cse356game',arr2string(user['gamestate']))
        resp.set_cookie('cse356user', str(user['name']))
        return resp
    return jsonify({'status':'ERROR'})

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    resp = make_response(jsonify({'status':'OK'}))
    resp.set_cookie('cse356user', "")
    resp.set_cookie('cse356game', "")
    return resp

def getDB(collection):
    client = MongoClient('localhost', 27017)
    db = client['cse356']
    collection = db[collection]
    return collection

def getDoc(user, password=None):
    db = getDB('users')
    for doc in db.find():
        if password is not None:
            if doc['enabled'] and doc['name'] == user and doc['password'] == password:
                return doc
        else:
            if doc['enabled'] and doc['name'] == user:
                return doc
    return None

def verify(email, key):
    users = getDB('users')
    for doc in users.find():
        if doc['email'] == email and (key == doc['key'] or key == "abracadabra"):
            user = doc
            user['enabled'] = True
            user['gamestate'] = [' ',' ',' ',' ',' ',' ',' ', ' ',' ']
            user['gameID'] = 1
            user['gameStartDate'] = strftime("%Y-%m-%d", gmtime())
            users.save(user)
            return {'status': 'OK'}
    return {'status':'ERROR'}

def arr2string(a):
    s = ""
    for c in a:
        s += str(c)
    return s

def checkWin(grid):
    for l in indices:
        if compare(grid, l[0], l[1], l[2]):
            return l, grid[l[0]]
    return None, ' '

# if player using C is about to win with indices x,y,z
# return the winning index. else, return -1
def canWin(grid, c, x, y, z):
    if grid[x] == c and grid[x] == grid[y] and grid[z] == ' ':
        return z
    elif grid[y] == c and grid[y] == grid[z] and grid[x] == ' ':
        return x
    elif grid[z] == c and grid[z] == grid[x] and grid[y] == ' ':
        return y
    else:
        return -1

# find somewhere to place O
def findSpot(grid):
    # first make sure theres an empty spot
    valid = False
    for c in grid:
        if c == ' ':
            valid = True
            break
    if not valid:
        return None
    # check if we can win
    for l in indices:
        x = canWin(grid, 'O', l[0], l[1], l[2])
        if x != -1:
            #sys.stderr.write('ttt: can win at ' + str(x) + '\n')
            return x
    # check if the player is about to win
    for l in indices:
        x = canWin(grid, 'X', l[0], l[1], l[2])
        if x != -1:
            #sys.stderr.write('ttt: player about to win at ' + str(x) + '\n')
            return x
    # else, place in random open spot
    while True:
        i = random.randint(0,8)
        if grid[i] == ' ':
            return i

def compare(grid, x, y, z):
    return grid[x] != ' ' and grid[x]==grid[y] and grid[y]==grid[z]

@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

if __name__ == '__main__':
    app.run(debug=True)
