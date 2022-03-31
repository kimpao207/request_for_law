import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
import os
from retrying import retry
import pickledb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64

tables_url = 'http://www.ttc.gov.tw/lp.asp?CtNode=97&CtUnit=40&BaseDSD=31&htx_xBody=&pagesize=30&nowPage='
content_base_url = 'http://www.ttc.gov.tw/fp'

# {
#     '22299'(xItem):{
#         'tax_law': '契稅條例',
#         'year': "八十九年版",
#         'chapter': "第1章 全部",
#         'law': "第1條（徵收依據）",
#         'title': "行政機關就行政法規所為之解釋自法規生效日起有其適用",
#         'html': "",
#         'htmlImg': "",
#     }
#     .....
# }


class DataBase:
    def __init__(self):
        self.db = pickledb.load('Finance_letter_database.db', True)

    def exist(self, key):
        return self.db.exists(key)

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def request_page_num():
    # 取得共有幾頁
    soup = request_fun(tables_url + str(1))
    page_num_temp = soup.select('#pageissue')[0].text
    return int(page_num_temp[page_num_temp.find('/') + 1:page_num_temp.find('頁')])


def request_all_table():
    db = DataBase()
    # 前六個欄位，後面存的時候會用到
    col = ['tax_law', 'year', 'chapter', 'law', 'category', 'title']

    page_num = request_page_num()

    for i in range(1, page_num + 1):
        print('start page', i)
        table_url = tables_url + str(i)
        table_soup = request_fun(table_url)

        # 取得列表中的每一條項目
        table = table_soup.select('#ListTable tr')
        for idx, entry in enumerate(table):
            # 每次的第一項為欄位名稱，跳過
            if idx == 0:
                continue

            dict_tmp = {}
            content_url_tmp = entry.select('a')[0]['href']
            # xItem為key
            item_id = content_url_tmp[content_url_tmp.find('xItem=')
                                      + len(str('xItem=')):content_url_tmp.find('&')]

            if not db.exist(item_id):
                # 把前五個欄位(跳過分類)的文字取出來，用前面col中的欄位存
                tds_tmp = entry.select('td')
                for td_idx, td in enumerate(tds_tmp):
                    # 分類不存
                    if td_idx == 4:
                        continue
                    # 標題以後的欄位不存
                    if td_idx > 5:
                        break

                    # 空的不存
                    if td.text.strip() != '':
                        dict_tmp[col[td_idx]] = td.text.strip()

                content_url = 'http://www.ttc.gov.tw/fp' \
                              + content_url_tmp[2:content_url_tmp.find('CtNode=97') + len('CtNode=97')]

                print('start content', idx)
                content = request_each_content(content_url)
                content_img = get_base64_screenshot(content_url)
                print('done content', idx)
                # 存html跟圖
                dict_tmp['html'] = str(content)
                dict_tmp['htmlImg'] = str(content_img, 'utf-8')

                db.set(item_id, dict_tmp)
            else:
                print('existed')
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
    content = request_fun(content_url)
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
