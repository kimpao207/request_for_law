import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
from retrying import retry
import pickledb
from selenium import webdriver
import base64
import os

tables_url = 'https://www.laws.taipei.gov.tw/Law/LawIntegrated/LawIntegratedSearchResult?criteria.searchTypes=%E4%B8%AD%E5%A4%AE%E8%A7%A3%E9%87%8B%E4%BB%A4%E5%87%BD&criteria.orderBy=%E4%BE%9D%E6%97%A5%E6%9C%9F&criteria.searchString1=&criteria.searchString2=&criteria.searchString3=&criteria.searchAnd1=AND&criteria.searchAnd2=AND&criteria.dateFrom=0100101&criteria.dateTo=&criteria.word=&criteria.number=&criteria.showType=&type=%E4%B8%AD%E5%A4%AE%E8%A7%A3%E9%87%8B%E4%BB%A4%E5%87%BD&page='
total_content_url = 'https://www.laws.taipei.gov.tw/Law/LawInterpretation/LawInterpretationContentPrint?soid='
total_extra_url = 'https://www.laws.taipei.gov.tw'


class DataBase:
    def __init__(self):
        self.db = pickledb.load('Law_and_Regulation.db', True)

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def request_page_num():
    # 取得共有幾頁
    soup = request_fun(tables_url + str(1))
    page_count_tmp = soup.select('.paging-counts')[0]
    return int(page_count_tmp.select('em')[1].text)


def request_all_table():
    db = DataBase()

    page_num = request_page_num()

    for i in range(1, page_num + 1):
        print('start page', i)
        table_soup = request_fun(tables_url + str(i))

        # 取得列表中的每一條項目
        table = table_soup.select('.fx-cluster .fx-tb')
        for j in range(0, len(table)):
            # 以dictionary存需要的資料
            dict_tmp = {}
            soid = 0
            # 在class="fx-list"中，如果該項目有規範的話會有兩條連結
            links = table[j].select('.fx-list a')

            # 處理第一個連結
            if len(links) > 0:
                # 取得soid
                content_url_tmp = links[0]['href']
                soid = content_url_tmp[content_url_tmp.find('soid=')
                                       + len(str('soid=')):content_url_tmp.find('&typeName=')]
                # 檢查是否有在資料庫內，如果有的話直接跳下一項
                if not db.get(soid):
                    # 存發文字號
                    dict_tmp['issue_no'] = links[0].text.strip()
                    # 存要旨
                    dict_tmp['gist'] = table[j].select('.fx-list .pre')[0].text.strip()
                    # 取得連結與其內容
                    content_url = total_content_url + str(soid)
                    print('start content', j + 1)
                    content = request_each_content(content_url, '.law')
                    content_img = get_base64_screenshot(content_url)
                    print('done content', j + 1)
                    dict_tmp['html'] = str(content)
                    dict_tmp['htmlImg'] = str(content_img, 'utf-8')
                else:
                    continue

            # 有些項目會有規範，是各部會底下查到的相關內容
            if len(links) > 1:
                extra_url = total_extra_url + links[1]['href']
                print('start extra link', j + 1)
                extra = request_each_content(extra_url, '.col-article')
                extra_img = get_base64_screenshot(extra_url)
                print('done extra link', j + 1)
                dict_tmp['norm'] = str(extra)
                dict_tmp['normImg'] = str(extra_img, 'utf-8')

            dict_tmp['image'] = ''
            db.set(soid, dict_tmp)

        print('done page', i)
    db.dump()


def get_base64_screenshot(url):
    # 用selenium + phantomjs對網頁截圖
    browser.get(url)
    browser.maximize_window()
    browser.save_screenshot('tmp.png')

    # 讀取截圖並轉成base64
    with open('tmp.png', 'rb') as f:
        image_data = f.read()
        base64_data = base64.b64encode(image_data)

    # 移除暫存圖片
    os.remove('tmp.png')
    return base64_data


def request_each_content(content_url, select_item):
    # 取得每條項目中連結的內容
    content_soup = request_fun(content_url)
    try:
        content = content_soup.select(select_item)[0]
    except:
        print('not web page or no content')
        return ''
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
    browser = webdriver.PhantomJS()
    request_all_table()
    browser.close()
