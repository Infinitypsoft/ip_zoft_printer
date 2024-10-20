# !/usr/bin/python
# -- coding: utf-8 --
import json
from time import sleep
from escpos.printer import Network
import requests
from PIL import Image, ImageFont, ImageOps, ImageDraw
# import mysql.connector
from multiprocessing import Process


ip_host = "https://tam-lun-thung.zoftconnect.co/ipsoftapi/"
# ip_host = "http://172.104.184.60/ipsoftapi/"
# ip_host = "http://165.22.59.74/"
#ip_host = "http://localhost:8000/"

printer_ipAddress = "192.168.1.234"

get_ip_printer = requests.get(
    url=ip_host+'api/printerlists',
    params=dict(origin='Chicago,IL',destination='Los+Angeles,CA',waypoints='Joplin,MO|Oklahoma+City,OK',sensor='false')
    )

ip_printer_data = get_ip_printer.json()

def printer_Order(ip_printer,type,kitchen,table,customer,item,order_id,order,created_at,name_admin,printer_id):
    try:
        p = Network(ip_printer)
        p.set(align='left')
        for item in item:
            if type == "บุฟเฟ่":
                p.image(textImage(u"บุฟเฟ่ต์"))
                p.image(textImage(u"ครัว : "+kitchen))
            else:
                p.image(textImage(u"ทานที่ร้าน"))
                p.image(textImage(u"ครัว : อาหาร"))
            p.image(textImage(table))
            p.image(textImage(u"ลูกค้า : "+customer))
            p.text('------------------------------------------------')
            p.text('------------------------------------------------ \n')
            
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
            p.image(textImage(u'ออเดอร์ที่ : #' + str(order)))

            if name_admin != None:
                text_name_admin = u'พนักงานผู้สั่ง : ' + name_admin
                if len(text_name_admin) > 45:
                    p.image(textImage(text_name_admin[:45]))
                    p.image(textImage(text_name_admin[45:]))
                else:
                    p.image(textImage(text_name_admin))

            p.image(textImage(created_at))
            p.cut()

        url2 = ip_host+'api/updateOrderDetailnobuff'
        data = {
            'order_detail_id': order_id,
            'printer_id': printer_id,
            'status_printer': 1
        }
        res = requests.post(url2,json=data)
        return print("Print Order To Kidchen")
    except:
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
    try:
        res = requests.get(url=url, params=params)
        data = res.json()
        
        p = Network(ip_printer_data[1]["IP_address"])
        p.set(align='center')
        p.image(Image.open(requests.get(data["logo_image"], stream=True).raw))
        p.text('------------------------------------------------ \n')
        if data["type"] == "บุฟเฟ่":
            p.image(textImage(u"บุฟเฟ่ต์"))
            p.image(textImage(u"โต๊ะที่ : "+data["table"]))
        else:
            p.image(textImage(u"ทานที่ร้าน"))
            p.image(textImage(u"โต๊ะที่ : "+data["table"]))
        p.text('\n')
        p.image(Image.open(requests.get(data["qrcode_image"], stream=True).raw))
        p.text('\n')
        p.image(textImage("ขอบคุณที่มาอุดหนุน"))
        p.image(textImage("powerd by ZoftConnect"))
        p.cut()
        
        url2 = ip_host+'api/updateopentable'
        data = {
            'id':data["opentable_id"]
        }
        res = requests.post(url2,json=data)
        print('Print Qrcode',res.status_code)
    except:
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
    try:
        res = requests.get(url=url, params=params)
        data = res.json()
        p = Network(printer_ipAddress)
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

        res = requests.post(url2,json=data)
        print('Print Order To Kitchen')
    except:
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
        res = requests.get(url=url, params=params)
        data = res.json()
        
        for detail in data["detail"]:
            if len(detail["printer_1"]) > 0:
                printer_Order(
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
                    )

            if len(detail["printer_2"]) > 0:
                printer_Order(
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
                )
            if len(detail["printer_3"]) > 0:
                printer_Order(
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
                )
            if len(detail["printer_4"]) > 0:
                printer_Order(
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
                )
            if len(detail["printer_5"]) > 0:
                printer_Order(
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
                )
            if len(detail["printer_6"]) > 0:
                printer_Order(
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
                )
            if len(detail["printer_7"]) > 0:
                printer_Order(
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
                )
            if len(detail["printer_8"]) > 0:
                printer_Order(
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
                ) 
            if len(detail["printer_9"]) > 0:
                printer_Order(
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
                )  
            if len(detail["printer_10"]) > 0:
                printer_Order(
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
                )
        
        print('Print Order To Kitchen')
    except:
        pass
    
def orderTableTakehome():
    url = ip_host+'api/ordertabletakehome'
    params = dict(
        origin='Chicago,IL',
        destination='Los+Angeles,CA',
        waypoints='Joplin,MO|Oklahoma+City,OK',
        sensor='false'
    )
    try:
        res = requests.get(url=url, params=params)
        data = res.json()
        
        p = Network(ip_printer_data[1]["IP_address"])
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
        data = {
            'id':data["invoiceDetail"]["order_id"],
            'status':1
        }
        res = requests.post(url2,json=data)
        print('Print Order Table Take Home')
    except:
        pass
    
def orderTakeHome():
    url = ip_host+'api/ordertakehome'
    params = dict(
        origin='Chicago,IL',
        destination='Los+Angeles,CA',
        waypoints='Joplin,MO|Oklahoma+City,OK',
        sensor='false'
    )
    
    try:
        res = requests.get(url=url, params=params)
        data = res.json()
        
        # print(data["detail"])
        
        p = Network(ip_printer_data[1]["IP_address"])
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
        data = {
            'id':data["invoice_id"],
            'status':1
        }
        res = requests.post(url2,json=data)
        print('Print Order Take Home')
    except:
        pass
    

if __name__ == "__main__":
    while True:
        qrcode()
        orderTokidchen()
        # order_a_la_cart()
        orderTableTakehome()
        orderTakeHome()
        time.sleep(2)

# orderTokidchen()