# !/usr/bin/python
# -- coding: utf-8 --
import json
import sys
from time import sleep
from escpos.printer import Network
import requests
from PIL import Image, ImageFont, ImageOps, ImageDraw
# import mysql.connector
from multiprocessing import Process
from datetime import datetime

# Timeout (วินาที) – ป้องกัน API/เครื่องปริ้นค้าง
REQUEST_TIMEOUT = 15
IMAGE_TIMEOUT = 20
PRINTER_TIMEOUT = 20
# เวลาออเดอร์เยอะ เซิร์ฟเวอร์อาจตอบช้า – ใช้ timeout ยาวกว่าเฉพาะ order-to-kitchen
KITCHEN_REQUEST_TIMEOUT = 30

def api_get_json(url, params=None, timeout=None):
    """เรียก GET แล้วคืน (data, None) หรือ (None, error_msg). timeout ถ้าไม่ระบุใช้ REQUEST_TIMEOUT"""
    try:
        t = timeout if timeout is not None else REQUEST_TIMEOUT
        res = requests.get(url=url, params=params or {}, timeout=t)
        text = (res.text or "").strip()
        if res.status_code != 200:
            return None, "API HTTP %s" % res.status_code
        if not text:
            return None, None
        try:
            return res.json(), None
        except ValueError as e:
            return None, "Invalid JSON (%s)" % e
    except requests.RequestException as e:
        return None, str(e)

ip_host = "http://45.118.133.135/ipsoftapi/"
# ip_host = "http://172.104.184.60/ipsoftapi/"
# ip_host = "http://165.22.59.74/"
#ip_host = "http://localhost:8000/"

printer_ipAddress = "192.168.1.252"

# โหลดรายการเครื่องปริ้น (retry ตอนรันด้วย Task Scheduler / เปิดเครื่องใหม่)
STARTUP_RETRY = 12
STARTUP_RETRY_DELAY = 10
ip_printer_data = None
for attempt in range(1, STARTUP_RETRY + 1):
    try:
        res = requests.get(
            url=ip_host+'api/printerlists',
            params=dict(origin='Chicago,IL',destination='Los+Angeles,CA',waypoints='Joplin,MO|Oklahoma+City,OK',sensor='false'),
            timeout=REQUEST_TIMEOUT
        )
        if res.status_code != 200 or not (res.text or "").strip():
            raise ValueError("API returned status %s or empty body" % res.status_code)
        ip_printer_data = res.json()
        if not isinstance(ip_printer_data, list) or len(ip_printer_data) == 0:
            raise ValueError("printer list empty or invalid")
        break
    except Exception as e:
        if attempt < STARTUP_RETRY:
            print("โหลด printerlists ไม่ได้ (ครั้งที่ %d) รอ %d วินาที ..." % (attempt, STARTUP_RETRY_DELAY))
            sleep(STARTUP_RETRY_DELAY)
        else:
            print("ไม่สามารถโหลดรายการเครื่องปริ้นจาก API ได้:", e)
            print("ตรวจสอบ ip_host =", ip_host)
            sys.exit(1)

