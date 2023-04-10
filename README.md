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

## Run Locally
> **Note** StudentMate is currently locked to North Allegheny Students only because it only works with how NA has Blackboard set up.

If you'd like to run your own instance of StudentMate and/or change how it works to use your LMS, follow le instructions below:
1. Clone the repo
```bash
git clone https://github.com/CoolCoderSJ/StudentMate.git
```
2. Copy the `.env.example` file to `.env` and fill it out.

The project uses Appwrite, so you will need to get an appwrite project set up.

4. The chromedriver supplied is for ARM64 machines only. Download the correct chromedriver for your machine from [Electron Releases](https://github.com/electron/electron/releases). Extract the chromedriver binary into the project root and replace the current binary with it. 
5. Make sure you have chromium-browser installed

On Debian-based distros:
```bash
sudo apt update
sudo apt install chromium-browser
```
On Windows and macOS:
Download the binary from https://download-chromium.appspot.com/ and make sure the binary is in your PATH.

4. Install Python and its Requirements
Make sure you have Python 3 installed.
