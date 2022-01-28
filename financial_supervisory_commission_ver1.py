import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
import os
from retrying import retry
import math

tables_url = 'https://www.fsc.gov.tw/ch/home.jsp?id=3&parentpath=0&contentid=128&mcustomize=lawnew_list.jsp&pagesize=100&page='
content_path = 'content/'


def request_data_num():
    # 取得共有幾筆資料
    soup = request_fun(tables_url + str(1))
    return int(soup.select('.red')[0].text)


def request_all_table():
    request_data_num()
    # 建立資料夾
    if not os.path.exists(content_path):
        os.mkdir(content_path)

    total_data = '<div class="newslist" role="table"><ul role="rowgroup">'

    # 資料總數除以一頁幾筆資料，獲得共有幾頁
    page_num = math.ceil(request_data_num() / 100)

    for i in range(1, page_num + 1):
        print('start page', i)
        table_soup = request_fun(tables_url + str(i))

        # 取得列表中的每一條項目
        table = table_soup.select('.newslist')[0].select('li')
        for j in range(0, len(table)):
            # 每次的第一項為欄位名稱，ver1只會取一次
            if i != 1 and j == 0:
                continue

            # 將該項目加入自行生成的列表中
            total_data += str(table[j])

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

    total_data += '</ul></div>'

    # 所有資料存到該html裡，只會有一張列表
    file = open('total_table.html', 'w', encoding='utf-8')
    file.write(str(total_data))
    file.close()


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
