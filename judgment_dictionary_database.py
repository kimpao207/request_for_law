import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
from retrying import retry
import pickledb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64
import os

tables_url = 'https://terms.judicial.gov.tw/List.aspx?&TXT=%25&SYS=&Page='
entry_content_url = 'https://terms.judicial.gov.tw/'

# 格式
# {
#     '比例原則'(noun):{
#         'fields': ["民事", "刑事"],
#         'html': "",
#         'htmlImg': ""
#     }
#     .....
# }


class DataBase:
    def __init__(self):
        self.db = pickledb.load('judgment_dictionary_database.db', True)

    def exist(self, key):
        return self.db.exists(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def request_page_num():
    # 取得共有幾頁
    soup = request_fun(tables_url + str(1))
    page_count_tmp = soup.select('#lbTotalPage')[0]
    return int(page_count_tmp.text)


def request_all_table():
    db = DataBase()

    page_num = request_page_num()

    for i in range(1, page_num):
        print('start page', i)
        table_soup = request_fun(tables_url + str(i))

        # 取得列表中的每一條項目
        table = table_soup.select('.fy_page_content tr a')
        for idx, entry in enumerate(table):
            # 以dictionary存需要的資料
            dict_tmp = {}
            # 法律名詞為key
            noun = entry.text
            # 存在就跳過
            if db.exist(noun):
                print('existed')
                continue

            content_url = entry_content_url + entry['href']
            print('start content', idx + 1)
            content, fields = request_each_content(content_url)
            content_img = get_base64_screenshot(content_url)
            print('done content', idx + 1)
            dict_tmp['fields'] = fields
            dict_tmp['html'] = str(content)
            dict_tmp['htmlImg'] = str(content_img, 'utf-8')

            db.set(noun, dict_tmp)

        print('done page', i)

        if i == 10:
            break

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
    content = content_soup.select('.fy_page_content')[0]
    fields = []
    for field in content_soup.select('.fy_term_jtname'):
        fields.append(field.text.strip('適用之法領域：'))
    return content, fields


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

