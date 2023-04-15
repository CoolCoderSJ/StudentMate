from flask import Flask, redirect, render_template, session, request, url_for
from flask_session import Session
from authlib.integrations.flask_client import OAuth
import sys, os
from utils import *
from flask_cors import CORS, cross_origin

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query

import datetime
import pytz
utc=pytz.UTC

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()
client = (Client()
    .set_endpoint('https://appwrite.shuchir.dev/v1') # Your API Endpoint
    .set_project('studentmate')                # Your project ID
    .set_key(os.environ['APPWRITE_API_KEY']))          # Your secret API key
db = Databases(client)

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
oauth = OAuth(app)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']

CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@app.get("/health")
def health():
    return "ok"

@app.get("/faq")
def faq():
    return render_template("faq.html")

@app.get("/")
def index():
    if not session.get("user"):
        return render_template("landing.html")
    
    user = db.list_documents("users", "users", queries=[Query.equal("id", session.get("user"))])
    user = user['documents'][0]
    syncRes = db.list_documents("sync", "blackboard-na", queries=[Query.equal("userId", user['id'])])
    if syncRes['total'] == 0:
        return redirect("/na/setup/2")
    if not syncRes['documents'][0]['bbSyncComplete']:
        return redirect("/na/setup/2")
    else:
        session['firstTime'] = False

    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))


    classes = getUserClasses(int(session.get("user")))
    return render_template("home.html", user=user, classes=classes)


@app.route("/sendCookies", methods=['POST', 'OPTIONS'])
@cross_origin()
def sendCookies():
    form = request.get_json(force=True)
    print(form)
    username = form['user']
    print(username)
    user = db.list_documents("users", "users", queries=[Query.equal("email", username+"@nastudents.org")])
    userId = int(user['documents'][0]['id'])
    cookies = form['bbcookies']
    print(userId, cookies)
    
    syncRes = db.list_documents("sync", "blackboard-na", queries=[Query.equal("userId", userId)])
    if syncRes['total'] == 0: 
        db.create_document("sync", "blackboard-na", "unique()", {
            "userId": userId,
            "bbcookie": cookies
        })
    else:
        db.update_document("sync", "blackboard-na", syncRes['documents'][0]['$id'], {
            "userId": userId,
            "bbcookie": cookies
        })
    syncRes = db.list_documents("sync", "blackboard-na", queries=[Query.equal("userId", userId)])

    if not syncRes['documents'][0]['bbSyncComplete']:
        classes = getBbClasses(userId, cookies)
        for c in classes:
            matches = db.list_documents("users", "classes", queries=[Query.equal("courseId", c['courseId']), Query.equal("userId", userId)])
            if matches['total'] > 0:
                continue
            db.create_document("users", "classes", "unique()", {
                "id": getId("classes"),
                "className": c['name'],
                "teacher": c['teacher'],
                "userId": userId,
                "courseId": c['courseId'],
                "propagateAutomatically": True
            })
            link = getBbClassPage(userId, c['courseId'])
            if link:
                assignments = gpt_ify_classes(link)
                for name, due in assignments.items():
                    userclass = db.list_documents("users", "classes", queries=[Query.equal("courseId", c['courseId']), Query.equal("userId", userId)])
                    print(name, due, c['name'])
                    now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z')
                    db.create_document("users", "assignments", "unique()", {
                        "id": getId("assignments"),
                        "name": name,
                        "added": now,
                        "due": due.strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                        "classId": userclass['documents'][0]['id'],
                        "userId": userId
                    })
        db.update_document("sync", "blackboard-na", syncRes['documents'][0]['$id'], {
            "bbSyncComplete": True
        })


    return redirect("/")

@app.get("/na/setup/2")
def setup2():
    
    if not session.get("user"):
        return render_template("landing.html")
    
    classes = db.list_documents("users", "classes", queries=[Query.equal("userId", session.get("user"))])
    if classes['total'] > 0: session['firstTime'] = False
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = db.list_documents("users", "users", queries=[Query.equal("id", session.get("user"))])
    user = user['documents'][0]
    syncRes = db.list_documents("sync", "blackboard-na", queries=[Query.equal("userId", user['id'])])
    if syncRes['total'] == 0:
        return render_template("setup2.html", context={"user": getUserInfo(int(session.get("user")))})
    if not syncRes['documents'][0]['bbSyncComplete']:
        return render_template("setup2.html", context={"user": getUserInfo(int(session.get("user")))})
    return redirect("/")

@app.get("/login")
def loginGet():
    
    if session.get("user"):
        return redirect("/")
    
    return render_template("login.html")

