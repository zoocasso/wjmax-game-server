# 노가다 두개재 
# 오직 DB 입력만을 위한 temp code

import pymysql

db = pymysql.connect(host='REDACTED_HOST', port=3306, user='root', passwd='REDACTED_PASSWORD', db='wjmax_db', charset='utf8')

cursor = db.cursor()

key_gubun = 4

category = 'fixedmember'

#roentgenium,chunyang
#jururu, viichan, lilpa, jingburger, ine, gosegu

artist = ''

name = "dancewithme"
difficulty = [1,3,11,16]

for i in difficulty:
    sql = f"insert into music_tb (`name`, `key_gubun`, `difficulty`, `artist`, `category`) values ('{name}',{key_gubun},{i},'{artist}','{category}')"
    cursor.execute(sql)
    db.commit()


db.close()