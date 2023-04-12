# https://docs.google.com/presentation/d/e/2PACX-1vQvLy60vlsp4jsGW69-lkppZeThqanHiqJcYt-4JyZffI4tZL-cwLmWZTgLWM1pc7BjzICJE9FBLnw7/embed?start=false&amp;loop=false&amp;delayms=3000
from lxml import etree
import smtplib
from email.message import EmailMessage
import urllib.parse
import time
import os
import datetime
import requests
from PIL import Image
from pytesseract import image_to_string
from youdotcom import Chat

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query

from dotenv import load_dotenv
load_dotenv()


SENDER = os.environ['SENDGRID_EMAIL']
PASSWORD = os.environ['SENDGRID_PASSWORD']

parser = etree.XMLParser(strip_cdata=False)


client = (Client()
          .set_endpoint('https://appwrite.shuchir.dev/v1')  # Your API Endpoint
          .set_project('studentmate')                # Your project ID
          .set_key(os.environ['APPWRITE_API_KEY']))          # Your secret API key
db = Databases(client)

def gpt_ify_classes(url):
    pId = url.split("/d/e/")[1].split("/")[0].replace("-", "")
    print("Getting screenshot...")
    apiurl = f"https://image.thum.io/get/maxAge/12/width/1920/{url}"
    payload = {}
    headers = {
        'Referer': 'https://www.thum.io/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }

    r = requests.request("GET", apiurl, headers=headers, data=payload)
    with open(f"{pId}.png", "wb") as f:
        f.write(r.content)
    print("reading text...")
    text = image_to_string(Image.open(f"{pId}.png"))
    text = text.replace('\n', '')
    os.remove(f"{pId}.png")
    time.sleep(.5)
    message = f"You are given the following text: {text} From this piece of text, find all of the assignments listed and when they are due. List these assignments in the following order- [assignment name] due [due date] where due date is in the form mm/dd/yyyy hh:mm:ss. If no date is specified, use the date the assignment was assigned on. If no time is specified, use 23:59:59 for the time. Do not use parentheses. Today is {datetime.datetime.today().strftime('%A')}. The date is {datetime.datetime.now().strftime('%m/%d/%Y')}. Use this date to calculate dates for names of days All dates should be after today. Make sure the format matches the following exactly- [assignment name] due [due date] where due date is mm/dd/yyyy hh:mm:ss. Insert a new line after each assignment."
    print(urllib.parse.quote(message), "\n", os.environ['YOU_API_KEY'].strip())
    assignments = Chat.send_message(message=urllib.parse.quote(
        message), api_key=os.environ['YOU_API_KEY'].strip())
    if not "message" in assignments:
        print(assignments)
        return {}
    assignments = assignments['message']
    print(assignments)
    assignmentsList = {}
    if not assignments:
        return assignmentsList
    for assignment in assignments.split("\n"):
        if not " due " in assignment:
            continue

        assignment = assignment.split(" due ")
        if len(assignment) == 1:
            assignment = assignment[0].split(" due on ")
        name = assignment[0]
        date = assignment[1]
        try:
            date = datetime.datetime.strptime(date, "%m/%d/%Y %H:%M:%S")
        except:
            continue
        if name not in assignmentsList.keys():
            assignmentsList[name] = date
    print(assignmentsList)
    return assignmentsList


def getBbClasses(userId, cookie=None):
    document = db.list_documents("users", "users", queries=[
                                 Query.equal("id", userId)])
    if document['total'] == 0:
        return None
    document = document['documents'][0]
    if cookie is None:
        cookie = document['bbcookie']

    url = "https://northallegheny.blackboard.com/webapps/portal/execute/tabs/tabAction"

    payload = 'action=refreshAjaxModule&modId=_3_1&tabId=_1_1&tab_tab_group_id=_1_1'
    headers = {
        'Cookie': cookie,
        'Origin': 'https://northallegheny.blackboard.com',
        'Referer': 'https://northallegheny.blackboard.com/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    root = etree.XML(response.text, parser)
    root = root.text
    splitclasses = root.split(' target="_top">')
    classes = []
    for i in range(1, len(splitclasses)):
        name = splitclasses[i].split("</a>")[0]
        link = splitclasses[i-1].split('<a href=" ')[1].replace('&url="', "")
        try:
            teacher = splitclasses[i].split(
                "</a>")[1].split(";&nbsp;&nbsp;</span>")[0].split("'name'>")[1]
        except:
            teacher = ""
        print(name, link, teacher)
        classes.append({
            "name": name,
            "link": link,
            "teacher": teacher,
            "courseId": link.split("Course&id=")[-1]
        })
    return classes


def getBbClassPage(userId, courseId):
    document = db.list_documents("users", "users", queries=[
                                 Query.equal("id", userId)])
    if document['total'] == 0:
        return None
    document = document['documents'][0]
    cookie = document['bbcookie']
    url = f"https://northallegheny.blackboard.com/webapps/blackboard/content/listContent.jsp?course_id={courseId}"

    payload = {}
    headers = {
        'Cookie': cookie,
        'Origin': 'https://northallegheny.blackboard.com',
        'Referer': 'https://northallegheny.blackboard.com/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    try:
        slidesLink = "https://docs.google.com/presentation" + \
            response.text.split(
                "https://docs.google.com/presentation")[1].split('"')[0]
    except Exception as e:
        print(e)
        slidesLink = ""

    return slidesLink

API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
headers = {"Authorization": f"Bearer {os.environ['HUGGINGFACE_TOKEN']}"}


def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()


def checkSim(name):
    assignments = db.list_documents("users", "assignments")
    documents = []
    for assign in assignments['documents']:
        documents.append(assign)
        while True:
            if assignments['total'] > len(documents):
                assignments = db.list_documents("users", "assignments", queries=[
                                                Query.offset(len(documents)-1), Query.limit(100)])
                for assign in assignments['documents']:
                    documents.append(assign)
            else:
                break
    assignments = documents
    for assign in assignments:
        outputs = query({
            "inputs": {
                "source_sentence": name,
                "sentences": [
                        assign['name']
                        ]
            },
        })
        if outputs[0] > 0.9:
            return True
    return False

def propagate():
    allClasses = db.list_documents("users", "classes")
    documents = []
    for userclass in allClasses['documents']:
        documents.append(userclass)
        while True:
            if allClasses['total'] > len(documents):
                allClasses = db.list_documents("users", "classes", queries=[
                                               Query.offset(len(documents)-1)])
                for userclass in allClasses['documents']:
                    documents.append(userclass)
            else:
                break

    for userclass in documents:
        if userclass['propagateAutomatically']:
            print(userclass['className'], userclass['userId'])
            slidesLink = getBbClassPage(
                userclass['userId'], userclass['courseId'])
            if slidesLink:
                assignments = gpt_ify_classes(slidesLink)
                for name, due in assignments.items():
                    if checkSim(name): continue
                    print(name, due, userclass['className'])
                    now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z')
                    db.create_document("users", "assignments", "unique()", {
                        "id": getId("assignments"),
                        "name": name,
                        "added": now,
                        "due": due.strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                        "classId": userclass['id'],
                        "userId": userclass['userId']
                    })


def getId(collection): return db.list_documents(
    "users", collection)['total'] + 1


def getUserClasses(userId):
    classes = db.list_documents("users", "classes", queries=[
                                Query.equal("userId", userId)])
    return classes['documents']


def getUserInfo(userId):
    user = db.list_documents("users", "users", queries=[
                             Query.equal("id", userId)])
    return user['documents'][0]


CARRIER_GATEWAYS = {
    "att": "@mms.att.net",
    "tmobile": "@tmomail.net",
    "verizon": "@vtext.com",
    "sprint": "@messaging.sprintpcs.com",
    "visible": "@vtext.com",
    "cricket": "@mms.cricketwireless.net",
    "googlefi": "@msg.fi.google.com",
    "metropcs": "@mymetropcs.com",
    "mint": "@tmomobile.net",
    "xfinity": "@vtext.com",
}


def send_email(recipient, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = recipient
    server = smtplib.SMTP_SSL("smtp.sendgrid.com", 465)
    server.login("apikey", PASSWORD)
    server.send_message(msg)
    server.quit()


def send_gmail(recipient, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = f"StudentMate <{os.environ['EMAIL']}>"
    msg["To"] = recipient
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(os.environ['EMAIL'], os.environ['EMAIL_PASSWORD'])
    server.send_message(msg)
    server.quit()


def sendText(phone, carrier, message):
    gateway = CARRIER_GATEWAYS[carrier]
    send_email(recipient=f"{phone}{gateway}",
               subject='StudentMate Notification', body=message)


def remind():
    return
    assignments = db.list_documents("users", "assignments")
    documents = []
    for assign in assignments['documents']:
        documents.append(assign)
        while True:
            if assignments['total'] > len(documents):
                assignments = db.list_documents("users", "assignments", queries=[
                                                Query.offset(len(documents)-1), Query.limit(100)])
                for assign in assignments['documents']:
                    documents.append(assign)
            else:
                break

    for assign in documents:
        due = datetime.datetime.strptime(
            assign['due'], '%Y-%m-%dT%H:%M:%S.%f%z')
        overdue = due < datetime.datetime.now().replace(tzinfo=due.tzinfo)
        if overdue and not assign['notified'] and not assign['completed']:
            print(assign)
            user = getUserInfo(assign['userId'])
            send_gmail(user['email'], 'StudentMate Notification',
                       f'Your assignment {assign["name"]} is overdue!')
            if user['phoneNumber'] and user['phoneCarrier']:
                sendText(user['phoneNumber'], user['phoneCarrier'],
                         f'Your assignment {assign["name"]} is overdue!')
            db.update_document("users", "assignments", assign['$id'], {
                "id": assign['id'],
                "name": assign['name'],
                "added": assign['added'],
                "due": assign['due'],
                "classId": assign['classId'],
                "userId": assign['userId'],
                "completed": assign['completed'],
                "notified": True
            })