@app.post("/settings")
def setSettings():
    if not session.get("user"):
        return redirect("/")

    user = db.list_documents("users", "users", queries=[Query.equal("id", session.get("user"))])
    user = user['documents'][0]
    db.update_document("users", "users", user['$id'], {
        "id": user['id'],
        "name": user['name'],
        "email": user['email'],
        "phoneNumber": request.form['phoneNumber'],
        "phoneCarrier": request.form['phoneCarrier']
    })
    return redirect("/")

@app.get("/na/google")
def google():
    
    if session.get("user"):
        return redirect("/")
    
    return oauth.google.authorize_redirect("https://studentmate.shuchir.dev/na/google/auth")


@app.get("/na/google/auth")
def oauthCallback():
    token = oauth.google.authorize_access_token()
    user = token
    print(" Google User ", user)
    email, name = user['userinfo']['email'], user['userinfo']['name']
    if "@northallegheny.org" in email:
        return render_template("error.html", context={"error": "Hi teacher! Unfortunately, we do not have an interface for teachers yet. Something is in the works!"})
    if not "@nastudents.org" in email:
        return render_template("error.html", context={"error": "You must use your NA Student email to login."})
    results = db.list_documents("users", "users", queries=[Query.equal("email", email)])
    if results['total'] == 0:
        session['firstTime'] = True
        results = db.create_document("users", "users", "unique()", {
            "id": getId("users"),
            "name": name,
            "email": email,
            "method": "bb-na"
        })
        session['user'] = results['id']
        return redirect("/")
    else:
        syncRes = db.list_documents("sync", "blackboard-na", queries=[Query.equal("userId", results['documents'][0]['id'])])
        if not syncRes['documents'][0]['bbcookie']:
            session['firstTime'] = True
        else:
            session['firstTime'] = False
        session['user'] = results['documents'][0]['id']
        return redirect("/")

@app.get("/class/<int:classId>/assignment/<assignmentId>/editNotifs/<notiftimes>")
def editNotifs(classId:int, assignmentId, notiftimes):
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    assignment = db.list_documents("users", "assignments", queries=[Query.equal("classId", userclass['id']), Query.equal("id", int(assignmentId))])
    if assignment['total'] == 0:
        return render_template("error.html", context={"error": "Assignment not found."})
    
    assignment = assignment['documents'][0]
    notifs = notiftimes.split(",")
    notifdb = db.list_documents("users", "notifications", queries=[Query.equal("assignId", assignment['id'])])
    if notifdb['total'] == 0:
        db.create_document("users", "notifications", "unique()", {
            "assignId": assignment['id'],
            "times": notifs
        })
    else:
        db.update_document("users", "notifications", notifdb['documents'][0]['$id'], {
            "assignId": assignment['id'],
            "times": notifs,
            "notifiedAt": notifdb['documents'][0]['notifiedAt']
        })
    return "ok"

@app.get("/class/<int:classId>/assignment/<assignmentId>/editNotifs/")
def clearNotifs(classId:int, assignmentId):
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    assignment = db.list_documents("users", "assignments", queries=[Query.equal("classId", userclass['id']), Query.equal("id", int(assignmentId))])
    if assignment['total'] == 0:
        return render_template("error.html", context={"error": "Assignment not found."})
    
    assignment = assignment['documents'][0]
    notifdb = db.list_documents("users", "notifications", queries=[Query.equal("assignId", assignment['id'])])
    if notifdb['total'] == 0:
        db.create_document("users", "notifications", "unique()", {
            "assignId": assignment['id'],
            "times": []
        })
    else:
        db.update_document("users", "notifications", notifdb['documents'][0]['$id'], {
            "assignId": assignment['id'],
            "times": [],
            "notifiedAt": notifdb['documents'][0]['notifiedAt']
        })
    return "ok"

@app.post("/class/<int:classId>/assignment/<assignmentId>/edit")
def editAssignment(classId:int, assignmentId):
    print(request.form)
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    assignment = db.list_documents("users", "assignments", queries=[Query.equal("classId", userclass['id']), Query.equal("id", int(assignmentId))])
    if assignment['total'] == 0:
        return render_template("error.html", context={"error": "Assignment not found."})
    
    assignment = assignment['documents'][0]

    db.update_document("users", "assignments", assignment['$id'], {
        "id": assignmentId,
        "classId": userclass['id'],
        "name": request.form.get("name"),
        "userId": user,
        "added": assignment['added'],
        "due": request.form.get("due"),
        "completed": assignment['completed']
    })
    return redirect("/class/" + str(classId))

@app.post("/class/<int:classId>/assignment/<assignmentId>/delete")
def deleteAssignment(classId:int, assignmentId):
    
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))
    
    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    assignment = db.list_documents("users", "assignments", queries=[Query.equal("classId", userclass['id']), Query.equal("id", int(assignmentId))])
    if assignment['total'] == 0:
        return render_template("error.html", context={"error": "Assignment not found."})
    
    assignment = assignment['documents'][0]

    db.delete_document("users", "assignments", assignment['$id'])
    try:
        notif = db.list_documents("users", "notifications", queries=[Query.equal("assignId", assignment['id'])])['documents'][0]
        db.delete_document("users", "notifications", notif['$id'])
    except:
        pass
    return redirect("/class/" + str(classId))

