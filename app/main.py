# -*- coding: utf-8 -*-

import sys
sys.path.append("./")

from app import db_session

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, status

## fastapi 인스턴스 저장
app = FastAPI()

class TestForm(BaseModel):
    test : str

@app.post("/insert_test")
async def insert_test(request:Request, test_form:TestForm):
    db_session.insert_test_tb(test_form)
    return 1

class MusicForm(BaseModel):
    name : str
    key_gubun : int
    difficulty : int
    artist : str
    category : str

@app.post("/insert_music")
async def insert_music(request:Request, music_form:MusicForm):
    db_session.insert_music_tb(music_form)
    return 1

class SignupForm(BaseModel):
    user_key : str
    device_id : str

@app.post("/signup")
async def signup(request:Request, signup_form:SignupForm):
    db_session.insert_user_tb(signup_form)
    return 1

class Select_form(BaseModel):
    user_key : str

@app.post("/select_user")
async def main(request:Request, select_form:Select_form):
    db_session.select_user_tb(select_form)
    return "complete Selct data"

@app.post("/db_commit_and_close")
async def db_commit_and_close():
    db_session.db_commit_and_close()

@app.get("/")
async def main(request:Request):
    if 1 == 1:
        raise HTTPException(status_code=404, detail="Page Not Found")
    return True

if __name__ == "__main__":
    uvicorn.run("main:app", host = '127.0.0.1', port = 8000, reload=True)