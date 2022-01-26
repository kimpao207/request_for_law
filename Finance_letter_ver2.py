import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
import os
from retrying import retry

tables_url = 'http://www.ttc.gov.tw/lp.asp?CtNode=97&CtUnit=40&BaseDSD=31&htx_xBody=&pagesize=30&nowPage='
content_path = 'content/'
table_path = 'table/'


def request_page_num():
    # 取得共有幾頁
    soup = request_fun(tables_url + str(1))
    page_num_temp = soup.select('#pageissue')[0].text
    return int(page_num_temp[page_num_temp.find('/') + 1:page_num_temp.find('頁')])


def request_all_table():
    # 建立資料夾
    if not os.path.exists(content_path):
        os.mkdir(content_path)
    if not os.path.exists(table_path):
        os.mkdir(table_path)

    page_num = request_page_num()

    for i in range(1, page_num + 1):
        print('start page', i)
        table_url = tables_url + str(i)
        table_soup = request_fun(table_url)

        # ver2為直接存當前table，有幾頁就生成幾個html
        full_table = table_soup.select('#ListTable')[0]
        file = open(table_path + '/page' + str(i) + '.html', 'w', encoding='utf-8')
        file.write(str(full_table))
        file.close()

        # 取得列表中的每一條項目
        table = full_table.select('tr')
        for j in range(0, len(table)):
            if table[j].select('a'):
                # url為友善列印的url，id為該連結內容的xItem，連結上可以看到
                content_url_tmp = table[j].select('a')[0]['href']
                content_url = 'http://www.ttc.gov.tw/fp' \
                              + content_url_tmp[2:content_url_tmp.find('CtNode=97') + len('CtNode=97')]
                item_id = content_url_tmp[content_url_tmp.find('Item=')
                                          + len(str('Item=')):content_url_tmp.find('&')]
                print('start content', j)
                request_each_content(content_url, item_id)
                print('done content', j)

        print('done page', i)


def request_each_content(content_url, item_id):
    # 取得每條項目中連結的內容
    content_soup = request_fun(content_url)
    file = open(content_path + '/' + str(item_id) + '.html', 'w', encoding='utf-8')
    file.write(str(content_soup))
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
