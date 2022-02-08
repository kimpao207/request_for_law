import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
import os
from retrying import retry
import math

tables_url = 'https://mojlaw.moj.gov.tw/LawResult.aspx?check=etype5&search=3&LawType=etype5&iPageSize=40&page='
content_path = 'content/'
table_path = 'table/'


def request_data_num():
    # 取得共有幾頁
    soup = request_fun(tables_url + str(1))
    page_num_temp = soup.select('.pageinfo')[0].text
    return int(page_num_temp[page_num_temp.find('共') + 1:page_num_temp.find('筆')])


def request_all_table():
    # 建立資料夾
    if not os.path.exists(content_path):
        os.mkdir(content_path)
    if not os.path.exists(table_path):
        os.mkdir(table_path)

    # 資料總數除以一頁幾筆資料，獲得共有幾頁
    page_num = math.ceil(request_data_num() / 40)

    for i in range(1, page_num + 1):
        print('start page', i)
        table_soup = request_fun(tables_url + str(i))

        # ver2為直接存當前table，有幾頁就生成幾個html
        full_table = table_soup.select('.table')[0]
        file = open(table_path + '/page' + str(i) + '.html', 'w', encoding='utf-8')
        file.write(str(full_table))
        file.close()

        # 取得列表中的每一條項目
        table = full_table.select('tr')
        for j in range(0, len(table)):
            if table[j].select('a'):
                # id為該連結內容的id
                content_url_tmp = table[j].select('a')[0]['href']
                content_url = 'https://mojlaw.moj.gov.tw/' + content_url_tmp
                item_id = content_url_tmp[content_url_tmp.find('id=')
                                          + len(str('id=')):content_url_tmp.find('&type=E')]
                print('start content', j + 1)
                request_each_content(content_url, item_id)
                print('done content', j + 1)

        print('done page', i)


def request_each_content(content_url, item_id):
    # 取得每條項目中連結的內容
    content_soup = request_fun(content_url)
    try:
        content = content_soup.select('.text-con')[0]
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
