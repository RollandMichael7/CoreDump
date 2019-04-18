import string
import random
import time
import pymongo
from operator import itemgetter
#from cassandra.cluster import Cluster

def getDB(collection):
    client = pymongo.MongoClient('192.168.122.10', 27017)
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

def searchQuestions(timestamp, limit, query=None):
    matches = []
    db = getDB('questions')
    if query is not None and query != "":
        db.create_index([('title', 'text'), ('body', 'text')], default_language='none')
        questions = db.find({'$text': {'$search':query}})
    else:
        questions = db.find()
    for question in questions:
        if question['timestamp'] <= timestamp:
            matches.append(question)
            if len(matches) == limit:
                return matches
    return matches

def getTopQuestions(limit):
    top = []
    sortedQs = getDB('questions').find().sort("view_count", pymongo.DESCENDING)
    for q in sortedQs:
        top.append(q)
        if len(top) == limit:
            return top
    return top

def getID():
    questions = getDB('questions')
    answers = getDB('answers')
    new = True
    start = True
    while start or not new:
        start = False
        new = True
        newID = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        for q in questions.find():
            if q['id'] == newID:
                new = False
        if not new:
            continue
        for a in answers.find():
            if a['id'] == newID:
                new = False
    return newID

#def cassandraInsert(filename, contents):
#    cluster = Cluster()
#    session = cluster.connect('hw5')
#    print("------------INSERTING " + filename)
#    session.execute("""
#                    INSERT INTO imgs (filename, contents)
#                    VALUES (%s, %s)
#                    """,
#                    (filename, contents))
#    return 0

#def cassandraSelect(filename):
#    cluster = Cluster()
#    session = cluster.connect('hw5')
#    data = session.execute("""
#                            SELECT contents FROM imgs WHERE filename=%s;
#                            """,
#                            (filename,))
#    for o in data:
#        return o.contents;
#    return None;
