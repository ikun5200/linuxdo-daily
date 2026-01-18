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
import importlib
import subprocess
import signal
import json

AUTO_INSTALL_DEPS = os.environ.get("AUTO_INSTALL_DEPS", "true").strip().lower() not in [
    "false",
    "0",
    "off",
]
REQUIRED_MODULES = [
    "loguru",
    "DrissionPage",
    "tabulate",
    "curl_cffi",
    "bs4",
    "wcwidth",
]
REQUIREMENTS = [
    "DrissionPage==4.1.0.18",
    "wcwidth==0.2.13",
    "tabulate==0.9.0",
    "loguru==0.7.2",
    "curl-cffi",
    "bs4",
]


def ensure_dependencies():
    if not AUTO_INSTALL_DEPS:
        return True
    missing = []
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(module)
    if not missing:
        return True

    print(f"Missing dependencies: {', '.join(missing)}")
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.isfile(requirements_path):
        cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_path]
    else:
        print(f"requirements.txt not found: {requirements_path}")
        print("Falling back to built-in requirements list.")
        cmd = [sys.executable, "-m", "pip", "install", *REQUIREMENTS]
    try:
        subprocess.check_call(cmd)
    except Exception as exc:
        print(f"Auto-install failed: {exc}")
        print("Please install pip or use QingLong dependency manager.")
        return False
    return True


if not ensure_dependencies():
    sys.exit(1)

from loguru import logger
from DrissionPage import ChromiumOptions, Chromium
from tabulate import tabulate
from curl_cffi import requests
from bs4 import BeautifulSoup


def retry_decorator(retries=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:  # 最后一次尝试
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
GOTIFY_URL = os.environ.get("GOTIFY_URL")  # Gotify 服务器地址
GOTIFY_TOKEN = os.environ.get("GOTIFY_TOKEN")  # Gotify 应用的 API Token
SC3_PUSH_KEY = os.environ.get("SC3_PUSH_KEY")  # Server酱³ SendKey
LINUXDO_UA = os.environ.get("LINUXDO_UA", "")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
)

HOME_URL = "https://linux.do/"
LOGIN_URL = "https://linux.do/login"
SESSION_URL = "https://linux.do/session"
CSRF_URL = "https://linux.do/session/csrf"

ACCOUNT_TIMEOUT_WITH_BROWSE = 15 * 60
ACCOUNT_TIMEOUT_NO_BROWSE = 3 * 60


class AccountTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise AccountTimeout()


def split_env_list(value):
    return [item.strip() for item in re.split(r"[&;,\n]+", value) if item.strip()]


def split_ua_list(value):
    if not value:
        return []
    raw_value = value.strip()
    if raw_value.startswith("[") and raw_value.endswith("]"):
        try:
            data = json.loads(raw_value)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except Exception:
            pass
    return [item.strip() for item in re.split(r"\n|\|\|", raw_value) if item.strip()]


def parse_int_env(name, default):
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning(f"{name} 值无效: {raw_value}，使用默认值 {default}")
        return default
    if value < 0:
        logger.warning(f"{name} 不能为负数，使用默认值 {default}")
        return default
    return value


def mask_account(value):
    if not value:
        return ""
    if "@" in value:
        name, domain = value.split("@", 1)
        if len(name) <= 2:
            return f"{name[0]}*@{domain}"
        return f"{name[0]}***{name[-1]}@{domain}"
    if len(value) <= 2:
        return f"{value[0]}*"
    return f"{value[0]}***{value[-1]}"


