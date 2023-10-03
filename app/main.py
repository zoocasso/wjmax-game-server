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


@app.post("/row_insert")
async def row_insert(request:Request, row_form:Row_form):
    print(row_form)
    mysql_session = db_session.mysql_session()
    mysql_session.insert_into_table_value(row_form)
    mysql_session.db_close()
    return "complete insert data"

@app.get("/")
async def main(request:Request):
    mysql_session = db_session.mysql_session()
    mysql_session.db_close()
    return "wakjmax main page"

if __name__ == "__main__":
    uvicorn.run(app, host = '127.0.0.1', port = 8000)