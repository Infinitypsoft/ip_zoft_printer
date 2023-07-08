# from ast import While
# from time import sleep, time
import time

import requests

while True:
    res = requests.get('http://127.0.0.2/api/printconclusion')
    print('print conclusion', res.status_code)
    res = requests.get('http://127.0.0.2/api/printconclusionselectdate')
    print('print conclusionselectdate', res.status_code)
    res = requests.get('http://127.0.0.2/api/printpi')
    print('print checkbill', res.status_code)
    res = requests.get('http://127.0.0.2/api/printreceiptrecheck')
    print('print receiptrecheck', res.status_code)
    # sleep(1)
    time.sleep(2)