@app.post("/class/<int:classId>/assignment/<assignmentId>/complete")
def completeAssignment(classId:int, assignmentId):
    
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    assignment = db.list_documents("users", "assignments", queries=[Query.equal("classId", userclass['id']), Query.equal("id", int(assignmentId))])
    if assignment['total'] == 0:
        return render_template("error.html", context={"error": "Assignment not found."})
    
    assignment = assignment['documents'][0]

    db.update_document("users", "assignments", assignment['$id'], {
        "id": assignmentId,
        "classId": userclass['id'],
        "name": assignment['name'],
        "userId": user,
        "added": assignment['added'],
        "due": assignment['due'],
        "completed": True
    })
    return redirect("/class/" + str(classId))

@app.post("/class/<int:classId>/assignment/<assignmentId>/uncomplete")
def uncompleteAssignment(classId:int, assignmentId):
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    assignment = db.list_documents("users", "assignments", queries=[Query.equal("classId", userclass['id']), Query.equal("id", int(assignmentId))])
    if assignment['total'] == 0:
        return render_template("error.html", context={"error": "Assignment not found."})
    
    assignment = assignment['documents'][0]

    db.update_document("users", "assignments", assignment['$id'], {
        "id": assignmentId,
        "classId": userclass['id'],
        "name": assignment['name'],
        "userId": user,
        "added": assignment['added'],
        "due": assignment['due'],
        "completed": False
    })
    return redirect("/class/" + str(classId))

@app.post("/class/<int:classId>/edit")
def editClass(classId:int):
    
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    print(user, classId)
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    db.update_document("users", "classes", userclass['$id'], {
        "id": userclass['id'],
        "className": request.form.get("name"),
        "teacher": request.form.get("teacher"),
        "userId": user,
        "courseId": userclass['courseId'],
        "propagateAutomatically": request.form.get("propagateAutomatically") == "on"
    })
    return redirect("/class/" + str(classId))

@app.post("/class/<int:classId>/addAssignment")
def addAssignment(classId:int):
    
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    
    userclass = userclass['documents'][0]

    assignId = getId("assignments")
    db.create_document("users", "assignments", "unique()", {
        "id": assignId,
        "classId": userclass['id'],
        "name": request.form.get("name"),
        "userId": user,
        "added": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
        "due": request.form.get("due"),
        "completed": False
    })
    db.create_document("users", "notifications", "unique()", {
        "assignId": assignId,
    })
    return redirect("/class/" + str(classId))

class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)

@app.get("/class/<int:classId>")
def classpage(classId:int):
    
    if not session.get("user"):
        return render_template("landing.html")
    
    if session.get("firstTime"):
        return render_template("setup.html", user=session.get("user"))

    user = int(session.get("user"))
    userclass = db.list_documents("users", "classes", queries=[Query.equal("userId", user), Query.equal("id", classId)])
    if userclass['total'] == 0:
        return render_template("error.html", context={"error": "You are not enrolled in this class."})
    userclass = userclass['documents'][0]
    assignments = db.list_documents("users", "assignments", queries=[Query.equal("classId", userclass['id'])])
    assignments = assignments['documents']

    assignList = []
    for assignment in assignments:
        due = datetime.datetime.strptime(assignment['due'], '%Y-%m-%dT%H:%M:%S.%f%z')
        notifs = db.list_documents("users", "notifications", queries=[Query.equal("assignId", assignment['id'])])
        if notifs['total'] == 0:
            notifs = []
        else:
            try:
                notifs = notifs['documents'][0]['times']
            except Exception as e: print(e); notifs = []
        assignList.append(Struct(**{
            "id": assignment['id'],
            "name": assignment['name'],
            "added": datetime.datetime.strptime(assignment['added'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime("%m/%d/%Y %I:%M:%S %p"),
            "due": datetime.datetime.strptime(assignment['due'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime("%m/%d/%Y %I:%M:%S %p"),
            "completed": assignment['completed'],
            "classId": assignment['classId'],
            "userId": assignment['userId'],
            "overdue": due < datetime.datetime.now().replace(tzinfo=due.tzinfo),
            "notifs": notifs
        }))
    return render_template("class.html", userclass=userclass, assignments=assignList)

scheduler = BackgroundScheduler()
scheduler.add_job(func=remind, trigger="interval", seconds=60)
scheduler.add_job(func=propagate, trigger="interval", seconds=300)
scheduler.start()

app.run(host="0.0.0.0", port=9999, debug=False)