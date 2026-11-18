# main.py 主逻辑：包括字段拼接、模拟请求
import re
import json
import time
import random
import logging
import hashlib
import requests
import urllib.parse
from push import push
from config import (
    data,
    headers,
    cookies,
    validate_request_config,
    READ_NUM,
    PUSH_METHOD,
    BOOKS,
    BOOK_READ_COUNT,
    BOOK_READ_COUNTS,
    SWITCH_MODE,
    SWITCH_BASE_PROB,
    SWITCH_PROB_INCREASE,
)

# 配置日志格式
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-8s - %(message)s')

# 加密盐及其它默认值
KEY = "3c5c8717f3daf09iop3423zafeqoi"
READ_URL = "https://weread.qq.com/web/book/read"
RENEW_URL = "https://weread.qq.com/web/login/renewal"
FIX_SYNCKEY_URL = "https://weread.qq.com/web/book/chapterInfos"
COOKIE_DATA_VARIANTS = [
    {"rq": "%2Fweb%2Fbook%2Fread", "ql": False},
    {"rq": "%2Fweb%2Fbook%2Fread", "ql": True},
    {"rq": "%2Fweb%2Fbook%2Fread"},
]
REQUEST_TIMEOUT = (10, 30)
SYNCKEY_REPAIR_LIMIT = 3
SYNCKEY_REPAIR_DELAY = 5
AUTH_ERROR_CODES = {-2012, -2013}


def encode_data(data):
    """数据编码"""
    return '&'.join(f"{k}={urllib.parse.quote(str(data[k]), safe='')}" for k in sorted(data.keys()))


def cal_hash(input_string):
    """计算哈希值"""
    _7032f5 = 0x15051505
    _cc1055 = _7032f5
    length = len(input_string)
    _19094e = length - 1

    while _19094e > 0:
        _7032f5 = 0x7fffffff & (_7032f5 ^ ord(input_string[_19094e]) << (length - _19094e) % 30)
        _cc1055 = 0x7fffffff & (_cc1055 ^ ord(input_string[_19094e - 1]) << _19094e % 30)
        _19094e -= 2

    return hex(_7032f5 + _cc1055)[2:].lower()