def parse_accounts():
    raw_accounts = os.environ.get("LINUXDO_ACCOUNTS", "").strip()
    if raw_accounts:
        accounts = []
        for item in re.split(r"[;\n]+", raw_accounts):
            item = item.strip()
            if not item:
                continue
            if ":" not in item:
                logger.warning(f"LINUXDO_ACCOUNTS entry missing ':': {item}")
                continue
            username, password = item.split(":", 1)
            username = username.strip()
            password = password.strip()
            if not username or not password:
                logger.warning(f"LINUXDO_ACCOUNTS entry invalid: {item}")
                continue
            accounts.append((username, password))
        if not accounts:
            logger.error("LINUXDO_ACCOUNTS is set but no valid entries found")
        return accounts

    username = os.environ.get("LINUXDO_USERNAME") or os.environ.get("USERNAME")
    password = os.environ.get("LINUXDO_PASSWORD") or os.environ.get("PASSWORD")
    if not username or not password:
        return []
    usernames = split_env_list(username)
    passwords = split_env_list(password)
    if len(usernames) != len(passwords):
        logger.error(
            f"用户名与密码数量不一致: {len(usernames)} vs {len(passwords)}"
        )
        return []
    return list(zip(usernames, passwords))


class LinuxDoBrowser:
    def __init__(self, username, password, user_agent=None, browse_max_topics=10) -> None:
        self.username = username
        self.password = password
        self.display_name = mask_account(username)
        self.custom_user_agent = user_agent
        self.browse_max_topics = browse_max_topics

        browser_ua = self.custom_user_agent or DEFAULT_USER_AGENT
        request_ua = self.custom_user_agent or DEFAULT_USER_AGENT

        co = (
            ChromiumOptions()
            .headless(True)
            .incognito(True)
            .set_argument("--no-sandbox")
        )
        co.set_user_agent(browser_ua)
        self.browser = Chromium(co)
        self.page = self.browser.new_tab()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": request_ua,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        if self.custom_user_agent:
            logger.info(f"账号 {self.display_name} 使用自定义 UA")
        else:
            logger.info(f"账号 {self.display_name} 使用默认 Windows UA")

    def login(self):
        logger.info(f"账号 {self.display_name} 开始登录")
        # Step 1: Get CSRF Token
        logger.info("获取 CSRF token...")
        headers = {
            "User-Agent": self.session.headers.get("User-Agent", DEFAULT_USER_AGENT),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": LOGIN_URL,
        }
        resp_csrf = self.session.get(CSRF_URL, headers=headers, impersonate="chrome136")
        csrf_data = resp_csrf.json()
        csrf_token = csrf_data.get("csrf")
        logger.info(f"CSRF Token obtained: {csrf_token[:10]}...")

        # Step 2: Login
        logger.info("正在登录...")
        headers.update(
            {
                "X-CSRF-Token": csrf_token,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": "https://linux.do",
            }
        )

        data = {
            "login": self.username,
            "password": self.password,
            "second_factor_method": "1",
            "timezone": "Asia/Shanghai",
        }

        try:
            resp_login = self.session.post(
                SESSION_URL, data=data, impersonate="chrome136", headers=headers
            )

            if resp_login.status_code == 200:
                response_json = resp_login.json()
                if response_json.get("error"):
                    logger.error(f"登录失败: {response_json.get('error')}")
                    return False
                logger.info("登录成功!")
            else:
                logger.error(f"登录失败，状态码: {resp_login.status_code}")
                logger.error(resp_login.text)
                return False
        except Exception as e:
            logger.error(f"登录请求异常: {e}")
            return False

        # Step 3: Pass cookies to DrissionPage
        logger.info("同步 Cookie 到 DrissionPage...")

        # Convert requests cookies to DrissionPage format
        # Using standard requests.utils to parse cookiejar if possible, or manual extraction
        # requests.Session().cookies is a specialized object, but might support standard iteration

        # We can iterate over the cookies manually if dict_from_cookiejar doesn't work perfectly
        # or convert to dict first.
        # Assuming requests behaves like requests:

        cookies_dict = self.session.cookies.get_dict()

        dp_cookies = []
        for name, value in cookies_dict.items():
            dp_cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": ".linux.do",
                    "path": "/",
                }
            )

        self.page.set.cookies(dp_cookies)

        logger.info("Cookie 设置完成，导航至 linux.do...")
        self.page.get(HOME_URL)

        time.sleep(5)
        user_ele = self.page.ele("@id=current-user")
        if not user_ele:
            # Fallback check for avatar
            if "avatar" in self.page.html:
                logger.info("登录验证成功 (通过 avatar)")
                return True
            logger.error("登录验证失败 (未找到 current-user)")
            return False
        else:
            logger.info("登录验证成功")
            return True

    def click_topic(self):
        list_area = self.page.ele("@id=list-area")
        if not list_area:
            logger.error("未找到主题列表区域")
            return False
        topic_list = list_area.eles(".:title")
        if not topic_list:
            logger.error("未找到主题帖")
            return False
        max_topics = int(self.browse_max_topics) if self.browse_max_topics else 0
        if max_topics <= 0:
            logger.info("浏览上限为 0，跳过浏览任务")
            return True
        sample_count = min(max_topics, len(topic_list))
        logger.info(f"发现 {len(topic_list)} 个主题帖，随机选择 {sample_count} 个")
        for topic in random.sample(topic_list, sample_count):
            self.click_one_topic(topic.attr("href"))
        return True

    @retry_decorator()
    def click_one_topic(self, topic_url):
        new_page = self.browser.new_tab()
        new_page.get(topic_url)
        if random.random() < 0.3:  # 0.3 * 30 = 9
            self.click_like(new_page)
        self.browse_post(new_page)
        new_page.close()

    def browse_post(self, page):
        prev_url = None
        # 开始自动滚动，最多滚动10次
        for _ in range(10):
            # 随机滚动一段距离
            scroll_distance = random.randint(550, 650)  # 随机滚动 550-650 像素
            logger.info(f"向下滚动 {scroll_distance} 像素...")
            page.run_js(f"window.scrollBy(0, {scroll_distance})")
            logger.info(f"已加载页面: {page.url}")

            if random.random() < 0.03:  # 33 * 4 = 132
                logger.success("随机退出浏览")
                break

            # 检查是否到达页面底部
            at_bottom = page.run_js(
                "window.scrollY + window.innerHeight >= document.body.scrollHeight"
            )
            current_url = page.url
            if current_url != prev_url:
                prev_url = current_url
            elif at_bottom and prev_url == current_url:
                logger.success("已到达页面底部，退出浏览")
                break

            # 动态随机等待
            wait_time = random.uniform(2, 4)  # 随机等待 2-4 秒
            logger.info(f"等待 {wait_time:.2f} 秒...")
            time.sleep(wait_time)

    def run(self, timeout_seconds=0):
        timeout_seconds = int(timeout_seconds) if timeout_seconds else 0
        old_handler = None
        try:
            logger.info(
                f"账号 {self.display_name} 任务开始，浏览任务："
                f"{'开启' if BROWSE_ENABLED else '关闭'}"
            )
            if timeout_seconds > 0 and hasattr(signal, "SIGALRM"):
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, timeout_seconds)

            login_res = self.login()
            if not login_res:  # 登录
                logger.warning("登录验证失败，跳过浏览任务")
            else:
                logger.info("登录验证成功")

            browse_res = None
            if BROWSE_ENABLED and login_res:
                logger.info("开始浏览任务")
                browse_res = self.click_topic()  # 点击主题
                if not browse_res:
                    logger.error("点击主题失败")
                else:
                    logger.info("完成浏览任务")

            if login_res:
                logger.info("输出连接信息")
                try:
                    self.print_connect_info()
                except Exception as exc:
                    logger.error(f"获取连接信息失败: {exc}")

            logger.info("发送通知")
            self.send_notifications(login_res, browse_res)  # 发送通知
        except AccountTimeout:
            logger.warning(
                f"账号 {self.display_name} 运行超时 {timeout_seconds} 秒，跳过后续步骤"
            )
        finally:
            if timeout_seconds > 0 and hasattr(signal, "SIGALRM"):
                try:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                except Exception:
                    pass
                if old_handler is not None:
                    try:
                        signal.signal(signal.SIGALRM, old_handler)
                    except Exception:
                        pass
            try:
                self.page.close()
            except Exception:
                pass
            try:
                self.browser.quit()
            except Exception:
                pass
            logger.info(f"账号 {self.display_name} 任务结束")

    def click_like(self, page):
        try:
            # 专门查找未点赞的按钮
            like_button = page.ele(".discourse-reactions-reaction-button")
            if like_button:
                logger.info("找到未点赞的帖子，准备点赞")
                like_button.click()
                logger.info("点赞成功")
                time.sleep(random.uniform(1, 2))
            else:
                logger.info("帖子可能已经点过赞了")
        except Exception as e:
            logger.error(f"点赞失败: {str(e)}")

    def print_connect_info(self):
        logger.info("获取连接信息")
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        }
        resp = self.session.get(
            "https://connect.linux.do/", headers=headers, impersonate="chrome136"
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table tr")
        info = []

        for row in rows:
            cells = row.select("td")
            if len(cells) >= 3:
                project = cells[0].text.strip()
                current = cells[1].text.strip() if cells[1].text.strip() else "0"
                requirement = cells[2].text.strip() if cells[2].text.strip() else "0"
                info.append([project, current, requirement])

        print(f"--------------Connect Info ({self.display_name})-----------------")
        print(tabulate(info, headers=["项目", "当前", "要求"], tablefmt="pretty"))

    def send_notifications(self, login_ok, browse_ok):
        if login_ok:
            status_msg = f"账号 {self.display_name}: ✅登录成功"
        else:
            status_msg = f"账号 {self.display_name}: ❌登录失败"
        if BROWSE_ENABLED and login_ok:
            if browse_ok:
                status_msg += " + 浏览任务完成"
            else:
                status_msg += " + 浏览任务失败"

        if GOTIFY_URL and GOTIFY_TOKEN:
            try:
                response = requests.post(
                    f"{GOTIFY_URL}/message",
                    params={"token": GOTIFY_TOKEN},
                    json={"title": "LINUX DO", "message": status_msg, "priority": 1},
                    timeout=10,
                )
                response.raise_for_status()
                logger.success("消息已推送至Gotify")
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
            params = {"title": "LINUX DO", "desp": status_msg}

            attempts = 5
            for attempt in range(attempts):
                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    logger.success(f"Server酱³推送成功: {response.text}")
                    break
                except Exception as e:
                    logger.error(f"Server酱³推送失败: {str(e)}")
                    if attempt < attempts - 1:
                        sleep_time = random.randint(180, 360)
                        logger.info(f"将在 {sleep_time} 秒后重试...")
                        time.sleep(sleep_time)


if __name__ == "__main__":
    accounts = parse_accounts()
    if not accounts:
        print("Please set LINUXDO_ACCOUNTS or LINUXDO_USERNAME/LINUXDO_PASSWORD")
        exit(1)
    browse_max_topics = parse_int_env("BROWSE_MAX_TOPICS", 10)
    ua_list = split_ua_list(LINUXDO_UA)
    logger.info(f"检测到 UA 配置数量：{len(ua_list)}")
    if ua_list and len(ua_list) != len(accounts):
        logger.warning(
            f"LINUXDO_UA 数量({len(ua_list)})与账号数量({len(accounts)})不一致，"
            "未配置的账号将使用默认 Windows UA"
        )
    account_timeout = (
        ACCOUNT_TIMEOUT_WITH_BROWSE
        if BROWSE_ENABLED
        else ACCOUNT_TIMEOUT_NO_BROWSE
    )
    total = len(accounts)
    logger.info(
        f"检测到 {total} 个账号，浏览任务："
        f"{'开启' if BROWSE_ENABLED else '关闭'}，"
        f"单账号限时 {account_timeout // 60} 分钟"
    )
    if BROWSE_ENABLED:
        logger.info(f"浏览帖子上限：{browse_max_topics} 个")
    for idx, (username, password) in enumerate(accounts, start=1):
        user_agent = ua_list[idx - 1] if idx - 1 < len(ua_list) else None
        logger.info(
            f"开始处理账号 {idx}/{total}: {mask_account(username)}，限时 {account_timeout // 60} 分钟"
        )
        try:
            l = LinuxDoBrowser(
                username,
                password,
                user_agent=user_agent,
                browse_max_topics=browse_max_topics,
            )
            l.run(account_timeout)
        except Exception:
            logger.exception(f"账号 {mask_account(username)} 执行异常，跳过该账号")
