# StudentMate
An AI-based approach to remembering assignments.

## What is StudentMate?
StudentMate is a to-do list platform that uses AI to automatically fetch assignments from my school district's LMS. It then notifies people of the assignments so that students don't need to remember to check teacher pages for assignments.

## How does it work?
After setup, Studentmate scrapes our LMS (LMS will now be referred to as Blackboard, the name of the LMS.) using access it gains through a browser extension. 
- StudentMate cycles through each teacher page and looks for an agenda in the format of a Google Slides slidedeck. 
- It opens the slidedeck in a headless chromedriver instance, takes a screenshot, then runs it through OCR.
- It sends the text grabbed from the slidedeck to [YouChat](https://you.com/chat), a free alternative to ChatGPT, with a heavily customized prompt
- Finally, it reads YouChat's response and adds the assignments received to the database.
- When assignments are near due, StudentMate sends an email reminder, with an option to text reminders too.

## Some Pictures
![image](https://user-images.githubusercontent.com/53063247/230997454-70c9ad1a-ddcc-41c1-bbd0-951447464675.png) ![image](https://user-images.githubusercontent.com/53063247/230997591-062568d2-94fd-4160-968a-5851d0648c40.png) ![image](https://user-images.githubusercontent.com/53063247/230997685-604d630d-9898-463f-8918-e577f3aa7174.png) ![image](https://user-images.githubusercontent.com/53063247/230997773-bb57721f-1161-4b68-849a-2e4808669fc9.png)


## Run Locally
> **Note** StudentMate is currently locked to North Allegheny Students only because it only works with how NA has Blackboard set up.

If you'd like to run your own instance of StudentMate and/or change how it works to use your LMS, follow le instructions below:
### 1. Clone the repo
```bash
git clone https://github.com/CoolCoderSJ/StudentMate.git
```
### 2. Setup `.env`
To begin, copy `.env.example` to `.env`

#### Appwrite
The project uses [Appwrite](https://appwrite.io), so you will need to get an appwrite project set up. You can get private beta access to the cloud hosted instance @ https://appwrite.io/cloud, or host it yourself. 
- Change line 21 in `main.py` and line 28 in `utils.py` to your appwrite instance url, and change line 22 in `main.py` and line 29 in `utils.py` to your appwrite project ID. Finally, set the environment variable APPWRITE_API_KEY to your Appwrite server API key in `.env`

#### Google Oauth
- Setup a new Google Developer Project @ http://console.cloud.google.com/
- Create Oauth2 Credentials for the project
- Set the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env` to these credentials
- **If you need more help creating these credentials, follow this tutorial: https://developers.google.com/workspace/guides/create-credentials**

#### YouChat
- Get an API Key at https://api.betterapi.net/about/
- Fill out the api key as `YOU_API_KEY`in the `.env`

#### Email and SMS Notifications
To send email reminders, the project uses gmail SMTP. If you would like to use something else, you can configure the `send_email` function (View [here](https://github.com/CoolCoderSJ/StudentMate/blob/9463713e773679b4149d49ff2605beced0141b2b/utils.py#L285)) to use your SMTP settings and change [line 331 of `utils.py`](https://github.com/CoolCoderSJ/StudentMate/blob/9463713e773679b4149d49ff2605beced0141b2b/utils.py#L331) to use the send_email function instead.

If you would like to use Gmail SMTP, all you have to do is fill out `EMAIL` and `EMAIL_PASSWORD` in `.env`

##### SMS
To send emails StudentMate uses Gmail SMTP so that it uses my school email to bypass any district email filters. However, to text people, StudentMate uses Sendgrid (email-to-text) so that it can use the official email. If you are fine with Sendgrid, configure `SENDGRID_EMAIL` and `SENDGRID_PASSWORD` in the env file. Otherwise, configure the `send_email` function (View [here](https://github.com/CoolCoderSJ/StudentMate/blob/9463713e773679b4149d49ff2605beced0141b2b/utils.py#L285)) to use your SMTP settings instead. 

### Screeenly
Taking screenshots on the server consumes an immense amount of resources and therefore has to be done externally. This is done via Screeenly, a free screenshot API. To use it, set the `SCREENLY_API_KEY` in `.env` to your Screeenly API key. (Get one [here](https://screeenly.com/))

### Python
4. Install Python and its Requirements
- Make sure you have Python 3 installed.
- Install all dependencies by running 
```bash
pip install -r requirements.txt
```
### Run Server
6. Run the server using `python main.py`
