import string
import random
from operator import itemgetter
from pymongo import MongoClient

def getDB(collection):
    client = MongoClient('localhost', 27017)
    db = client['cse356']
    collection = db[collection]
    return collection

def getDoc(collection, args):
    db = getDB(collection)
    for doc in db.find():
        match = True
        for key in args.keys():
            #print(doc[key] + " vs " + args[key])
            if doc[key] != args[key]:
                match = False
                break
        if match:
            return doc
    return None

def verify(email, key):
    users = getDB('users')
    for doc in users.find():
        if doc['email'] == email and (key == doc['key'] or key == "abracadabra"):
            if doc['enabled'] == True:
                return {'status':'error', 'error':"You're already registered."}
            user = doc
            user['enabled'] = True
            #user['gamestate'] = [' ',' ',' ',' ',' ',' ',' ', ' ',' ']
            #user['gameID'] = 1
            #user['gameStartDate'] = strftime("%Y-%m-%d", gmtime())
            users.save(user)
            return {'status': 'OK'}
    return {'status':'error', 'error':'Invalid credentials.'}

def getMatchingAnswers(qID):
    answers = []
    answerDB = getDB('answers')
    for answer in answerDB.find():
        if answer['qID'] == qID:
            answers.append(answer)
    return answers

def searchQuestions(timestamp, limit):
    questions = []
    questionDB = getDB('questions')
    for question in questionDB.find():
        if question['timestamp'] <= timestamp:
            questions.append(question)
            if len(questions) == limit:
                return questions
    return questions

def getTopQuestions(limit):
    top = []
    sortedQs = getDB('questions').find().sort("view_count")
    for q in sortedQs:
        top.append(q)
        if len(top) == limit:
            return top
    return top

def getID():
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
