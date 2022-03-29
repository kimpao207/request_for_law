import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
from retrying import retry
import pickledb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64
import os

table_url = 'https://cons.judicial.gov.tw/judcurrentNew1.aspx?fid=38'
entry_content_url = 'https://cons.judicial.gov.tw/docdata.aspx?fid=38&id='

# {
#     '111年憲判字第3號'(judgment):{
#         'fid': '38',
#         'html': "",
#         'htmlImg': ""
#     }
#     .....
# }


class DataBase:
    def __init__(self):
        self.db = pickledb.load('constitutional_court_judgment.db', True)

    def exist(self, key):
        return self.db.exists(key)

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def request_all_table():
    db = DataBase()

    table_soup = request_fun(table_url)
    table = table_soup.select('.judgmentList li')

    for idx, entry in enumerate(table):
        dict_tmp = {'fid': '38'}
        link = entry.select('a')[0]['href']

        if link.find('&id=') != -1:
            # 用id找內容跟截圖
            entry_id = link[link.find('&id=') + len(str('&id=')):]
        else:
            print("empty entry")
            continue

        # 判決字號為key
        judgment = entry.text
        # 重複就跳過
        if db.exist(judgment):
            print('existed')
            continue

        # 取得連結與其內容
        content_url = entry_content_url + str(entry_id)
        print('start content', idx + 1)
        content = request_each_content(content_url)
        content_img = get_base64_screenshot(content_url)
        print('done content', idx + 1)
        dict_tmp['html'] = str(content)
        dict_tmp['htmlImg'] = str(content_img, 'utf-8')

        db.set(judgment, dict_tmp)

    db.dump()


def get_base64_screenshot(url):
    # 用selenium + chromedriver對網頁截圖
    browser.get(url)
    # browser.maximize_window()
    width = browser.execute_script("return document.documentElement.scrollWidth")
    height = browser.execute_script("return document.documentElement.scrollHeight")
    # 不確定為什麼到不了最下面，加一點數字做為保險
    browser.set_window_size(width, height + (height / 25))
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
    content = content_soup.select('#sec_page_main')[0]
    return content


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
