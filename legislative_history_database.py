import requests as re
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
from retrying import retry
import pickledb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64
import os
import random
from PIL import Image

base_url = 'https://lis.ly.gov.tw/'
# for screenshot
height_size = 50000
bias = 100


class DataBase:
    def __init__(self):
        self.db = pickledb.load('legislative_history.db', True)

    def exist(self, key):
        return self.db.exists(key)

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        self.db.set(key, value)

    def dump(self):
        self.db.dump()


def driver(need_option, options):
    return webdriver.Chrome() if not need_option else webdriver.Chrome(options=options)


def get_to_browser_category():
    # 進入分類瀏覽
    operate_browser.get('https://lis.ly.gov.tw/lglawc/lglawkm')
    category = operate_browser.find_element_by_xpath('//*[@id="manu_bar"]/table/tbody/tr/td[4]/a')
    category.click()


def get_all_data():
    get_to_browser_category()

    # 進入法律清單&爬現行法內容
    movement('/html/body/form/table/tbody/tr[2]/td/table/tbody/tr[1]/td/ul/li[2]/a')
    get_current_table(0, '現行法')

    # 爬廢止法內容
    movement('//*[@id="sub_i"]/ul/li[2]/a')
    get_current_table(0, '廢止法')

    # 爬停止適用法內容
    movement('//*[@id="sub_i"]/ul/li[3]/a')
    get_current_table(0, '停止適用法')

    # 進入主管/業務機關
    movement('/html/body/form/table/tbody/tr[2]/td/table/tbody/tr[1]/td/ul/li[1]/a')

    # 取出全部的名字和網址
    tmp_agencies = operate_browser.find_elements_by_css_selector('.content tr:nth-child(2) a')
    agencies = []
    for tmp_agency in tmp_agencies:
        agencies.append([tmp_agency.get_attribute('href'), tmp_agency.text[0:tmp_agency.text.find('(')]])

    # 進入每一個網址並進行主管/業務機關的標記
    for agency in agencies:
        # 現行法標記
        operate_browser.get(agency[0])
        operate_browser.implicitly_wait(random.randint(1, 15))
        get_current_table(1, agency[1])

        # 廢止法&停止適用法標記
        for i in range(2, 4):
            try:
                movement(f'//*[@id="sub_i"]/ul/li[{i}]/a')
            except:
                print('no such button')


def get_current_table(mode, mode_data):
    bottom = False
    counter = 1
    while not bottom:
        print('start page', counter)
        # 透過bs4解析網頁並將其傳至get_each_entry
        get_each_entry(bs(operate_browser.page_source, 'html.parser'), mode, mode_data)
        print('done page', counter)
        counter += 1
        try:
            # 按下一頁直到不能按為止
            if mode == 0:
                movement('/html/body/form/table/tbody/tr[2]/td/table/tbody' +
                         '/tr[2]/td/table/tbody/tr/td[2]/table/tbody/tr/td[4]/input')
            elif mode == 1:
                movement('/html/body/form/table/tbody/tr[2]/td/table/tbody/tr[2]/td' +
                         '/table/tbody/tr[2]/td/table/tbody/tr/td[9]/table/tbody/tr/td[4]/input')
            operate_browser.implicitly_wait(random.randint(1, 15))
        except:
            print('reached bottom page or encounter error')
            bottom = True


# mode 0為新增資料,mode_data放的是category
# mode 1為標記是哪個主管/業務機關,mode_data放的是agency
def get_each_entry(soup, mode, mode_data):
    db = DataBase()
    entries = soup.select('.sumtd2000 a')
    counter = 1
    for entry in entries:
        print('start content', counter)
        if mode == 0 and not db.exist(entry.text):
            # 以dictionary存需要的資料，先放入類別
            dict_tmp = {'agency': [], 'category': mode_data}

            # 取得法律沿革及其url，用來截圖
            tmp_url = base_url + entry['href']
            content, target_url = request_content(tmp_url)
            dict_tmp['html'] = content

            # 截圖
            content_img = get_base64_screenshot(target_url)
            dict_tmp['htmlImg'] = str(content_img, 'utf-8')

            # key為名稱
            db.set(entry.text, dict_tmp)
        elif mode == 1 and db.exist(entry.text):
            target = db.get(entry.text)
            if mode_data not in target['agency']:
                target['agency'].append(mode_data)
                db.set(entry.text, target)
            else:
                print('already marked')
        else:
            if mode == 0:
                print('repeated')
            else:
                print("no such data in database")
        print('done content', counter)
        counter += 1

    db.dump()


def movement(xpath):
    tables = operate_browser.find_element_by_xpath(xpath)
    tables.click()


def request_content(url):
    tmp_soup = request_fun(url)
    target_url = base_url + tmp_soup.select('.L_tab a')[0]['href']
    soup = request_fun(target_url)
    content = soup.select('table')[1]
    return str(content), target_url


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
    request.encoding = 'utf-8'
    return bs(request.text, 'html.parser')


if __name__ == '__main__':
    operate_browser = driver(False, '')
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    screenshot_browser = driver(True, chrome_options)
    get_all_data()
    screenshot_browser.close()
    operate_browser.quit()

