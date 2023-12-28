import config

import databases
import sqlalchemy
from fastapi import FastAPI
from pydantic import BaseModel
import time
# async def 에서 사용시 동기적으로 강제 전환
import asyncio
# async.sleep로 기존의 time.sleep를 async방식으로 동작

user = config.DATABASE_CONFIG['user']
password = config.DATABASE_CONFIG['password']
host = config.DATABASE_CONFIG['host']
port = config.DATABASE_CONFIG['port']
db_name = config.DATABASE_CONFIG['db_name']


DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

notes = sqlalchemy.Table(
    "temp",
    metadata,
    sqlalchemy.Column("idx", sqlalchemy.Integer, primary_key=True),
	sqlalchemy.Column("value", sqlalchemy.Integer),
)


engine = sqlalchemy.create_engine(
    DATABASE_URL
)
metadata.create_all(engine)


class NoteIn(BaseModel):
    value: int


class Note(BaseModel):
    idx: int
    value : int

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/a")
def a():
    print(1)
    time.sleep(1)
    print(1)
    time.sleep(1)
    print(1)
    time.sleep(1)
    print(1)
    time.sleep(1)
    print(1)

@app.get("/b")
def b():
    print(2)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(2)


@app.post("/notes/a", response_model=Note)
async def create_note(note: NoteIn):
    print('start')
    await asyncio.sleep(10)
    print('process')
    for i in range(1,101):
        query = notes.insert().values(value=i)
        last_record_id = await database.execute(query)
    print('end')
    return {**note.dict(), "idx": last_record_id}

@app.post("/notes/b", response_model=Note)
async def create_note(note: NoteIn):
    for i in range(101,201):
        query = notes.insert().values(value=i)
        last_record_id = await database.execute(query)
    return {**note.dict(), "idx": last_record_id}