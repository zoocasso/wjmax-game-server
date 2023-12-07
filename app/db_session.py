import config

import pandas as pd
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table, MetaData
from sqlalchemy import insert, select

user=config.DATABASE_CONFIG['user']
password=config.DATABASE_CONFIG['password']
host=config.DATABASE_CONFIG['host']
port=config.DATABASE_CONFIG['port']
dbname=config.DATABASE_CONFIG['dbname']

MYSQLALCHEMY_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"
engine = create_engine(MYSQLALCHEMY_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
db = SessionLocal()

metadata = MetaData()
user_tb = Table("user_tb", metadata, autoload_with=engine)
music_tb = Table("music_tb", metadata, autoload_with=engine)
playlog_tb = Table("playlog_tb", metadata, autoload_with=engine)

def insert_music_tb(insert_music_form):
    insert_music_tb_sql = insert(music_tb).values(name=f'{insert_music_form.name}',key_gubun=f'{insert_music_form.key_gubun}',difficulty=f'{insert_music_form.difficulty}',artist=f'{insert_music_form.artist}',category=f'{insert_music_form.category}')
    db.execute(insert_music_tb_sql)

def insert_user_tb(insert_user_form):
    insert_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    insert_user_tb_sql = insert(user_tb).values(device_id=f'{insert_user_form.device_id}', insert_date =f'{insert_time}')
    db.execute(insert_user_tb_sql)

def select_user_tb(select_user_form):
    select_user_tb_sql = select(user_tb).where(user_tb.c.device_id == select_user_form.device_id)
    result = db.execute(select_user_tb_sql)
    return result

def insert_playlog_tb(insert_playlog_form):
    insert_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    insert_playlog_tb_sql = insert(playlog_tb).values(music_key=f'{insert_playlog_form.music_key}', user_key=f'{insert_playlog_form.user_key}', total_score=f'{insert_playlog_form.total_score}', insert_date =f'{insert_time}')
    db.execute(insert_playlog_tb_sql)

def select_playlog_tb(select_playlog_form):
    select_playlog_tb_sql = select(playlog_tb).where(playlog_tb.c.user_key == select_playlog_form.user_key).where(playlog_tb.c.music_key == select_playlog_form.music_key)
    result = db.execute(select_playlog_tb_sql)
    return result
    
def db_commit_and_close():
    db.commit()
    # engine.close()