"""
cron: 0 */6 * * *
new Env("Linux.Do 签到")
"""

import os
import random
import time
import functools
import sys
import re
import logging
import urllib.request
import urllib.parse
import urllib.error
import json
from html.parser import HTMLParser
from http.cookiejar import CookieJar


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def retry_decorator(retries=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"函数 {func.__name__} 最终执行失败: {str(e)}")
                    logger.warning(
                        f"函数 {func.__name__} 第 {attempt + 1}/{retries} 次尝试失败: {str(e)}"
                    )
                    time.sleep(1)
            return None

        return wrapper

    return decorator


os.environ.pop("DISPLAY", None)
os.environ.pop("DYLD_LIBRARY_PATH", None)

BROWSE_ENABLED = os.environ.get("BROWSE_ENABLED", "true").strip().lower() not in [
    "false",
    "0",
    "off",
]
GOTIFY_URL = os.environ.get("GOTIFY_URL")
GOTIFY_TOKEN = os.environ.get("GOTIFY_TOKEN")
SC3_PUSH_KEY = os.environ.get("SC3_PUSH_KEY")

ACCOUNTS = []
index = 1
while True:
    username = os.environ.get(f"LINUXDO_USERNAME_{index}")
    password = os.environ.get(f"LINUXDO_PASSWORD_{index}")
    if username and password:
        ACCOUNTS.append({"username": username, "password": password, "index": index})
        index += 1
    else:
        break

if not ACCOUNTS:
    username = os.environ.get("LINUXDO_USERNAME")
    password = os.environ.get("LINUXDO_PASSWORD")
    if not username:
        username = os.environ.get("USERNAME")
    if not password:
        password = os.environ.get("PASSWORD")
    if username and password:
        ACCOUNTS.append({"username": username, "password": password, "index": 1})

HOME_URL = "https://linux.do/"
LOGIN_URL = "https://linux.do/login"
SESSION_URL = "https://linux.do/session"
CSRF_URL = "https://linux.do/session/csrf"


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.all_rows = []
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_text = ""

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_table:
            self.in_row = False
            if len(self.current_row) >= 3:
                self.all_rows.append(self.current_row)
        elif tag == "td" and self.in_row:
            self.in_cell = False
            text = self.current_text.strip()
            self.current_row.append(text if text else "0")

    def handle_data(self, data):
        if self.in_cell:
            self.current_text += data


class LinuxDoBrowser:
    def __init__(self, username, password, account_index) -> None:
        from sys import platform
        self.username = username
        self.password = password
        self.account_index = account_index

        if platform == "linux" or platform == "linux2":
            platformIdentifier = "X11; Linux x86_64"
        elif platform == "darwin":
            platformIdentifier = "Macintosh; Intel Mac OS X 10_15_7"
        elif platform == "win32":
            platformIdentifier = "Windows NT 10.0; Win64; x64"

        chrome_versions = ["131.0.0.0", "132.0.0.0", "133.0.0.0"]
        chrome_version = random.choice(chrome_versions)
        self.user_agent = f"Mozilla/5.0 ({platformIdentifier}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.opener.addheaders = [
            ("User-Agent", self.user_agent),
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"),
            ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
            ("Accept-Encoding", "gzip, deflate, br"),
            ("Connection", "keep-alive"),
            ("Upgrade-Insecure-Requests", "1"),
            ("Sec-Fetch-Dest", "document"),
            ("Sec-Fetch-Mode", "navigate"),
            ("Sec-Fetch-Site", "none"),
            ("Sec-Fetch-User", "?1"),
            ("Cache-Control", "max-age=0"),
        ]

    def login(self):
        logger.info(f"账户 {self.account_index} 开始登录")
        
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        req = urllib.request.Request(LOGIN_URL, headers=headers)
        try:
            resp = self.opener.open(req, timeout=30)
            logger.info("访问登录页面成功")
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            logger.error(f"访问登录页面失败: {e}")
            return False
        
        logger.info("获取 CSRF token...")
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": LOGIN_URL,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        req = urllib.request.Request(CSRF_URL, headers=headers)
        try:
            resp = self.opener.open(req, timeout=30)
            csrf_data = json.loads(resp.read().decode('utf-8'))
            csrf_token = csrf_data.get("csrf")
            logger.info(f"CSRF Token obtained: {csrf_token[:10]}...")
            time.sleep(random.uniform(0.5, 1))
        except Exception as e:
            logger.error(f"获取 CSRF token 失败: {e}")
            return False

        logger.info("正在登录...")
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://linux.do",
            "Referer": LOGIN_URL,
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf_token,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        data = urllib.parse.urlencode({
            "login": self.username,
            "password": self.password,
            "second_factor_method": "1",
            "timezone": "Asia/Shanghai",
        }).encode('utf-8')

        try:
            req = urllib.request.Request(SESSION_URL, data=data, headers=headers, method='POST')
            resp = self.opener.open(req, timeout=30)
            response_json = json.loads(resp.read().decode('utf-8'))
            
            if response_json.get("error"):
                logger.error(f"登录失败: {response_json.get('error')}")
                return False
            logger.info("登录成功!")
        except Exception as e:
            logger.error(f"登录请求异常: {e}")
            return False

        self.print_connect_info()
        
        logger.info("验证登录状态...")
        req = urllib.request.Request(HOME_URL, headers={"User-Agent": self.user_agent})
        try:
            resp = self.opener.open(req, timeout=30)
            html_content = resp.read().decode('utf-8')
            if 'current-user' in html_content or 'avatar' in html_content:
                logger.info(f"账户 {self.account_index} 登录验证成功")
                return True
            else:
                logger.error(f"账户 {self.account_index} 登录验证失败")
                return False
        except Exception as e:
            logger.error(f"验证登录状态失败: {e}")
            return False

    def run(self):
        login_res = self.login()
        if not login_res:
            logger.warning(f"账户 {self.account_index} 登录验证失败")
            return False

        logger.info(f"账户 {self.account_index} 签到任务完成")
        return True

    def print_connect_info(self):
        logger.info(f"账户 {self.account_index} 获取连接信息")
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        }
        req = urllib.request.Request("https://connect.linux.do/", headers=headers)
        try:
            resp = self.opener.open(req, timeout=30)
            html_content = resp.read().decode('utf-8')
            
            parser = TableParser()
            parser.feed(html_content)
            
            if parser.all_rows:
                print(f"--------------Connect Info (账户 {self.account_index})-----------------")
                print(f"{'项目':<30} {'当前':<15} {'要求':<15}")
                print("-" * 60)
                for row in parser.all_rows:
                    print(f"{row[0]:<30} {row[1]:<15} {row[2]:<15}")
            else:
                logger.info("未找到连接信息")
        except Exception as e:
            logger.error(f"获取连接信息失败: {e}")


