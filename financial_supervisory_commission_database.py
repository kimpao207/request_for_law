import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
import os
from retrying import retry
import math
import pickledb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64

tables_url = 'https://www.fsc.gov.tw/ch/home.jsp?id=3&parentpath=0&contentid=128&mcustomize=lawnew_list.jsp&pagesize=100&page='
content_base_url = 'https://www.fsc.gov.tw/ch/'

# {
#     '金管保產字第11104910131號'(entry_id):{
#         'title': '修正「保險商品銷售前程序作業準則」',
#         'date': "2022-03-29",
#         'source': "保險局",
#         'html': "",
#         'htmlImg': "",
#     }
#     .....
# }


class DataBase:
    def __init__(self):
        self.db = pickledb.load('financial_supervisory_commission_database.db', True)

    def exist(self, key):
        return self.db.exists(key)

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def request_data_num():
    # 取得共有幾筆資料
    soup = request_fun(tables_url + str(1))
    return int(soup.select('.red')[0].text)


def request_all_table():
    db = DataBase()

    # 資料總數除以一頁幾筆資料，獲得共有幾頁
    page_num = math.ceil(request_data_num() / 100)

    for i in range(1, page_num + 1):
        print('start page', i)
        table_soup = request_fun(tables_url + str(i))

        # 取得列表中的每一條項目
        table = table_soup.select('.newslist li')[1:]
        for idx, entry in enumerate(table):
            dict_tmp = {}
            content_url = content_base_url + entry.select('a')[0]['href']
            print('start content', idx + 1)
            # entry_id為key，但需要先request一次才能取得
            # 有些內容沒有發文字號，會自動改用標題
            content, entry_id = request_each_content(content_url)
            content_img = get_base64_screenshot(content_url)
            print('done content', idx + 1)

            if not db.exist(entry_id):
                # 存標題
                dict_tmp['title'] = entry.select('a')[0].text
                # 存發布日期
                dict_tmp['date'] = entry.select('.date')[0].text
                # 存資料來源
                dict_tmp['source'] = entry.select('.unit')[0].text

                # 存html跟圖
                dict_tmp['html'] = str(content)
                dict_tmp['htmlImg'] = str(content_img, 'utf-8')

                db.set(entry_id, dict_tmp)
            else:
                print('existed', entry_id)
                continue

        print('done page', i)

    db.dump()


def get_base64_screenshot(url):
    # 用selenium + chromedriver對網頁截圖
    browser.get(url)
    # browser.maximize_window()
    width = browser.execute_script("return document.documentElement.scrollWidth")
    height = browser.execute_script("return document.documentElement.scrollHeight")
    browser.set_window_size(width, height)
    browser.get_screenshot_as_file('tmp.png')

    # 讀取截圖並轉成base64
    with open('tmp.png', 'rb') as f:
        image_data = f.read()
        base64_data = base64.b64encode(image_data)

    # 移除暫存圖片
    os.remove('tmp.png')
    return base64_data


def request_each_content(content_url):
    # 取得每條項目中連結的內容
    content_soup = request_fun(content_url)
    content = content_soup.select('#ap')[0]
    tmp = content_soup.select('.main-a_03')[0].text
    if tmp.find('發文字號：') != -1:
        tmp = tmp[tmp.find('發文字號：') + len('發文字號：'):]
        content_id = tmp[:tmp.find('\n')]
    else:
        content_id = content_soup.select('.subject')[0].text.strip()
        print("issue no. not existed, instead ,use the title")
    return content, content_id


@retry(stop_max_attempt_number=3)
def request_fun(url):
    # 發出request都由這邊發出
    fake_header_can = UserAgent().random
    fake_header = {'user-agent': fake_header_can}
    request = re.get(url, headers=fake_header)
    return bs(request.text, 'html.parser')


if __name__ == '__main__':
    # 執行前先開啟webdriver，增加存圖的速度
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    browser = webdriver.Chrome(options=chrome_options)
    request_all_table()
    browser.close()
