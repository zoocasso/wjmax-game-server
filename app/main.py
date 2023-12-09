# -*- coding: utf-8 -*-

import sys
sys.path.append("./")

from app import db_session

import json
import uvicorn
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, status
import asyncio

## fastapi 인스턴스 저장
app = FastAPI()

# class InsertUserForm(BaseModel):
#     device_id : str

# class InsertPlaylogForm(BaseModel):
#     music_key: str
#     device_id: str
#     total_score: int

class InsertPlayCountForm(BaseModel):
    device_id : str
    count_log : str

# @app.post("/insert_user")
# async def insert_user(request:Request, insert_user_form:InsertUserForm):
#     insert_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
#     device_id = insert_user_form.device_id
#     db_session.insert_user_tb(device_id,insert_time)
#     db_session.db_commit()

# @app.post("/insert_playlog")
# async def insert_playlog(request:Request, insert_playlog_form:InsertPlaylogForm):
#     insert_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
#     music_key = insert_playlog_form.music_key
#     device_id = insert_playlog_form.device_id
#     total_score = insert_playlog_form.total_score
#     db_session.insert_playlog_tb(music_key, device_id, total_score, insert_time)
#     db_session.db_commit()

@app.post("/insert_playcount")
async def insert_playcount(request:Request, insert_playcount_form:InsertPlayCountForm):
    insert_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    device_id = insert_playcount_form.device_id
    count_log = insert_playcount_form.count_log
    try:
        # user insert
        db_session.insert_user_tb(device_id,insert_time)
        db_session.db_commit()

        # playcount insert
        count_log = count_log.replace("'",'"')
        playDatas = json.loads(count_log)["playDatas"]
        
        for i in range(len(playDatas)):
            playData = playDatas[i].split("*")

            title = playData[0]
            if title == "오르트 구름":
                title = "Oort Cloud"
            music_key = db_session.select_music_key(title)
            music_key_start = music_key.fetchall()[0][0]
            
            for j in range(8):
                print(device_id)
                print(music_key_start+j)
                print(playData[j+1])
                db_session.insert_playcount_tb(device_id,music_key_start+j,playData[j+1])
        db_session.db_commit()
        db_session.db_close()
    except:
        pass




# class SelectUserForm(BaseModel):
#     device_id : str

# class SelectLogForm(BaseModel):
#     device_id : str
#     music_key : str

# @app.post("/select_user")
# async def select_user(request:Request, select_user_form:SelectUserForm):
#     device_id = select_user_form.device_id
#     user_info = db_session.select_user_tb(device_id)
#     db_session.db_commit()

#     result_row = user_info.fetchall()
#     return str(result_row[0][0])

# @app.post("/select_playlog")
# async def select_playlog(request:Request, select_playlog_form:SelectLogForm):
#     device_id = select_playlog_form.device_id
#     music_key = select_playlog_form.music_key
#     playlog_info = db_session.select_playlog_tb(device_id, music_key)
#     db_session.db_commit()

#     result_row = playlog_info.fetchall()
#     return str(result_row)



@app.get("/")
async def main(request:Request):
    if 1 == 1:
        raise HTTPException(status_code=404, detail="Page Not Found")
    return True

if __name__ == "__main__":
    uvicorn.run("main:app", host = '127.0.0.1', port = 8000, reload=True)