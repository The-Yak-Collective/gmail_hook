
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
from datetime import datetime
import time
import discord
from dotenv import load_dotenv
import json

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

client = discord.Client()

load_dotenv('.env')
reminders=[]

@client.event
async def on_ready(): 
    print('should never reach here, as decide dto use dicord webhook instead')
    print('We have logged in as {0.user}'.format(client),  client.guilds)
    channel = client.get_channel(704047116086935602)#calendar events channel
    #await channel.send('test message')
    #better - do not connect to discord at all. just use ADY_WEBHOOK using https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks and https://discord.com/developers/docs/resources/webhook
    #here is example of posting to test server

    
    
def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('yc-credentials.json', SCOPES)
            creds = flow.run_local_server(port=9000)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    # Call the Gmail API
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
    else:
        print('labels found but lets save space')
            
    results= service.users().messages().list(userId="me", maxResults=5, labelIds=['INBOX']).execute()
    messages = results.get('messages', [])
    # print(messageheader)
    for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            heads=dict([y for y in map(lambda x: (x['name'],x['value']) if (x['name']=='Subject' or x['name']=='From' or x['name']=='Date') else None, msg['payload']['headers']) if y])
            print('here is the date on teh gmail - mayeb it tells us correct timezzone?',heads['Date'])
            heads['Date']=time.mktime(parsedate(heads['Date']))
            print(heads ,msg['snippet'])
            print('arrived in last 100 seconds:',heads['Date']>int(time.time()-100))
            iscal=heads['From'].startswith('Google Calendar')
            print('is calendar:',iscal)
            #print('msg:',msg['payload'])
            if iscal: #gmail/gcal notifications have a format we can guess.
                content = msg['payload']['parts'][0]['body']['data']
                msg_body = base64.urlsafe_b64decode(content).decode('utf-8')
                print("message body in plain text? ",msg_body)
                if heads['Subject'].startswith('Notification'):
                    reminders.append((heads['Subject'],msg_body))

    request = {  'labelIds': ['INBOX'],  'topicName': 'projects/yc-cal-reminders-1604260822408/topics/hook' }
    print(service.users().watch(userId='me', body=request).execute())#needs to be renewed daily. or at least weekly. but we get enough reminders to make this happen on its own. we hope
#    discord_token=os.getenv('CAL_DISCORD_KEY')
#    client.run(discord_token)
    print('going to send:',[x for x in reminders], 'to:',704047116086935602)
    url = os.getenv('TEST_HOOK')
    icalurl='https://calendar.google.com/calendar/ical/o995m43173bpslmhh49nmrp5i4%40group.calendar.google.com/public/basic.ics'
    icalfile=requests.get(icalurl)
    #print('got ical',icalfile,icalfile.text)
    es=events(icalurl)
    #print('just the events:',es)
    for y in es:
        print('time left for:', y.summary, y.time_left())
    for x in reminders:
        y="Heads up! @here "+x[0]+'\n\n'#+x[1]
        ttlpos=x[1].find('\nTitle:')
        nlat=x[1].find('\n',ttlpos+1)
        ttl=x[1][ttlpos+7:nlat]
        y=y+"\ntitle is maybe:"+ttl
        whenpos=x[1].find('\nWhen:')
        nlaw=x[1].find('\n',whenpos+1)
        whn=x[1][whenpos+6:nlaw]
        y=y+"\nwhen is maybe:"+whn
        dtl=x[1][nlat+1:whenpos-1]
        y=y+"\ndetails are maybe:"+dtl
        
        payload = {'content': y}
        headers = {'content-type': 'application/json'}
        r = requests.post(url, data=payload)#, headers=headers)
        print(r,r.text)#,r.json())
        newwhen=x[0][x[0].find('@')+1:]
        rngs=newwhen.find('-')
        rnge=newwhen.find('(',rngs)
        newwhen=newwhen[:rngs-1]+' '+newwhen[rnge:rnge+5]
        print('extracted time:',newwhen, 'need to convert 3 letter code to real offset; note it depend son machine locals AND pacific time has DST')
        #t=datetime.strptime(newwhen,'%a %b %d, %Y %I%p %z')
        #print('read time:',t)

if __name__ == '__main__':
    main()
