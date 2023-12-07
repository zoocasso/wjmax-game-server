# -*- coding: utf-8 -*-

import sys
sys.path.append("./")

from app import db_session

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, status

## fastapi 인스턴스 저장
app = FastAPI()

class InsertMusicForm(BaseModel):
    name : str
    key_gubun : int
    difficulty : int
    artist : str
    category : str

@app.post("/insert_music")
async def insert_music(request:Request, insert_music_form:InsertMusicForm):
    db_session.insert_music_tb(insert_music_form)
    return 1

class InsertUserForm(BaseModel):
    device_id : str

@app.post("/insert_user")
async def insert_user(request:Request, insert_user_form:InsertUserForm):
    db_session.insert_user_tb(insert_user_form)
    db_session.db_commit_and_close()

class InsertPlaylogForm(BaseModel):
    music_key: str
    user_key: str
    total_score: str

@app.post("/insert_playlog")
async def insert_playlog(request:Request, insert_playlog_form:InsertPlaylogForm):
    db_session.insert_playlog_tb(insert_playlog_form)
    db_session.db_commit_and_close()

class SelectUserForm(BaseModel):
    device_id : str

@app.post("/select_user")
async def select_user(request:Request, select_user_form:SelectUserForm):
    user_info = db_session.select_user_tb(select_user_form)
    db_session.db_commit_and_close()

    result_row = user_info.fetchall()
    return str(result_row)

class SelectLogForm(BaseModel):
    user_key : str
    music_key : str

@app.post("/select_playlog")
async def select_playlog(request:Request, select_playlog_form:SelectLogForm):
    playlog_info = db_session.select_playlog_tb(select_playlog_form)
    db_session.db_commit_and_close()

    result_row = playlog_info.fetchall()
    return str(result_row)

# @app.post("/db_commit_and_close")
# async def db_commit_and_close():
#     db_session.db_commit_and_close()

@app.get("/")
async def main(request:Request):
    if 1 == 1:
        raise HTTPException(status_code=404, detail="Page Not Found")
    return True

if __name__ == "__main__":
    uvicorn.run("main:app", host = '127.0.0.1', port = 8000, reload=True)