def printer_Order(ip_printer,type,kitchen,table,customer,item,order_id,order,created_at,name_admin,printer_id):
    p = None
    try:
        p = Network(ip_printer, timeout=PRINTER_TIMEOUT)
        p.set(align='left')
        if type == "บุฟเฟ่":
            p.image(textImage(u"บุฟเฟ่ต์"))
            p.image(textImage(u"ครัว : "+kitchen))
        else:
            p.image(textImage(u"ทานที่ร้าน | ครัว : อาหาร | " + table))
        p.image(textImage(u"ลูกค้า : "+customer))
        p.text('------------------------------------------------ \n')
        for item in item:
            textDetail = u"     " + str(item["amount"]) + "   " + item["foodName"]
            if len(textDetail) > 45:
                p.image(textImage(textDetail[:45]))
                p.image(textImage(textDetail[45:]))
            else:
                p.image(textImage(textDetail))
                
            if item["description"] != None:
                textDescription = u"       ***"+ item["description"]
                
                if len(textDescription) > 45:
                    p.image(textImage(textDescription[:45]))
                    p.image(textImage(textDescription[45:]))
                else:
                    p.image(textImage(textDescription))
                
            if len(item["toping"]) != 0:
                for item2 in item["toping"]:
                    if item2["amount"] != None:
                        if item2["amount"] > 0:
                            textTopping = u"         + " + str(item2["amount"]) + " " + item2["topingName"]
                        else:
                            textTopping = u"         + " + item2["topingName"]
                    else:
                        textTopping = u"         + " + item2["topingName"]
                    if len(textTopping) > 45:
                        p.image(textImage(textTopping[:45]))
                        p.image(textImage(textTopping[45:]))
                    else:
                        p.image(textImage(textTopping))
        p.text('\n')
        p.text('------------------------------------------------ \n')
        order_with_date = u'ออเดอร์ที่: #' + str(order) + u'  (' + created_at + u')'
        p.image(textImage(order_with_date))

        if name_admin != None:
            text_name_admin = u'พนักงานผู้สั่ง : ' + name_admin
            if len(text_name_admin) > 45:
                p.image(textImage(text_name_admin[:45]))
                p.image(textImage(text_name_admin[45:]))
            else:
                p.image(textImage(text_name_admin))

        # p.image(textImage(created_at))
        p.cut()

        url2 = ip_host+'api/updateOrderDetailnobuff'
        payload = {
            'order_detail_id': order_id,
            'printer_id': printer_id,
            'status_printer': 1
        }
        for attempt in range(2):
            try:
                requests.post(url2, json=payload, timeout=KITCHEN_REQUEST_TIMEOUT)
                break
            except requests.RequestException as e:
                if attempt == 1:
                    print('updateOrderDetailnobuff error (status อาจยังเป็น 0):', e)
        print("Print Order To Kidchen")
        return True
    except Exception as e:
        print("printer_Order error:", e)
        return False
    finally:
        if p is not None:
            # ป้องกัน Escpos.__del__ เรียก close() บน socket ที่หลุดแล้ว (WinError 10057)
            orig_close = p.close
            try:
                p.close = lambda: None
            except Exception:
                pass
            try:
                orig_close()
            except Exception:
                pass

def textImage(text):
    font = ImageFont.truetype('C:/xampp/htdocs/ip_zoft_printer/ThaiSarabun/THSarabunNew Bold.ttf', 45)
    left, top, right, bottom = font.getbbox(text)
    width, height = right - left, bottom - top
    image = Image.new('RGB', (width, 20+ height))
    draw1 = ImageDraw.Draw(image)
    draw1.text((0, 0), text, font=font)
    textImage = ImageOps.invert(image)
    return textImage

def textImageBill(text):
    font = ImageFont.truetype('C:/xampp/htdocs/ip_zoft_printer/ThaiSarabun/THSarabunNew Bold.ttf', 35)
    left, top, right, bottom = font.getbbox(text)
    width, height = right - left, bottom - top
    image = Image.new('RGB', (width, 10+ height))
    draw1 = ImageDraw.Draw(image)
    draw1.text((0, 0), text, font=font)
    textImage = ImageOps.invert(image)
    return textImage

