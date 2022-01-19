import requests as re
from bs4 import BeautifulSoup as bs
import json
from fake_useragent import UserAgent


def request_law():
    dict = {}
    url = 'https://law.moj.gov.tw/Law/LawSearchResult.aspx?ty=ONEBAR&psize=60&page='

    r = re.get(url + str(1))
    soup = bs(r.text, 'html.parser')
    pages = len(soup.select('#ddlPages option'))

    for i in range(1, pages + 1):
        
        url_tmp = url + str(i)
        fake_header_can = UserAgent().random
        fake_header = {'user-agent': fake_header_can}
        r = re.get(url_tmp, headers=fake_header)
        
        soup = bs(r.text, 'html.parser')
        soups_tmp = soup.select('.tab-result tbody tr')
        
        for soup_tmp in soups_tmp:
            # 標號
            key = soup_tmp.select('td')[0].text.strip()[:-1]
            # 內容如url，法規名稱等
            content = soup_tmp.select('td')[1]

            url_tmp = 'https://law.moj.gov.tw' + content.select('a')[0]['href'][2:]
            name_tmp = content.select('a')[0].text
            time_tmp = content.text[content.text.find('民國'):content.text.find('日') + 1]
            dict[key] = {'name': name_tmp, 'url': url_tmp, 'time': time_tmp}

        with open("data.json", 'w', encoding='utf-8') as f:
            json.dump(dict, f, ensure_ascii=False)
            f.close()

        print(i)
        '''delay = random.choice(delay_choices)
        time.sleep(delay)'''


if __name__ == '__main__':
    request_law()
