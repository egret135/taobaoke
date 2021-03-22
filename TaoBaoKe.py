#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/3/20 下午3:07
# @Author  : 白鹭
# @email   : zhanghang@linghit.com
import argparse
import re
import traceback
import nil as nil
import requests
from selenium import webdriver
import time
import json

from selenium.common.exceptions import NoSuchFrameException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TaoBaoKe:
    # 账号
    _username = ''
    # 密码
    _password = ''
    # 浏览器驱动
    _driver = nil
    # cookie
    cookie = ''
    # token
    token = ''
    # 浏览器存放位置
    _binary_location = ''
    # 不打开浏览器运行程序
    _headless = False

    is_successful = False
    exception = nil
    position_index = ''
    has_next_page = True
    data = {}
    error_msg = ''

    # 登录链接
    login_url = 'https://login.taobao.com/member/login.jhtml?style=mini&newMini2=true&from=alimama&redirectURL=http' \
                '%3A%2F%2Flogin.taobao.com%2Fmember%2Ftaobaoke%2Flogin.htm%3Fis_login%3d1&full_redirect=true' \
                '&disableQuickLogin=true '
    # 校验登录链接
    check_login_url = 'https://pub.alimama.com/common/getUnionPubContextInfo.json'
    # 后台首页链接
    backend_home_url = 'https://pub.alimama.com/manage/overview/index.htm'
    # 获取订单接口
    get_order_url = 'https://pub.alimama.com/openapi/param2/1/gateway.unionpub/report.getTbkOrderDetails.json'
    # 域名
    domain = 'https://pub.alimama.com/'

    def __init__(self, username, password, binary_location, headless):
        self._username = username
        self._password = password
        self._binary_location = binary_location
        self._headless = headless
        self._init__driver()

    def _init__driver(self):
        chrome_options = webdriver.ChromeOptions()
        if self._binary_location != '':
            chrome_options.binary_location = self._binary_location
        if self._headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            'user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36 SocketLog(tabid=1007&client_id=1)"')
        PROXY = "http://D37EPSERV96VT4W2:CERU56DAEB345HU90@proxy.abuyun.com:9020"
        desired_capabilities = chrome_options.to_capabilities()
        desired_capabilities['proxy'] = {
            "httpProxy": PROXY,
            "ftpProxy": PROXY,
            "sslProxy": PROXY,
            "noProxy": None,
            "proxyType": "MANUAL",
            "class": "org.openqa.selenium.Proxy",
            "autodetect": False
        }
        self._driver = webdriver.Chrome(options=chrome_options, desired_capabilities=desired_capabilities)
        # self._driver.maximize_window()
        self._driver.set_window_rect(0, 0, 1792, 1120)
        self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
            """
        })

    # 登录
    def login(self):
        self._driver.get(self.login_url)
        time.sleep(1)

        # 输入账号密码并点击登录
        loginId = self._driver.find_element_by_id('fm-login-id')
        loginId.send_keys(self._username)
        time.sleep(1)
        passwordId = self._driver.find_element_by_id('fm-login-password')
        passwordId.send_keys(self._password)
        time.sleep(1)

        # 滑块处理 nc_1_n1z
        try:
            self._driver.switch_to.frame('baxia-dialog-content')
            action = ActionChains(self._driver)
            button = self._driver.find_element_by_id('nc_1__bg')
            action.reset_actions()  # 清除之前的action
            action.click_and_hold(button).perform()
            distance = 210
            track = self._get_track(distance)
            for i in track:
                action.move_by_offset(xoffset=i, yoffset=0)
            action.perform()
            self._driver.switch_to.default_content()
        except NoSuchFrameException:
            print('登录不需要滑块验证')

        time.sleep(1)
        loginBtn = self._driver.find_element_by_class_name('password-login')
        loginBtn.click()
        time.sleep(2)

        current_url = str(self._driver.current_url)

        if re.search(r'login_unusual.htm', current_url):
            iframe = self._driver.find_element_by_xpath('//iframe')
            self._driver.switch_to.frame(iframe)
            time.sleep(2)
            html = self._driver.execute_script("return document.documentElement.outerHTML")
            if re.search('点击获取验证码', html):
                self._driver.find_element_by_id('J_GetCode').click()
                while True:
                    print('请输入六位数验证码：')
                    code = input()
                    self._driver.find_element_by_id('J_Checkcode').send_keys(code)
                    self._driver.find_element_by_id('btn-submit').click()
                    time.sleep(1.5)
                    html = self._driver.execute_script("return document.documentElement.outerHTML")
                    if re.search('校验码格式不正确', html):
                        continue
                    break

        # 校验通过登录成功
        self._set_cookie()
        local_headers = self._build_headers()
        res = requests.get(self.check_login_url, headers=local_headers, timeout=5)
        print(res.content)

        time.sleep(3)

    def _get_track(self, distance):
        track = []
        current = 0
        mid = distance / 2
        t = 0.5
        v = 20
        while current < distance:
            if current < mid:
                a = 15
            else:
                a = -8
            v0 = v
            v = v0 + a * t
            move = v0 * t + 1 / 2 * a * t * t
            current += move
            if current > distance:
                move = move - (distance - current) + 1
            track.append(round(move))
        return track

    # 模拟跳转到订单页
    def jump_order_page(self):
        self._driver.get('https://pub.alimama.com/manage/overview/index.htm')
        time.sleep(5)
        self._driver.find_element_by_link_text('效果报表').click()
        time.sleep(5)
        self._driver.find_element_by_link_text('订单明细报表').click()
        time.sleep(5)
        self._set_cookie()

    def _set_cookie(self):
        for elem in self._driver.get_cookies():
            self.cookie += elem["name"] + "=" + elem["value"] + "; "
            if elem["name"] == '_tb_token_':
                token = elem["value"]
        self.cookie = self.cookie[:-2]

    def close_driver(self):
        self._driver.close()

    # 获取订单列表
    def get_order(self, start_time, end_time, page=1, per_page=40, jump_type=0, position_index='', query_type='2',
                  tk_status='', member_type=''):
        params = {
            't': self._get_microtime(),
            '_tb_token_': self.token,
            'jumpType': jump_type,
            'positionIndex': position_index,
            'pageNo': page,
            'startTime': start_time,
            'endTime': end_time,
            'queryType': query_type,
            'tkStatus': tk_status,
            'memberType': member_type,
            'pageSize': per_page
        }
        try:
            res = requests.get(self.get_order_url, params=params, headers=self._build_headers())
            self.data = res.content
            self.data = json.loads(self.data)
            if self.data.__contains__('resultCode') and self.data.get('resultCode') == 200:
                self.is_successful = True
                self.data = self.data.get('data')
                self.position_index = self.data.get('positionIndex')
                self.has_next_page = self.data.get('hasNext')
            else:
                self.is_successful = False

        except Exception as exception:
            self.exception = exception
            self.is_successful = False
            self.error_msg = traceback.print_exc()
        return self

    def slider_check(self, url):
        self._driver.get(self.domain + url)
        time.sleep(3)
        # 滑块处理 nc_1_n1z
        action = ActionChains(self._driver)
        button = self._driver.find_element_by_id('nc_1_n1z')
        action.reset_actions()  # 清除之前的action
        action.click_and_hold(button).perform()
        distance = 300
        track = self._get_track(distance)
        for i in track:
            action.move_by_offset(xoffset=i, yoffset=0)
        action.perform()

    # 获取毫秒时间戳
    def _get_microtime(self):
        ct = time.time()
        return int(time.time() * 1000)

    def _build_headers(self):
        headers = {
            'referer': 'https://pub.alimama.com/manage/effect/overview_orders.htm',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36 SocketLog(tabid=419&client_id=1)',
            'cookie': self.cookie
        }
        return headers


start_time = ''
end_time = ''
page = 0
per_page = 40
tk_status = '3'
member_type = '2'
query_type = '3'
position_index = ''
binary_location = ''
headless = False
callback_url = ''

username = ''
password = ''

QUERY_TYPE = {
    '1': '创建时间',
    '2': '支付时间',
    '3': '结算时间'
}

MEMBER_TYPE = {
    '': '全部',
    '2': '二方',
    '3': '三方'
}

TK_STATUS = {
    '12': '付款',
    '13': '关闭',
    '14': '确认收货',
    '3': '结算成功'
}

if __name__ == '__main__':
    parse = argparse.ArgumentParser()
    parse.add_argument('-s', '--start', help='抓取订单起始日期，格式为：Y-m-d', required=True, dest='start_time')
    parse.add_argument('-e', '--end', help='抓取订单结束日期，格式为：Y-m-d', required=True, dest='end_time')
    parse.add_argument('-u', '--username', help='淘宝客手机号/用户名', required=True, dest='username')
    parse.add_argument('-p', '--password', help='淘宝客密码', required=True, dest='password')
    parse.add_argument('-q', '--query-type', default='3', choices=['1', '2', '3'], help='订单查询类型，1-创建时间，2-支付时间，3-结算时间',
                       dest='query_type')
    parse.add_argument('-m', '--member-type', default='', choices=['2', '3'], help='推广者角色类型，2-二方，3-三方',
                       dest='member_type')
    parse.add_argument('-t', '--tk-status', default='3', choices=['12', '13', '14', '3'],
                       help='淘客订单状态，12-付款，13-关闭，14-确认收货，3-结算成功', dest='tk_status')
    parse.add_argument('-b', '--binary-location', default='', help='浏览器可执行文件路径', dest='binary_location')
    parse.add_argument('-d', '--headless', action='store_true', help='不开启浏览器执行程序', dest='headless')
    parse.add_argument('-c', '--callback-url', default='', help='结果数据回调链接', dest='callback_url')
    args = parse.parse_args()
    pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if not pattern.match(args.start_time) or not pattern.match(args.end_time):
        print('日期格式必须为Y-m-d')
        exit(1)
    print("抓取订单起始日期：{0}".format(args.start_time))
    print("抓取订单结束日期：{0}".format(args.end_time))
    # print("淘宝客手机号：{0}".format(args.username))
    # print("淘宝客密码：{0}".format(args.password))
    print("订单查询类型：{0}".format(QUERY_TYPE[args.query_type]))
    print("推广者角色类型：{0}".format(MEMBER_TYPE[args.member_type]))
    print("淘客订单状态：{0}".format(TK_STATUS[args.tk_status]))
    print("订单数据回调链接：{0}".format(args.callback_url))
    start_time = args.start_time
    end_time = args.end_time
    username = args.username
    password = args.password
    query_type = args.query_type
    member_type = args.member_type
    tk_status = args.tk_status
    binary_location = args.binary_location
    headless = args.headless
    callback_url = args.callback_url

tbk = TaoBaoKe(username, password, binary_location, headless)
tbk.login()
tbk.jump_order_page()

while tbk.has_next_page:
    page += 1
    if tbk.get_order(
            start_time,
            end_time,
            page=page,
            per_page=per_page,
            tk_status=tk_status,
            member_type=member_type,
            query_type=query_type,
            position_index=position_index
    ).is_successful:
        position_index = tbk.position_index
        print(tbk.data)
        if callback_url != '':
            local_headers = {
                'Content-Type': 'application/json'
            }
            try:
                res = requests.post(callback_url, headers=local_headers, data=json.dumps(tbk.data), timeout=10)
                print('请求回调地址响应码：{0}，响应内容：{1}'.format(res.status_code, res.content))
            except Exception as e:
                print('请求回调地址出现异常：{0}'.format(traceback.print_exc()))
    else:
        if tbk.data.__contains__('rgv587_flag'):
            tbk.slider_check(tbk.data.get('url'))
            page -= 1
        else:
            raise Exception(print(tbk.data))

tbk.close_driver()