def qrcode():
    url = ip_host+'api/print_qr_code'
    params = dict(
        origin='Chicago,IL',
        destination='Los+Angeles,CA',
        waypoints='Joplin,MO|Oklahoma+City,OK',
        sensor='false'
    )
    p = None
    try:
        data, err = api_get_json(url, params)
        if err is not None and "500" not in str(err):
            print('qrcode error:', err)
        if data is None or not data.get('opentable_id') or not data.get('logo_image'):
            return False

        p = Network(ip_printer_data[1]["IP_address"], timeout=PRINTER_TIMEOUT)
        p.set(align='center')
        p.image(Image.open(requests.get(data["logo_image"], stream=True, timeout=IMAGE_TIMEOUT).raw))
        p.text('------------------------------------------------ \n')
        if data["type"] == "บุฟเฟ่":
            p.image(textImage(u"บุฟเฟ่ต์"))
            p.image(textImage(u"โต๊ะที่ : "+data["table"]))
        else:
            p.image(textImage(u"ทานที่ร้าน"))
            p.image(textImage(u"โต๊ะที่ : "+data["table"]))
        p.text('\n')
        p.image(Image.open(requests.get(data["qrcode_image"], stream=True, timeout=IMAGE_TIMEOUT).raw))
        p.text('\n')
        p.image(textImage("ขอบคุณที่มาอุดหนุน"))
        p.image(textImage("powerd by ZoftConnect"))
        p.cut()

        url2 = ip_host+'api/updateopentable'
        post_data = {'id': data["opentable_id"]}
        requests.post(url2, json=post_data, timeout=REQUEST_TIMEOUT)
        print('Print Qrcode')
        return True
    except Exception as e:
        print('qrcode error:', e)
        return False
    finally:
        if p is not None:
            orig_close = p.close
            try:
                p.close = lambda: None
            except Exception:
                pass
            try:
                orig_close()
            except Exception:
                pass

# ปริ้น a la cart
def order_a_la_cart():
    url = ip_host+'api/check-order-to-kitchen'
    params = dict(
        origin='Chicago,IL',
        destination='Los+Angeles,CA',
        waypoints='Joplin,MO|Oklahoma+City,OK',
        sensor='false'
    )
    p = None
    try:
        data, err = api_get_json(url, params)
        if err is not None and "500" not in str(err):
            print('order_a_la_cart error:', err)
        if data is None or not data.get('detail'):
            return False

        p = Network(printer_ipAddress, timeout=PRINTER_TIMEOUT)
        p.set(align='left')
        p.image(textImage(u"ทานที่ร้าน"))
        p.image(textImage(u"ครัว : อาหาร"))
        p.image(textImage(data["table"]))
        p.image(textImage(u"ลูกค้า : " + data["customer"]))
        p.text('------------------------------------------------')
        p.text('------------------------------------------------ \n')
        for detail in data["detail"]:
            for item in detail["printer_2"]:
                textDetail = u"     " + str(item["amount"]) + "   " + item["foodName"]
                if len(textDetail) > 45:
                    p.image(textImage(textDetail[:45]))
                    p.image(textImage(textDetail[45:]))
                else:
                    p.image(textImage(textDetail))
                    
                if item["description"] != None:
                    textDescription = u"       ***"+ item["description"]
                    
                    if len(textDescription) > 45:
                        p.image(textImage(textDescription[:45]))
                        p.image(textImage(textDescription[45:]))
                    else:
                        p.image(textImage(textDescription))
                    
                if len(item["toping"]) != 0:
                    for item2 in item["toping"]:
                        if item2["amount"] != None:
                            if item2["amount"] > 0:
                                textTopping = u"         + " + str(item2["amount"]) + " " + item2["topingName"]
                            else:
                                textTopping = u"         + " + item2["topingName"]
                        else:
                            textTopping = u"         + " + item2["topingName"]
                        if len(textTopping) > 45:
                            p.image(textImage(textTopping[:45]))
                            p.image(textImage(textTopping[45:]))
                        else:
                            p.image(textImage(textTopping))
        p.text('\n')
        p.text('------------------------------------------------')
        p.text('------------------------------------------------ \n')
        p.image(textImage(u'ออเดอร์ที่ : #' + str(data["order"])))

        if data["name_admin"] != None:
            text_name_admin = u'พนักงานผู้สั่ง : ' + data["name_admin"]
            if len(text_name_admin) > 45:
                p.image(textImage(text_name_admin[:45]))
                p.image(textImage(text_name_admin[45:]))
            else:
                p.image(textImage(text_name_admin))
                
        p.image(textImage(data["created_at"]))
        p.cut()


        url2 = ip_host+'api/updateOrderDetailnobuff'
        data = {
            'order_detail_id': data["order_id"],
            'status_printer': 1
        }

        res = requests.post(url2, json=data, timeout=REQUEST_TIMEOUT)
        print('Print Order To Kitchen')
        return True
    except Exception as e:
        print('order_a_la_cart error:', e)
        return False
    finally:
        if p is not None:
            orig_close = p.close
            try:
                p.close = lambda: None
            except Exception:
                pass
            try:
                orig_close()
            except Exception:
                pass

