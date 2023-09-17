# -*- coding: utf-8 -*-

import sys
sys.path.append("./")

import requests
import random

if __name__ == '__main__':
    url = 'http://REDACTED_HOST:8000/row_insert'
    headers = {"Content-Type":"application/json"}

    test_dict = dict()

    player_list = ['mogi','zoocasso','wakgood']
    music_list = {'A','B','C'}
    for i in range(30):
        for player in player_list:
            for music in music_list:
                test_dict['user'] = player
                test_dict['music'] = music
                test_dict['score'] = random.randint(200000,350000)
                res = requests.post(url, headers=headers, json=test_dict)