def send_notifications(results):
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    
    if total_count == 1:
        status_msg = f"✅每日登录成功" if results[0]["success"] else f"❌每日登录失败"
    else:
        status_msg = f"✅每日签到完成 - 成功: {success_count}/{total_count}"
        for result in results:
            status = "✅" if result["success"] else "❌"
            status_msg += f"\n{status} 账户{result['index']} ({result['username']})"

    if GOTIFY_URL and GOTIFY_TOKEN:
        try:
            url = f"{GOTIFY_URL}/message"
            data = json.dumps({
                "title": "LINUX DO",
                "message": status_msg,
                "priority": 1
            }).encode('utf-8')
            
            params = urllib.parse.urlencode({"token": GOTIFY_TOKEN})
            full_url = f"{url}?{params}"
            
            req = urllib.request.Request(
                full_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                },
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=10)
            logger.info("消息已推送至Gotify")
        except Exception as e:
            logger.error(f"Gotify推送失败: {str(e)}")
    else:
        logger.info("未配置Gotify环境变量，跳过通知发送")

    if SC3_PUSH_KEY:
        match = re.match(r"sct(\d+)t", SC3_PUSH_KEY, re.I)
        if not match:
            logger.error(
                "❌ SC3_PUSH_KEY格式错误，未获取到UID，无法使用Server酱³推送"
            )
            return

        uid = match.group(1)
        url = f"https://{uid}.push.ft07.com/send/{SC3_PUSH_KEY}"
        params = urllib.parse.urlencode({"title": "LINUX DO", "desp": status_msg})
        full_url = f"{url}?{params}"

        attempts = 5
        for attempt in range(attempts):
            try:
                req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
                resp = urllib.request.urlopen(req, timeout=10)
                response_text = resp.read().decode('utf-8')
                logger.info(f"Server酱³推送成功: {response_text}")
                break
            except Exception as e:
                logger.error(f"Server酱³推送失败: {str(e)}")
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info(f"将在 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)


if __name__ == "__main__":
    if not ACCOUNTS:
        print("Please set LINUXDO_USERNAME_1 and LINUXDO_PASSWORD_1 environment variables")
        exit(1)
    
    results = []
    for account in ACCOUNTS:
        logger.info(f"开始处理账户 {account['index']}: {account['username']}")
        browser = LinuxDoBrowser(account['username'], account['password'], account['index'])
        success = browser.run()
        results.append({
            "index": account['index'],
            "username": account['username'],
            "success": success
        })
        time.sleep(2)
    
    send_notifications(results)
    logger.info("所有账户签到任务完成")
