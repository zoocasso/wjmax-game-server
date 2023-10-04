# -*- coding: utf-8 -*-

import sys
sys.path.append("./")

from app import db_session

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request

## fastapi 인스턴스 저장
app = FastAPI()

class Row_form(BaseModel):
    user : str
    music : str
    artist : str
    key_gubun : int
    level : int
    mod : int
    max_combo : int
    hit_score : int
    score5 : int
    score4 : int
    score3 : int
    score2 : int
    score1 : int
    rate : int
    total_score : int
    item : int
    gear : int
    btn_sound : int
    speed : int
    option : str



@app.post("/insert")
async def insert(request:Request, insert_form:Insert_form):
    print(insert_form)
    mysql_session = db_session.mysql_session()
    mysql_session.insert_user_tb(insert_form)
    mysql_session.db_close()
    return "complete insert data"

class Select_form(BaseModel):
    user : str

@app.post("/select")
async def main(request:Request, select_form:Select_form):
    mysql_session = db_session.mysql_session()
    mysql_session.select_user_tb(select_form)
    mysql_session.db_close()
    return "wakjmax main page"

@app.get("/")
async def main(request:Request):
    mysql_session = db_session.mysql_session()
    mysql_session.db_close()
    return "[wjmax site] please do not 돚거"

if __name__ == "__main__":
    uvicorn.run(app, host = '127.0.0.1', port = 8000)