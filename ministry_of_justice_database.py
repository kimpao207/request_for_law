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

tables_url = 'https://mojlaw.moj.gov.tw/LawResult.aspx?check=etype5&search=3&LawType=etype5&iPageSize=40&page='
content_base_url = 'https://mojlaw.moj.gov.tw/'

# {
#     'FE356399'(id):{
#         'issue_no': '法務部廉政署 廉財字第 11105001340 號',
#         'gist': "審酌國民法官之選任方式及職權，與法官之職務性質有實質差異...",
#         'html': "",
#         'htmlImg': "",
#         'relLaw': "<article class="col-article" role="article">...",(相關法條的html)
#         'relLawImg': ""(相關法條的圖)
#     }
#     .....
# }


class DataBase:
    def __init__(self):
        self.db = pickledb.load('ministry_of_justice_database.db', True)

    def exist(self, key):
        return self.db.exists(key)

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def request_data_num():
    # 取得共有幾頁
    soup = request_fun(tables_url + str(1))
    page_num_temp = soup.select('.pageinfo')[0].text
    return int(page_num_temp[page_num_temp.find('共') + 1:page_num_temp.find('筆')])


def request_all_table():
    db = DataBase()

    # 資料總數除以一頁幾筆資料，獲得共有幾頁
    page_num = math.ceil(request_data_num() / 40)

    for i in range(1, page_num + 1):
        print('start page', i)
        table_soup = request_fun(tables_url + str(i))

        # 取得列表中的每一條項目
        table = table_soup.select('.table tr')
        for idx, entry in enumerate(table):
            dict_tmp = {}
            link_tag = entry.select('a')[0]
            # 取得連結
            link = content_base_url + link_tag['href']
            # id為key
            entry_id = link[link.find('id=') + len(str('id=')):link.find('&type=E')]
            if not db.exist(entry_id):
                # 存發文字號
                dict_tmp['issue_no'] = link_tag.text
                # 存要旨
                dict_tmp['gist'] = entry.select('pre')[0].text
                print('start content', idx + 1)
                content, extra_url = request_each_content(link, True)
                content_img = get_base64_screenshot(link)
                print('done content', idx + 1)
                # 存html跟圖
                dict_tmp['html'] = str(content)
                dict_tmp['htmlImg'] = str(content_img, 'utf-8')
            else:
                print('existed')
                continue

            if extra_url != '':
                print('start extra content', idx + 1)
                extra_content = request_each_content(extra_url, False)
                extra_content_img = get_base64_screenshot(extra_url)
                print('done extra content', idx + 1)
                # 存相關法條的html跟圖
                dict_tmp['relLaw'] = str(extra_content)
                dict_tmp['relLawImg'] = str(extra_content_img, 'utf-8')

            db.set(entry_id, dict_tmp)

        print('done page', i)
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


def request_each_content(content_url, need_extra):
    # 取得每條項目中連結的內容
    content_soup = request_fun(content_url)
    content = content_soup.select('.text-con')[0]
    extra_url = ''
    if need_extra:
        try:
            tmp = content.select('a')[0]
            if tmp.text == '相關法條':
                extra_url = content_base_url + tmp['href']
        except:
            print('no extra link')

        return content, extra_url
    else:
        return content


@retry(stop_max_attempt_number=3)
def request_fun(url):
    # 發出request都由這邊發出
    fake_header_can = UserAgent().random
    fake_header = {'user-agent': fake_header_can}
    # 碰到verify問題，之前沒碰到這問題，先以不認證來解決
    # request = re.get(url, headers=fake_header)
    request = re.get(url, headers=fake_header, verify=False)
    return bs(request.text, 'html.parser')


if __name__ == '__main__':
    # 執行前先開啟webdriver，增加存圖的速度
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    browser = webdriver.Chrome(options=chrome_options)
    request_all_table()
    browser.close()
