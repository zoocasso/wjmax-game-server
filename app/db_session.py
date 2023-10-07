import config

import pandas as pd
from sqlalchemy import create_engine,text
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

def insert_into_table_value(login_form):
    insert_user_tb_sql = insert(user_tb).values(user_key=f'{login_form.user_key}', nickname=f'{login_form.nickname}', device_id=f'{login_form.device_id}')
    db.execute(insert_user_tb_sql)

def select_user_tb(select_form):
    select_user_tb_sql = select(user_tb).where(user_tb.name == f'{select_form.user_key}')
    result = db.execute(select_user_tb_sql)

def db_commit_and_close():
    db.commit()
    db.close()