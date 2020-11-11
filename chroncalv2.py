import pprint

import tempfile

import pickle
import requests
import os.path
import os

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dateutil.parser import parse

from datetime import datetime, timedelta
from pytz import timezone
import pytz
import time
from dotenv import load_dotenv
import json

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/calendar.readonly']

croncycle=10800 #maybe will need to change this number

load_dotenv('/home/yak/.env')


def main():

    creds = None

    if os.path.exists('/home/yak/token.pickle'):
        with open('/home/yak/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('yc-credentials.json', SCOPES)
            creds = flow.run_local_server(port=9000)
        with open('/home/yak/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    cal = build('calendar', 'v3', credentials=creds)

    now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming week')
    events_result = cal.events().list(calendarId='o995m43173bpslmhh49nmrp5i4@group.calendar.google.com', timeMin=now,timeMax=(datetime.utcnow()+timedelta(days=7)).isoformat()+ 'Z',
                                        singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    pp = pprint.PrettyPrinter(indent=1)
    #pp.pprint(events_result)
    if not events:
        print('No upcoming events found.')

    for event in events:
        start = parse(event['start'].get('dateTime', event['start'].get('date')))
        seconds2go=int((start-datetime.utcnow().astimezone()).total_seconds())
        days, hours, minutes = int(seconds2go //(3600*24)), int(seconds2go // 3600), int(seconds2go // 60 % 60)
        print('starts in:', seconds2go, event['summary'], event['reminders'])
        if event['reminders'].get('useDefault',False):
            reminders=events_result['defaultReminders']
        else:
            reminders=event['reminders'].get('overrides',[])
        for rems in reminders:
            print('checking reminders')
            ttr=seconds2go-(int(rems['minutes'])*60)
            if ttr//croncycle==1:
                thetz=timezone('US/Pacific')
                print(thetz)
                thestring=start.astimezone(thetz).strftime('%a %b %d, %Y %I:%M %p (%Z)')
                y="Heads up! @here "+event['summary']+'  '+thestring+'\n\n'
                y=y+event['description']+'\n\n'
                ts=''
                if(days>0):
                    ts=ts+str(days) + ' days and '
                if(hours>0):
                    ts=ts+str(hours) + ' hours and '
                if(minutes>0):
                    ts=ts+str(minutes) + ' minutes.'
                if(days==0 and hours==0 and minutes<=2):
                    ts=' **NOW**'
                y=y+'starts in about: '+ ts
                print(y)
                payload = {"content": y}
                atm=(ttr) // 60
                f=tempfile.NamedTemporaryFile(mode='w+',delete=False)
                json.dump(payload,f)
                print('dumped')
                f.flush()
                os.system('''at now +{} minutes <<END
exec >>~/robot/gmail_hook/alogfile 2>&1
set -x
set -v
curl -d "@{}" -H "Content-Type: application/json" -X POST $TEST_HOOK 
rm {}
END'''.format(atm,f.name,f.name))



if __name__ == '__main__':
    main()
