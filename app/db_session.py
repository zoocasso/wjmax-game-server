import config

import pymysql

import pandas as pd

class mysql_session:
    def __init__(self):
        self.connection = pymysql.connect(host=config.DATABASE_CONFIG['host'],
                                    user=config.DATABASE_CONFIG['user'],
                                    password=config.DATABASE_CONFIG['password'],
                                    database=config.DATABASE_CONFIG['dbname'],
                                    cursorclass=pymysql.cursors.DictCursor)
        self.cursor = self.connection.cursor()

    def select_all_from_finplot(self):
        self.cursor.execute("select * from user_tb;")
        rows = self.cursor.fetchall()
        return rows

    def insert_into_table_value(self,row_form):
        sql = f"insert into `user_tb` (`user`,`music`,`artist`,`key_gubun`,`level`,`mod`,`max_combo`,`hit_score`,`score5`,`score4`,`score3`,`score2`,`score1`,`rate`,`total_score`,`item`,`gear`,`btn_sound`,`speed`,`option`) VALUES ('{row_form.user}','{row_form.music}','{row_form.artist}',{row_form.key_gubun},{row_form.level},{row_form.mod},{row_form.max_combo},{row_form.hit_score},{row_form.score5},{row_form.score4},{row_form.score3},{row_form.score2},{row_form.score1},{row_form.rate},{row_form.total_score},{row_form.item},{row_form.gear},{row_form.btn_sound},{row_form.speed},'{row_form.option}');"
        self.cursor.execute(sql)
        self.connection.commit()
        
    def select_user_tb(self,select_form):
        sql = f"select * from user_tb where user={select_form.user};"
        self.cursor.execute(sql)

    def db_close(self):
        self.connection.close()