def retry_decorator(max_retries=3, retry_delay=2):
    """重试装饰器
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试间隔(秒)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    retries += 1
                    if retries >= max_retries:
                        logging.error(f"❌ 请求失败，已达到最大重试次数: {e}")
                        raise
                    logging.warning(f"⚠️ 请求失败，正在进行第 {retries} 次重试: {e}")
                    time.sleep(retry_delay * (2 ** (retries - 1)))  # 指数退避策略
        return wrapper
    return decorator

def _extract_wr_skey(response):
    """从 renewal 响应中读取 wr_skey，兼容 requests CookieJar 和多个 Set-Cookie"""
    new_skey = response.cookies.get("wr_skey")
    if new_skey:
        return new_skey

    raw_headers = getattr(response.raw, "headers", None)
    if raw_headers is not None and hasattr(raw_headers, "getlist"):
        set_cookies = raw_headers.getlist("Set-Cookie")
    else:
        set_cookies = [response.headers.get("Set-Cookie", "")]

    for header in set_cookies:
        match = re.search(r"(?:^|;)\s*wr_skey=([^;]+)", header)
        if match:
            return match.group(1).strip()
    return None


def get_wr_skey():
    """刷新 cookie 密钥，依次尝试 renewal 接口的不同请求参数"""
    failures = []
    for cookie_data in COOKIE_DATA_VARIANTS:
        try:
            response = requests.post(
                RENEW_URL,
                headers=headers,
                cookies=cookies,
                data=json.dumps(cookie_data, separators=(',', ':')),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            failures.append(f"payload={cookie_data} 请求异常: {exc}")
            continue

        new_skey = _extract_wr_skey(response)
        if new_skey:
            return new_skey

        failures.append(
            f"payload={cookie_data} HTTP {response.status_code} 未返回 wr_skey"
        )

    logging.warning("密钥刷新失败详情：%s", "; ".join(failures))
    return None


@retry_decorator(max_retries=3, retry_delay=2)
def fix_no_synckey():
    response = requests.post(
        FIX_SYNCKEY_URL,
        headers=headers,
        cookies=cookies,
        data=json.dumps({"bookIds": ["3300060341"]}, separators=(',', ':')),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()


def notify(content, is_success):
    """发送通知；通知失败时保留原始运行错误"""
    if PUSH_METHOD in (None, ""):
        return False
    try:
        return push(content, PUSH_METHOD, is_success=is_success)
    except Exception:
        logging.exception("通知发送失败")
        return False


def refresh_cookie(strict=True, reason=""):
    """刷新 cookie 密钥；strict=False 时允许保留现有 Cookie 继续尝试"""
    logging.info("🍪 刷新cookie")
    new_skey = get_wr_skey()
    if new_skey:
        cookies['wr_skey'] = new_skey
        logging.info("✅ 密钥刷新成功，新密钥：%s***", new_skey[:2])
        logging.info("🔄 重新本次阅读。")
        return True

    detail = f"（{reason}）" if reason else ""
    error_message = (
        f"❌ 无法获取新密钥{detail}，当前登录状态可能已失效或 renewal 接口受限。"
    )
    if strict:
        logging.error(error_message)
        notify(error_message, is_success=False)
        raise RuntimeError(error_message)

    logging.warning("%s 保留现有 cookie 继续尝试阅读。", error_message)
    return False


@retry_decorator(max_retries=3, retry_delay=2)
def post_read_request(payload):
    """发送阅读请求"""
    return requests.post(
        READ_URL,
        headers=headers,
        cookies=cookies,
        data=json.dumps(payload, separators=(',', ':')),
        timeout=REQUEST_TIMEOUT,
    )


def _get_book_target_count(book_id):
    """获取指定书籍的目标阅读次数，支持按书配置和全局默认"""
    config = BOOK_READ_COUNTS.get(book_id)
    if config is not None:
        if isinstance(config, (list, tuple)) and len(config) == 2:
            return random.randint(config[0], config[1])
        return int(config)
    return BOOK_READ_COUNT


def _should_switch_book(consecutive_count):
    """基于概率判断是否应该换书，越读越久越容易换"""
    prob = min(SWITCH_BASE_PROB + consecutive_count * SWITCH_PROB_INCREASE, 0.5)
    result = random.random() < prob
    if result:
        logging.info(f"🎲 概率触发换书 (当前已连续 {consecutive_count} 次，概率: {prob:.1%})")
    return result


def _switch_book(current_book_id):
    """随机切换到另一本书，多本书时避免选到当前书"""
    all_books = list(BOOKS.keys())
    if len(all_books) > 1:
        other_books = [book_id for book_id in all_books if book_id != current_book_id]
        new_book = random.choice(other_books)
    else:
        new_book = all_books[0]
    logging.info(f"📚 换书，当前书籍：{new_book}")
    return new_book, BOOKS[new_book]


def _pick_chapter(chapters, current_index):
    """选择章节：80%按顺序翻页，20%随机跳章"""
    if random.random() < 0.8:
        next_index = current_index + 1
        if next_index >= len(chapters):
            next_index = random.randint(0, len(chapters) - 1)
            logging.info(f"📖 已到最后一章，随机跳至第 {next_index + 1} 章")
        else:
            logging.info(f"📖 顺序翻页至第 {next_index + 1} 章")
        return next_index, chapters[next_index]

    random_index = random.randint(0, len(chapters) - 1)
    logging.info(f"📖 随机跳至第 {random_index + 1} 章")
    return random_index, chapters[random_index]

validate_request_config()
if cookies.get('wr_skey'):
    logging.info("使用现有 wr_skey，启动时不强制刷新密钥。")
else:
    refresh_cookie(strict=False, reason="启动时未找到 wr_skey")

index = 1
lastTime = int(time.time()) - 30
synckey_repair_attempts = 0

# 初始化当前书籍
_current_book = random.choice(list(BOOKS.keys()))
_current_chapters = BOOKS[_current_book]
_chapter_index = random.randint(0, len(_current_chapters) - 1)
_book_read_count = 0

while index <= READ_NUM:
    data.pop('s')

    # 判断是否需要换书
    need_switch = False
    if SWITCH_MODE == 'prob':
        # 概率换书模式：基于连续阅读次数计算换书概率
        need_switch = _should_switch_book(_book_read_count)
    else:
        # 固定次数换书模式：每本书读够目标次数后换书
        target_count = _get_book_target_count(_current_book)
        if _book_read_count >= target_count:
            need_switch = True
            logging.info(f"📚 阅读次数达到 {target_count}，准备换书")

    if need_switch:
        _current_book, _current_chapters = _switch_book(_current_book)
        _chapter_index = random.randint(0, len(_current_chapters) - 1)
        _book_read_count = 0

    data['b'] = _current_book
    _chapter_index, data['c'] = _pick_chapter(_current_chapters, _chapter_index)
    _book_read_count += 1
    thisTime = int(time.time())
    data['ct'] = thisTime
    data['rt'] = thisTime - lastTime
    data['ts'] = int(thisTime * 1000) + random.randint(0, 1000)
    data['rn'] = random.randint(0, 1000)
    data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
    data['s'] = cal_hash(encode_data(data))

    logging.info(f"⏱️ 尝试第 {index} 次阅读...")
    logging.debug(f"📕 data: {data}")
    response = post_read_request(data)

    try:
        resData = response.json()
    except ValueError as exc:
        error_message = (
            f"read 接口返回非 JSON 响应，HTTP {response.status_code}："
            f"{response.text[:200]}"
        )
        logging.error(error_message)
        notify(error_message, is_success=False)
        raise RuntimeError(error_message) from exc

    logging.debug(f"📕 response: {resData}")

    if 'succ' in resData:
        if 'synckey' in resData:
            synckey_repair_attempts = 0
            lastTime = thisTime
            index += 1
            time.sleep(30)
            logging.info(f"✅ 阅读成功，阅读进度：{(index - 1) * 0.5} 分钟")
        else:
            synckey_repair_attempts += 1
            if synckey_repair_attempts > SYNCKEY_REPAIR_LIMIT:
                error_message = (
                    f"连续 {SYNCKEY_REPAIR_LIMIT} 次未恢复 synckey，终止运行。"
                )
                logging.error(error_message)
                notify(error_message, is_success=False)
                raise RuntimeError(error_message)

            logging.warning(
                "❌ 无 synckey，尝试修复（%d/%d）...",
                synckey_repair_attempts,
                SYNCKEY_REPAIR_LIMIT,
            )
            fix_no_synckey()
            time.sleep(SYNCKEY_REPAIR_DELAY)
    else:
        err_code = resData.get('errCode')
        err_msg = resData.get('errMsg')
        logging.warning(
            "read 接口返回异常：HTTP %s，errCode=%s，errMsg=%s",
            response.status_code,
            err_code,
            err_msg,
        )
        is_auth_error = isinstance(err_code, int) and err_code in AUTH_ERROR_CODES
        if is_auth_error:
            reason = "read 接口返回鉴权错误"
        else:
            reason = f"read errCode={err_code}, errMsg={err_msg}"
        refresh_cookie(reason=reason)

logging.info("🎉 阅读脚本已完成！")

if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    notify(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。", is_success=True)
