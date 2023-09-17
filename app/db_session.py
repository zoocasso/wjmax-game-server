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
        self.cursor.execute("select * from test;")
        rows = self.cursor.fetchall()
        return rows

    def insert_into_table_value(self,row_form):
        sql = f"insert into `test` (`user`,`music`,`score`) VALUES ('{row_form.user}','{row_form.music}',{row_form.score});"
        self.cursor.execute(sql)
        self.connection.commit()
        

    def db_close(self):
        self.connection.close()