
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
import discord
from dotenv import load_dotenv
import json

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

client = discord.Client()

load_dotenv('/home/yak/.env')


@client.event
async def on_ready(): 
    print('should never reach here, as decide dto use dicord webhook instead')
    print('We have logged in as {0.user}'.format(client),  client.guilds)
    channel = client.get_channel(704047116086935602)#calendar events channel
    #await channel.send('test message')
    #better - do not connect to discord at all. just use ADY_WEBHOOK using https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks and https://discord.com/developers/docs/resources/webhook

    
    
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
    reminders={}
    dones=[]
    beingdone=[]
    with open('/home/yak/lastmess','r') as f:
        dones=f.readlines()
    for message in messages:
            beingdone.append(message['id']+'\n')
            print(message['id'])
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            heads=dict([y for y in map(lambda x: (x['name'],x['value']) if (x['name']=='Subject' or x['name']=='From' or x['name']=='Date') else None, msg['payload']['headers']) if y])
            #print('here is the date on teh gmail - mayeb it tells us correct timezzone?',heads['Date'])
            heads['Date']=time.mktime(parsedate(heads['Date']))
            #print(heads ,msg['snippet'])
            #print('arrived in last 100 seconds:',heads['Date']>int(time.time()-100))
            isnew=message['id'] not in dones
            iscal=heads['From'].startswith('Google Calendar')
            print('is calendar:',iscal,'is new:',isnew, message['id'], heads['Date'])
            #print('msg:',msg['payload'])
            if iscal and isnew: #gmail/gcal notifications have a format we can guess.
                content = msg['payload']['parts'][0]['body']['data']
                msg_body = base64.urlsafe_b64decode(content).decode('utf-8')
                #print("message body in plain text? ",msg_body)
                if heads['Subject'].startswith('Notification'):
                    sum=heads['Subject'][13:heads['Subject'].find('@')].strip()
                    reminders[sum]=(heads['Subject'],msg_body)
                    print('got one:',reminders[sum])
    print('dones:',dones)
    print('beingdone:',beingdone,len(messages))
    with open('/home/yak/lastmess','w') as f:
        f.writelines(beingdone)

    request = {  'labelIds': ['INBOX'],  'topicName': 'projects/yc-cal-reminders-1604260822408/topics/hook' }
    print(service.users().watch(userId='me', body=request).execute())#needs to be renewed daily. or at least weekly. but we get enough reminders to make this happen on its own. we hope
#    discord_token=os.getenv('CAL_DISCORD_KEY')
#    client.run(discord_token)
    #print('going to send:',[x for x in reminders], 'to:',704047116086935602)
    url = os.getenv('TEST_HOOK')
    icalurl='https://calendar.google.com/calendar/ical/o995m43173bpslmhh49nmrp5i4%40group.calendar.google.com/public/basic.ics'
    #icalfile=requests.get(icalurl) #for now we just focus on events
    es=events(icalurl)

    for r in reminders:
        x=reminders[r]
        y="Heads up! @here "+x[0][13:]+'\n\n'#+x[1]
        ttlpos=x[1].find('\nTitle:')
        nlat=x[1].find('\n',ttlpos+1)
        ttl=x[1][ttlpos+7:nlat]
        #y=y+"\ntitle is maybe:"+ttl
        whenpos=x[1].find('\nWhen:')
        nlaw=x[1].find('\n',whenpos+1)
        whn=x[1][whenpos+6:nlaw]
        #y=y+"\nwhen is maybe:"+whn
        dtl=x[1][nlat+1:whenpos-1]
        #y=y+"\ndetails are maybe:"+dtl
        
        for z in es:
            if ttl.strip()==z.summary.strip():
                y=y+z.description[:-16]+'\n\n'
                tl=z.time_left()
                ts=''
                days, hours, minutes = tl.days, tl.seconds // 3600, tl.seconds // 60 % 60
                if(days>0):
                    ts=str(days) + ' days and '
                if(hours>0):
                    ts=ts+str(hours) + ' hours and'
                if(minutes>0):
                    ts=ts+str(minutes) + ' minutes.'
                if(days==0 and hours==0 and minutes<=0):
                    ts=' NOW'
                y=y+'starts in about (but see DST bug): '+ ts+'\n\n'
                break
        newwhen=x[0][x[0].find('@')+1:]
        rngs=newwhen.find('-')
        rnge=newwhen.find('(',rngs)
        newwhen=newwhen[:rngs-1].strip()
        print('extracted time:',newwhen, )
        t=datetime.strptime(newwhen,'%a %b %d, %Y %I%p')
        print('read time:',t)
        t1=timezone('US/Pacific').localize(t)
        print('localized time:',t1)
        dt=t1-datetime.now().astimezone()
        dt_t=dt.total_seconds()
        dth,dtm=dt_t //3600, dt_t // 60 % 60
        print('difference from now:',dt, dt_t, dth,":",dtm )
        if(dth>0):
            ts=str(int(dth)) + ' hours and '
        if(dtm>0):
            ts=ts+str(int(dtm)) + ' minutes.'
        if(dth==0 and dtm<=0):
            ts=' NOW'

        y=y+'new calculated time; event will start in about '+ts
        payload = {'content': y}
        headers = {'content-type': 'application/json'}
        req = requests.post(url, data=payload)#, headers=headers)
        print(req,req.text)#,r.json())


if __name__ == '__main__':
    main()
