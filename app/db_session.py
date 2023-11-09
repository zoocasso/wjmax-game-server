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
test_tb = Table("test_tb", metadata, autoload_with=engine)

def insert_test_tb(test_form):
    test_tb_sql = insert(test_tb).values(test=f'{test_form.test}')
    db.execute(test_tb_sql)

def insert_music_tb(music_form):
    insert_music_tb_sql = insert(music_tb).values(name=f'{music_form.name}',key_gubun=f'{music_form.key_gubun}',difficulty=f'{music_form.difficulty}',artist=f'{music_form.artist}',category=f'{music_form.category}')
    db.execute(insert_music_tb_sql)

def insert_user_tb(signup_form):
    insert_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    insert_user_tb_sql = insert(user_tb).values(user_key=f'{signup_form.user_key}', device_id=f'{signup_form.device_id}', insert_date =f'{insert_time}')
    db.execute(insert_user_tb_sql)

def select_user_tb(select_form):
    select_user_tb_sql = select(user_tb).where(user_tb.name == f'{select_form.user_key}')
    result = db.execute(select_user_tb_sql)

def db_commit_and_close():
    db.commit()
    engine.close()