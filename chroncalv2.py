#the one-run file that generates reminders
#basically, it reads google calander (first making sure the token is up to date) to obtain events in next week. this is best way to deal with DST problems
#it also identifies the reminders for each event (or the default ones)
#each reminder (stored in a temporary file) is generated at the correct time (at command) and sent to discord (webhook on events channel)
#this program is itself called by cron every 3 hours on the 10 min mark.
# program needs 2 cycles to send reminders. so it will only send reminders if the event is at least 6 hours from now.

#TEST_HOOK is an .env variable which is a webhook for discord event channel
#CALID is not (yet) an enviromental variable
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
CALID='o995m43173bpslmhh49nmrp5i4@group.calendar.google.com'
croncycle=10800 #maybe will need to change this number

load_dotenv('/home/yak/.env')


def main():
##this part taken from google quick start. it tries to use locally stored credentials, asked for new ones if missing or if they expired
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
##connect to calender service - to ask for next meetings. ask for next 7 days.

    cal = build('calendar', 'v3', credentials=creds)

    now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming week') #these all go to debugging file
    events_result = cal.events().list(calendarId=CALID, showDeleted=False, timeMin=now,timeMax=(datetime.utcnow()+timedelta(days=7)).isoformat()+ 'Z',
                                        singleEvents=True,
                                        orderBy='startTime').execute()
##results include event items and some other stuff
    events = events_result.get('items', [])
    pp = pprint.PrettyPrinter(indent=1)
    #pp.pprint(events_result) # for debugging
	
    if not events:
        print('No upcoming events found.')

    for event in events:
##start with figuring for each event how many seconds to go
        start = parse(event['start'].get('dateTime', event['start'].get('date')))
        print(event['summary'],start,datetime.utcnow(), event['status'])
        if (event['status']=="canceled" or event['summary'].startswith("Canceled:")):
            continue
        seconds2go=int((start-datetime.utcnow().astimezone()).total_seconds())
        days, hours, minutes = int(seconds2go //(3600*24)), int(seconds2go // 3600), int(seconds2go // 60 % 60) #obselete, used for debugging
        print('starts in:', seconds2go, event['summary'], event['reminders'])
##figure out reminders - either per event or global
        if event['reminders'].get('useDefault',False):
            reminders=events_result['defaultReminders']
        else:
            reminders=event['reminders'].get('overrides',[])
			
        for rems in reminders:
##figure out when reminder needs to be announced
            print('checking reminders', rems)
            rem_s=int(rems['minutes'])*60
            ttr=seconds2go-rem_s
            days, hours, minutes = int(rem_s //(3600*24)), int((rem_s // 3600)%24), int(rem_s // 60 % 60)
            print(ttr,ttr//croncycle)

##see if it needs to be announced within the next cycle, if yes, build the announcement string
            if ttr//croncycle==1:
##convert time to PST (the YC standard)
                thetz=timezone('US/Pacific')
                print(thetz)
                thestring=start.astimezone(thetz).strftime('%a %b %d, %Y %I:%M %p (%Z)')
                y="Heads up! @here "+event['summary'].replace("and Yak Collective","")+'  '+thestring+'\n\n'
				
##some events have no description enetered, only title
                y=y+event.get('description','No details')+'\n\n'
                ts=''
##generate time string (ts)
                if(days>0):
                    ts=ts+str(days) + ' days '
                if(hours>0):
                    if(days>0):
                        ts=ts+' and '
                    ts=ts+str(hours) + ' hours '
                if(minutes>0):
                    if (hours>0 or days >0):
                        ts=ts+ ' and '
                    ts=ts+str(minutes) + ' minutes.'
                if(days==0 and hours==0 and minutes<=2):
                    ts=' **NOW**'
                y=y+'starts in about: '+ ts
                print(y)
                payload = {"content": y}
##string is ready. now use "at" linux system function to send messgae using curl to predfined webhook of discord. make a temporary file that deletes itself after the "at" command
                atm=(ttr) // 60
                f=tempfile.NamedTemporaryFile(mode='w+',delete=False)
                json.dump(payload,f)
                print('dumped')
                f.flush()
                os.system('''at now +{} minutes <<END
exec >>~/robot/gmail_hook/alogfile 2>&1
date
cat {}
set -x
set -v
curl -d "@{}" -H "Content-Type: application/json" -X POST $TEST_HOOK 
rm {}
END'''.format(atm,f.name,f.name,f.name))



if __name__ == '__main__':
    main()
