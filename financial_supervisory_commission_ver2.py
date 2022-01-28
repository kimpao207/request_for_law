import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
import os
from retrying import retry
import math

tables_url = 'https://www.fsc.gov.tw/ch/home.jsp?id=3&parentpath=0&contentid=128&mcustomize=lawnew_list.jsp&pagesize=100&page='
content_path = 'content/'
table_path = 'table/'


def request_data_num():
    # 取得共有幾筆資料
    soup = request_fun(tables_url + str(1))
    return int(soup.select('.red')[0].text)


def request_all_table():
    # 建立資料夾
    if not os.path.exists(content_path):
        os.mkdir(content_path)
    if not os.path.exists(table_path):
        os.mkdir(table_path)

    # 資料總數除以一頁幾筆資料，獲得共有幾頁
    page_num = math.ceil(request_data_num() / 100)

    for i in range(1, page_num + 1):
        print('start page', i)
        table_url = tables_url + str(i)
        table_soup = request_fun(table_url)

        # ver2為直接存當前table，有幾頁就生成幾個html
        full_table = table_soup.select('.newslist')[0]
        file = open(table_path + '/page' + str(i) + '.html', 'w', encoding='utf-8')
        file.write(str(full_table))
        file.close()

        # 取得列表中的每一條項目
        table = full_table.select('li')
        for j in range(0, len(table)):
            if table[j].select('a'):
                # id為該連結內容的dataserno
                content_url_tmp = table[j].select('a')[0]['href']
                content_url = 'https://www.fsc.gov.tw/ch/' + content_url_tmp
                item_id = content_url_tmp[content_url_tmp.find('dataserno=')
                                          + len(str('dataserno=')):content_url_tmp.find('&dtable=')]
                print('start content', j)
                request_each_content(content_url, item_id)
                print('done content', j)

        print('done page', i)


def request_each_content(content_url, item_id):
    # 取得每條項目中連結的內容
    content_soup = request_fun(content_url)
    try:
        content = content_soup.select('.maincontent')[0]
    except:
        print('not web page or no content')
        return
    file = open(content_path + '/' + str(item_id) + '.html', 'w', encoding='utf-8')
    file.write(str(content))
    file.close()


@retry(stop_max_attempt_number=3)
def request_fun(url):
    # 發出request都由這邊發出
    fake_header_can = UserAgent().random
    fake_header = {'user-agent': fake_header_can}
    request = re.get(url, headers=fake_header)
    return bs(request.text, 'html.parser')


if __name__ == '__main__':
    request_all_table()