def orderTokidchen():
    url = ip_host+'api/check-order-to-kitchen'
    params = dict(
        origin='Chicago,IL',
        destination='Los+Angeles,CA',
        waypoints='Joplin,MO|Oklahoma+City,OK',
        sensor='false'
    )
    try:
        data, err = api_get_json(url, params, timeout=KITCHEN_REQUEST_TIMEOUT)
        if err is not None and "500" not in str(err):
            print('orderTokidchen error:', err)
        if data is None or not data.get('detail'):
            return False
        has_work = False
        for detail in data["detail"]:
            if len(detail["printer_1"]) > 0:
                if printer_Order(
                    ip_printer_data[0]["IP_address"],
                    data["type"],
                    "ครัว 1",
                    data["table"],
                    data["customer"],
                    detail["printer_1"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    1
                ):
                    has_work = True

            if len(detail["printer_2"]) > 0:
                if printer_Order(
                    ip_printer_data[1]["IP_address"],
                    data["type"],
                    "ครัว 2",
                    data["table"],
                    data["customer"],
                    detail["printer_2"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    2
                ):
                    has_work = True
            if len(detail["printer_3"]) > 0:
                if printer_Order(
                    ip_printer_data[2]["IP_address"],
                    data["type"],
                    "ครัว 3",
                    data["table"],
                    data["customer"],
                    detail["printer_3"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    3
                ):
                    has_work = True
            if len(detail["printer_4"]) > 0:
                if printer_Order(
                    ip_printer_data[3]["IP_address"],
                    data["type"],
                    "ครัว 4",
                    data["table"],
                    data["customer"],
                    detail["printer_4"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    4
                ):
                    has_work = True
            if len(detail["printer_5"]) > 0:
                if printer_Order(
                    ip_printer_data[4]["IP_address"],
                    data["type"],
                    "ครัว 5",
                    data["table"],
                    data["customer"],
                    detail["printer_5"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    5
                ):
                    has_work = True
            if len(detail["printer_6"]) > 0:
                if printer_Order(
                    ip_printer_data[5]["IP_address"],
                    data["type"],
                    "ครัว 6",
                    data["table"],
                    data["customer"],
                    detail["printer_6"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    6
                ):
                    has_work = True
            if len(detail["printer_7"]) > 0:
                if printer_Order(
                    ip_printer_data[6]["IP_address"],
                    data["type"],
                    "ครัว 7",
                    data["table"],
                    data["customer"],
                    detail["printer_7"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    7
                ):
                    has_work = True
            if len(detail["printer_8"]) > 0:
                if printer_Order(
                    ip_printer_data[7]["IP_address"],
                    data["type"],
                    "ครัว 8",
                    data["table"],
                    data["customer"],
                    detail["printer_8"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    8
                ):
                    has_work = True
            if len(detail["printer_9"]) > 0:
                if printer_Order(
                    ip_printer_data[8]["IP_address"],
                    data["type"],
                    "ครัว 9",
                    data["table"],
                    data["customer"],
                    detail["printer_9"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    9
                ):
                    has_work = True
            if len(detail["printer_10"]) > 0:
                if printer_Order(
                    ip_printer_data[9]["IP_address"],
                    data["type"],
                    "ครัว 10",
                    data["table"],
                    data["customer"],
                    detail["printer_10"],
                    data["order_id"],
                    data["order"],
                    data["created_at"],
                    data['name_admin'],
                    10
                ):
                    has_work = True
        if has_work:
            print('Print Order To Kitchen')
        return has_work
    except Exception as e:
        print('orderTokidchen error:', e)
        return False

def orderTableTakehome():
    url = ip_host+'api/ordertabletakehome'
    params = dict(
        origin='Chicago,IL',
        destination='Los+Angeles,CA',
        waypoints='Joplin,MO|Oklahoma+City,OK',
        sensor='false'
    )
    p = None
    try:
        data, err = api_get_json(url, params)
        if err is not None and "500" not in str(err):
            print('orderTableTakehome error:', err)
        if data is None or not data.get('invoiceDetail'):
            return False

        p = Network(ip_printer_data[1]["IP_address"], timeout=PRINTER_TIMEOUT)
        p.set(align='center')
        p.image('C:/xampp/htdocs/ip_zoft_printer/take-away.png')
        p.set(align='left')
        p.image(textImage(data["invoiceDetail"]["customer_name"]))
        p.image(textImage(data["invoiceDetail"]["invoiceNumber"]))
        p.text('------------------------------------------------')
        p.text('------------------------------------------------ \n')
        for item in data["invoiceDetail"]["listnoBuffet"]:
            textDetail = u"     " + str(item["amount"]) + "   " + item["name"]
            if len(textDetail) > 45:
                p.image(textImage(textDetail[:45]))
                p.image(textImage(textDetail[45:]))
            else:
                p.image(textImage(textDetail))
                
            if item["description"] != None:
                textDescription = u"       ***"+ item["description"]
                
                if len(textDescription) > 45:
                    p.image(textImage(textDescription[:45]))
                    p.image(textImage(textDescription[45:]))
                else:
                    p.image(textImage(textDescription))
                    
            if len(item["topping"]) != 0:
                for item2 in item["topping"]:
                    if item2["amount"] != None:
                        if item2["amount"] > 0:
                            textTopping = u"         + " + str(item2["amount"]) + " " + item2["name"]
                        else:
                            textTopping = u"         + " + item2["name"]
                    else:
                        textTopping = u"         + " + item2["name"]
                    if len(textTopping) > 45:
                        p.image(textImage(textTopping[:45]))
                        p.image(textImage(textTopping[45:]))
                    else:
                        p.image(textImage(textTopping))
                    
        p.text('\n')
        p.text('------------------------------------------------')
        p.text('------------------------------------------------ \n')
        p.image(textImage(u'ออเดอร์ที่ : #' + str(data["invoiceDetail"]["order"])))
        p.image(textImage(data["invoiceDetail"]["created_at"]))
        p.cut()
        
        url2 = ip_host+'api/updateorder'
        post_data = {'id': data["invoiceDetail"]["order_id"], 'status': 1}
        requests.post(url2, json=post_data, timeout=REQUEST_TIMEOUT)
        print('Print Order Table Take Home')
        return True
    except Exception as e:
        print('orderTableTakehome error:', e)
        return False
    finally:
        if p is not None:
            orig_close = p.close
            try:
                p.close = lambda: None
            except Exception:
                pass
            try:
                orig_close()
            except Exception:
                pass

def orderTakeHome():
    url = ip_host+'api/ordertakehome'
    params = dict(
        origin='Chicago,IL',
        destination='Los+Angeles,CA',
        waypoints='Joplin,MO|Oklahoma+City,OK',
        sensor='false'
    )
    p = None
    try:
        data, err = api_get_json(url, params)
        if err is not None and "500" not in str(err):
            print('orderTakeHome error:', err)
        if data is None or not data.get('detail'):
            return False

        p = Network(ip_printer_data[1]["IP_address"], timeout=PRINTER_TIMEOUT)
        p.set(align='center')
        p.image('C:/xampp/htdocs/ip_zoft_printer/take-away.png')
        p.set(align='left')
        p.image(textImage(u"คุณ "+data["customer_name"]))
        p.image(textImage(data["invoiceNumber"]))
        p.text('------------------------------------------------')
        p.text('------------------------------------------------ \n')
        for detail in data["detail"]:
            for item in detail["printer_2"]:
                textDetail = u"     " + str(item["amount"]) + "   " + item["foodName"]
                if len(textDetail) > 45:
                    p.image(textImage(textDetail[:45]))
                    p.image(textImage(textDetail[45:]))
                else:
                    p.image(textImage(textDetail))
                    
                if item["description"] != None:
                    textDescription = u"       ***"+ item["description"]
                    
                    if len(textDescription) > 45:
                        p.image(textImage(textDescription[:45]))
                        p.image(textImage(textDescription[45:]))
                    else:
                        p.image(textImage(textDescription))
                        
                if len(item["toping"]) != 0:
                    for item2 in item["toping"]:
                        if item2["amount"] != None:
                            if item2["amount"] > 0:
                                textTopping = u"         + " + str(item2["amount"]) + " " + item2["topingName"]
                            else:
                                textTopping = u"         + " + item2["topingName"]
                        else:
                            textTopping = u"         + " + item2["topingName"]
                        if len(textTopping) > 45:
                            p.image(textImage(textTopping[:45]))
                            p.image(textImage(textTopping[45:]))
                        else:
                            p.image(textImage(textTopping))
        p.text('\n')
        p.text('------------------------------------------------')
        p.text('------------------------------------------------ \n')
        p.image(textImage(u'ออเดอร์ที่ : #' + str(data["order"])))

        if data["name_admin"] != None:
            text_name_admin = u'พนักงานผู้สั่ง : ' + data["name_admin"]
            if len(text_name_admin) > 45:
                p.image(textImage(text_name_admin[:45]))
                p.image(textImage(text_name_admin[45:]))
            else:
                p.image(textImage(text_name_admin))

        p.image(textImage(data["created_at"]))
        p.cut()
        
        url2 = ip_host+'api/updatetakehome'
        post_data = {'id': data["invoice_id"], 'status': 1}
        requests.post(url2, json=post_data, timeout=REQUEST_TIMEOUT)
        print('Print Order Take Home')
        return True
    except Exception as e:
        print('orderTakeHome error:', e)
        return False
    finally:
        if p is not None:
            orig_close = p.close
            try:
                p.close = lambda: None
            except Exception:
                pass
            try:
                orig_close()
            except Exception:
                pass


# เวลารอระหว่างรอบ: ตอนมีงานใช้สั้น เพื่อดึงออเดอร์ต่อได้เร็ว ตอนไม่มีงานรอนานหน่อย
# ไม่ต่ำกว่า 0.5 เกินไป เพื่อไม่ให้ยิงเครื่องปริ้น/ซ็อกเก็ตถี่จนหลุด
SLEEP_WHEN_BUSY = 0.5
SLEEP_WHEN_IDLE = 1.0
SLEEP_BETWEEN_STEPS_IDLE = 1.0
SLEEP_BETWEEN_STEPS_BUSY = 0.5

if __name__ == "__main__":
    while True:
        has_work = False
        if qrcode():
            has_work = True
        sleep(SLEEP_BETWEEN_STEPS_BUSY if has_work else SLEEP_BETWEEN_STEPS_IDLE)
        if orderTokidchen():
            has_work = True
        sleep(SLEEP_BETWEEN_STEPS_BUSY if has_work else SLEEP_BETWEEN_STEPS_IDLE)
        if orderTableTakehome():
            has_work = True
        sleep(SLEEP_BETWEEN_STEPS_BUSY if has_work else 2)
        if orderTakeHome():
            has_work = True
        sleep(SLEEP_WHEN_BUSY if has_work else SLEEP_WHEN_IDLE)

# orderTokidchen()