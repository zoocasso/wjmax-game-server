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
    score : int


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
    uvicorn.run(app, host = '0.0.0.0', port = 8000)