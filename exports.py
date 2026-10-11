"""Portable, testable sharing and calendar exports."""
import base64, json, zlib, hashlib
from datetime import datetime
from services import AREA

def pack_share(area_id,names,params):
 record={'v':1,'a':area_id,'s':names,'start':params['start'],'end':params['end'],
         'mode':params['mode'],'interests':params['interests']}
 raw=json.dumps(record,ensure_ascii=False,separators=(',',':')).encode('utf8')
 return base64.urlsafe_b64encode(zlib.compress(raw,9)).decode().rstrip('=')

def unpack_share(token):
 if not token or len(token)>7000:return None
 try:
  raw=zlib.decompress(base64.urlsafe_b64decode(token+'='*(-len(token)%4)))
  if len(raw)>15000:return None
  data=json.loads(raw)
  if data.get('v')!=1 or data.get('a') not in AREA or not isinstance(data.get('s'),list):return None
  data['s']=[str(x) for x in data['s']][:20]
  return data
 except (ValueError,TypeError,KeyError,zlib.error):return None

def ics_text(plan,ordered):
 lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Mulkkobang//Sea Walk//KO','CALSCALE:GREGORIAN','METHOD:PUBLISH']
 def esc(s):return str(s).replace('\\','\\\\').replace(',','\\,').replace(';','\\;').replace('\n','\\n')
 for n,(p,item) in enumerate(zip(ordered,plan['schedule'])):
  starts=datetime.strptime('2027-01-09 '+item['arrive'],'%Y-%m-%d %H:%M').strftime('%Y%m%dT%H%M%S')
  ends=datetime.strptime('2027-01-09 '+item['leave'],'%Y-%m-%d %H:%M').strftime('%Y%m%dT%H%M%S')
  lines+=['BEGIN:VEVENT',f'UID:mulkkobang-{n}-{hashlib.md5(p["name"].encode()).hexdigest()[:10]}@dajeongsea',
    'DTSTAMP:20261011T000000Z',f'DTSTART;TZID=Asia/Seoul:{starts}',f'DTEND;TZID=Asia/Seoul:{ends}',
    f'SUMMARY:{esc(p["name"])}',f'LOCATION:{esc(p["address"])}',
    f'DESCRIPTION:{esc(p["description"]+" / "+p["notice"])}','END:VEVENT']
 lines.append('END:VCALENDAR')
 return '\r\n'.join(lines)+'\r\n'
