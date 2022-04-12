import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
from retrying import retry
import pickledb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64
import os
import math
from PIL import Image

tables_front_url = 'https://law.moj.gov.tw/Law/LawSearchResult.aspx?cur=Ln&ty=ONEBAR&set=LNNDATE%7cDESC&psize=60&page='
tables_back_url = 'https://law.moj.gov.tw/Law/LawSearchResult.aspx?cur=Ln&ty=ONEBAR&set=LNNDATE%7cASC&psize=60&page='
total_content_url = 'https://law.moj.gov.tw/LawClass/LawAll.aspx?media=print&pcode='
# for screenshot
height_size = 50000
bias = 100

# 格式
# {
#     'K0040013'(pcode):{
#         'title': '道路交通安全規則',
#         'html': "",
#         'htmlImg': ""
#     }
#     .....
# }


class DataBase:
    def __init__(self):
        self.db = pickledb.load('legislation.db', True)

    def exist(self, key):
        return self.db.exists(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def request_page_num():
    # 取得共有幾頁
    soup = request_fun(tables_front_url + str(1))
    page_num_temp = soup.select('.pageinfo')[0].text
    return int(page_num_temp[page_num_temp.find('共') + 1:page_num_temp.find('筆')])


def request_all_table():
    page_num = math.ceil(request_page_num() / 60)

    for i in range(1, (page_num // 2) + 1):
        print('start front page', i)
        table_soup = request_fun(tables_front_url + str(i))
        get_each_entry(table_soup)
        print('done front page', i)

    for i in range(1, (page_num // 2) + 1):
        print('start back page', i)
        table_soup = request_fun(tables_back_url + str(i))
        get_each_entry(table_soup)
        print('done back page', i)


def get_each_entry(table_soup):
    db = DataBase()
    # 取得列表中的每一條項目
    table = table_soup.select('#pnLaw tbody tr')
    for idx, entry in enumerate(table):
        link = entry.select('a')[0]
        # 以dictionary存需要的資料
        # 存title
        dict_tmp = {'title': link.text}

        pcode_tmp = link['href']
        # 存pcode
        pcode = pcode_tmp[pcode_tmp.find('pcode=') + len('pcode='):pcode_tmp.find('&cur=')]

        # 檢查是否有在資料庫內，如果有的話直接跳下一項
        if not db.exist(pcode):
            content_url = total_content_url + pcode
            print('start content', idx + 1)
            content = request_each_content(content_url)
            content_img = get_base64_screenshot(content_url)
            print('done content', idx + 1)
            dict_tmp['html'] = str(content)
            dict_tmp['htmlImg'] = str(content_img, 'utf-8')

            db.set(pcode, dict_tmp)
        else:
            print('existed')
            continue

    db.dump()


def request_each_content(content_url):
    # 取得每條項目中連結的內容
    content_soup = request_fun(content_url)
    content = content_soup.select('.container')[0]
    return content


def get_base64_screenshot(url):
    # 對網頁截圖
    screenshot_browser.get(url)
    width = screenshot_browser.execute_script("return document.documentElement.scrollWidth")
    height = screenshot_browser.execute_script("return document.documentElement.scrollHeight")

    # 若高度超過100000時, 用分段截圖後合併圖像的方式來處理
    if height > 100000:
        print('segmented screenshot')
        long_screenshot(width)
    else:
        screenshot_browser.set_window_size(width, height)
        screenshot_browser.get_screenshot_as_file('tmp.png')

    # 讀取截圖並轉成base64
    with open('tmp.png', 'rb') as f:
        image_data = f.read()
        base64_data = base64.b64encode(image_data)

    # 移除暫存圖片
    os.remove('tmp.png')
    return base64_data


def long_screenshot(width):
    # 設定視窗大小, bias為避免出現橫條擋住文字
    screenshot_browser.set_window_size(width + bias, height_size)
    # 調整後的視窗總長會變短
    total_height = screenshot_browser.execute_script("return document.documentElement.scrollHeight")
    count = total_height // height_size
    surplus_height = total_height - count * height_size

    for i in range(0, count):
        # 重複截高度為height_size的視窗畫面
        js = "scrollTo(0,%s)" % (i * height_size)
        screenshot_browser.execute_script(js)
        screenshot_browser.get_screenshot_as_file('%s.png' % i)
    else:
        # 考慮到會有剩下不足height_size的部分需要截圖, 最後調整視窗高度進行截圖
        screenshot_browser.set_window_size(width + bias, surplus_height)
        js = "scrollTo(0,%s)" % total_height
        screenshot_browser.execute_script(js)
        screenshot_browser.get_screenshot_as_file('%s.png' % count)

    # 用pillow進行圖的合併
    new_img = Image.new("RGB", (width + bias, total_height))
    k = 0
    for i in range(0, count + 1):
        tmp_img = Image.open('%s.png' % i)
        # 把圖片貼在上一張圖的下面
        new_img.paste(tmp_img, (0, height_size * k))
        k += 1
        os.remove('%s.png' % i)
    else:
        new_img.save("tmp.png")


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
    screenshot_browser = webdriver.Chrome(options=chrome_options)
    request_all_table()
    screenshot_browser.close()
