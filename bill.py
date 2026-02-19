# from ast import While
# from time import sleep, time
"""
bill.py – ตัว trigger ให้ Laravel (ip-qrcode-printer) ไปดึงข้อมูลแล้วปริ้น
Endpoints: /printpi, /printreceiptrecheck, /printconclusion, /printconclusionselectdate
"""
import time
import requests

REQUEST_TIMEOUT = 15
BILL_API_BASE = "http://127.0.0.2/api"


def api_get_safe(url, params=None):
    try:
        res = requests.get(url=url, params=params or {}, timeout=REQUEST_TIMEOUT)
        return res, None
    except requests.RequestException as e:
        return None, str(e)


def poll_once():
    endpoints = [
        ('printpi', 'print checkbill'),
        ('printreceiptrecheck', 'print receiptrecheck'),
        ('printconclusion', 'print conclusion'),
        ('printconclusionselectdate', 'print conclusionselectdate'),
        ('printconclusion', 'print printconclusion'),
    ]
    for path, label in endpoints:
        try:
            res, err = api_get_safe(f"{BILL_API_BASE}/{path}")
            if err:
                print(label, 'error:', err)
                continue
            if res.status_code == 200:
                print(label, res.status_code)
            elif res.status_code not in (204, 500):
                print(label, res.status_code)
        except Exception as e:
            print(label, 'error:', e)


if __name__ == "__main__":
    while True:
        poll_once()
        time.sleep(1)
