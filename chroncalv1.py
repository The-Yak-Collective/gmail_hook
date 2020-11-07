

from icalevents.icalevents import events
import base64
import tempfile
import os
import email
from datetime import datetime
import time
from dotenv import load_dotenv
import json

remindseconds=[900,7200]
croncycle=7100 #maybe will need to change this number

load_dotenv('.env')

    
def main():

    url = os.getenv('TEST_HOOK')
    icalurl='https://calendar.google.com/calendar/ical/o995m43173bpslmhh49nmrp5i4%40group.calendar.google.com/public/basic.ics'

    es=events(icalurl)

        
    for z in es:
        print('event is',z.summary)
        tl=z.time_left()
        ts=''
        y="Heads up! @here "+z.summary+'  '+str(z.start)+'\n\n'
        days, hours, minutes, sl = tl.days, tl.seconds // 3600, tl.seconds // 60 % 60, tl.days*3600*24+tl.seconds
        for rm in remindseconds:
            if True: #rm<croncycle and sl<croncycle:
                y=y+z.description[:-16]+'\n\n'
                if(days>0):
                    ts=str(days) + ' days and '
                if(hours>0):
                    ts=str(hours) + ' hours and'
                if(minutes>0):
                    ts=str(minutes) + ' minutes.'
                if(days==0 and hours==0 and minutes<=0):
                    ts=' NOW'
                y=y+'starts in about: '+ ts
                payload = {"content": y}
                atm=1 #(sl-rm) // 60
                f=tempfile.TemporaryFile(mode='w')
                json.dump(payload,f)
                os.system('''at now +{} minutes <<END
exec >>~/robot/gmail_hook/alogfile 2>&1
set -x
set -v
curl -d "@{}" -H "Content-Type: application/json" -X POST $TEST_HOOK 
END'''.format(atm,f.name))

if __name__ == '__main__':
    main()
