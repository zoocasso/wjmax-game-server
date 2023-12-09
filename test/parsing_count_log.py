import json
import pymysql
import pandas as pd

db = pymysql.connect(host='REDACTED_HOST', port=3306, user='root', passwd='REDACTED_PASSWORD', db='wjmax_db', charset='utf8')
cursor = db.cursor()

with open('message.txt','r',encoding='UTF8') as f:
    playDatas = json.loads(f.read())['playDatas']
    print(playDatas)
    
for i in range(len(playDatas)):
    playData = playDatas[i].split("*")

    ### user_key 조회하여 변수저장 로직 필요

    title = playData[0]
    if title == "오르트 구름":
        title = "Oort Cloud"
    select_sql = f"SELECT music_key FROM music_tb WHERE `name` = '{title}' LIMIT 1"
    cursor.execute(select_sql)
    db.commit()
    music_key_start = cursor.fetchone()[0]
    for j in range(8):
        print(f"INSERT INTO playcount_tb (`user_key`, `music_key`, `count`) values ({user_key},{music_key_start+j},{playData[j+1]})")