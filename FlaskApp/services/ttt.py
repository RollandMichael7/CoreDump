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

def arr2string(a):
    s = ""
    for c in a:
        s += str(c)
    return s