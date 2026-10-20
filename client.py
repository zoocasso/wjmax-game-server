"""Sends one play-count report the way the game client does, for trying the server locally.

uvicorn app.main:app --reload        # in one terminal, with DATABASE_URL set
python client.py                     # in another
"""

import json
import sys
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/insert_playcount"

# the client sends the log as a string with single quotes; counts are per chart, eight per song
count_log = str({"playDatas": ["Oort Cloud*3*1*0*0*2*0*0*0", "오르트 구름*1*0*0*0*0*0*0*0"]})
body = json.dumps({"device_id": "local-test-device", "count_log": count_log}).encode()

req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as res:
    print(res.status, res.read().decode())
