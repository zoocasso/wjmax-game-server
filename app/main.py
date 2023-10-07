# -*- coding: utf-8 -*-

import sys
sys.path.append("./")

from app import db_session

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request

## fastapi 인스턴스 저장
app = FastAPI()

class Login_form(BaseModel):
    user_key : str
    nickname : str
    device_id : str

@app.post("/users_tb")
async def insert(request:Request, login_form:Login_form):
    db_session.insert_into_table_value(login_form)
    return "complete Insert data"

class Select_form(BaseModel):
    user_key : str

@app.post("/select")
async def main(request:Request, select_form:Select_form):
    db_session.select_user_tb(select_form)
    return "complete Selct data"

@app.post("/db_commit_and_close")
async def db_commit_and_close():
    db_session.db_commit_and_close()

@app.get("/")
async def main(request:Request):
    return "[WJMAX OFFICAL SERVER] 왁제이맥스를 즐겨주셔서 감사합니다"

if __name__ == "__main__":
    uvicorn.run(app, host = '127.0.0.1', port = 8000)