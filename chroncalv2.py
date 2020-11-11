import pprint
import icalendar as ical
from icalevents.icalevents import events
import base64
import pickle
import requests
import os.path
import os
import email
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.utils import parsedate
from datetime import datetime, timedelta
from pytz import timezone
import pytz
import time
from dotenv import load_dotenv
import json

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/calendar.readonly']


load_dotenv('/home/yak/.env')

    
    
def main():

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('/home/yak/token.pickle'):
        with open('/home/yak/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('yc-credentials.json', SCOPES)
            creds = flow.run_local_server(port=9000)
        # Save the credentials for the next run
        with open('/home/yak/token.pickle', 'wb') as token:
            pickle.dump(creds, token)


    cal = build('calendar', 'v3', credentials=creds)

    url = os.getenv('TEST_HOOK')

    now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = cal.events().list(calendarId='o995m43173bpslmhh49nmrp5i4@group.calendar.google.com', timeMin=now,timeMax=(datetime.utcnow()+timedelta(days=7)).isoformat()+ 'Z',
                                        singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(type(start), start)
        print('starts in:', datetime.now()-start, event['summary'], event.reminders)
    pp = pprint.PrettyPrinter(indent=1)
    pp.pprint(events_result)
    print(events_result.defaultReminders)
    #req = requests.post(url, data=payload)#, headers=headers)
    #print(req,req.text)#,r.json())


if __name__ == '__main__':
    main()
