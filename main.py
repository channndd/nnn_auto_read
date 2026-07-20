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
from config import data, headers, cookies, READ_NUM, PUSH_METHOD, BOOKS, BOOK_READ_COUNT, BOOK_READ_COUNTS, SWITCH_MODE, SWITCH_BASE_PROB, SWITCH_PROB_INCREASE

# 配置日志格式
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-8s - %(message)s')

# 加密盐及其它默认值
KEY = "3c5c8717f3daf09iop3423zafeqoi"
COOKIE_DATA = {"rq": "%2Fweb%2Fbook%2Fread"}
READ_URL = "https://weread.qq.com/web/book/read"
RENEW_URL = "https://weread.qq.com/web/login/renewal"
FIX_SYNCKEY_URL = "https://weread.qq.com/web/book/chapterInfos"


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

@retry_decorator(max_retries=3, retry_delay=2)
def get_wr_skey():
    """刷新cookie密钥"""
    response = requests.post(RENEW_URL, headers=headers, cookies=cookies,
                             data=json.dumps(COOKIE_DATA, separators=(',', ':')))
    for cookie in response.headers.get('Set-Cookie', '').split(';'):
        if "wr_skey" in cookie:
            return cookie.split('=')[-1][:8]
    return None

@retry_decorator(max_retries=3, retry_delay=2)
def fix_no_synckey():
    requests.post(FIX_SYNCKEY_URL, headers=headers, cookies=cookies,
                             data=json.dumps({"bookIds":["3300060341"]}, separators=(',', ':')))

def refresh_cookie():
    logging.info(f"🍪 刷新cookie")
    new_skey = get_wr_skey()
    if new_skey:
        cookies['wr_skey'] = new_skey
        logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey}")
        logging.info(f"🔄 重新本次阅读。")
    else:
        ERROR_CODE = "❌ 无法获取新密钥或者WXREAD_CURL_BASH配置有误，终止运行。"
        logging.error(ERROR_CODE)
        push(ERROR_CODE, PUSH_METHOD)
        raise Exception(ERROR_CODE)

@retry_decorator(max_retries=3, retry_delay=2)
def post_read_request(data):
    """发送阅读请求"""
    response = requests.post(READ_URL, headers=headers, cookies=cookies, data=json.dumps(data, separators=(',', ':')))
    return response.json()


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
    """随机切换到另一本书（避免选到当前书）"""
    all_books = list(BOOKS.keys())
    if len(all_books) > 1:
        # 有多本书时，排除当前书
        other_books = [b for b in all_books if b != current_book_id]
        new_book = random.choice(other_books)
    else:
        # 只有一本书，只能读这本
        new_book = all_books[0]
    logging.info(f"📚 换书，当前书籍：{new_book}")
    return new_book, BOOKS[new_book]


def _pick_chapter(chapters, current_index):
    """选择章节：80%按顺序翻页，20%随机跳章"""
    if random.random() < 0.8:
        # 按顺序翻页
        next_index = current_index + 1
        if next_index >= len(chapters):
            # 到最后一章了，随机跳回
            next_index = random.randint(0, len(chapters) - 1)
            logging.info(f"📖 已到最后一章，随机跳至第 {next_index + 1} 章")
        else:
            logging.info(f"📖 顺序翻页至第 {next_index + 1} 章")
        return next_index, chapters[next_index]
    else:
        # 随机跳章
        random_index = random.randint(0, len(chapters) - 1)
        logging.info(f"📖 随机跳至第 {random_index + 1} 章")
        return random_index, chapters[random_index]

refresh_cookie()
index = 1
lastTime = int(time.time()) - 30

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
        _chapter_index = random.randint(0, len(_current_chapters) - 1)  # 换书时随机起始章节
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
    logging.info(f"📕 data: {data}")
    resData = post_read_request(data)
    logging.info(f"📕 response: {resData}")

    if 'succ' in resData:
        if 'synckey' in resData:
            lastTime = thisTime
            index += 1
            time.sleep(30)
            logging.info(f"✅ 阅读成功，阅读进度：{(index - 1) * 0.5} 分钟")
        else:
            logging.warning("❌ 无synckey, 尝试修复...")
            fix_no_synckey()
    else:
        logging.warning("❌ cookie 已过期，尝试刷新...")
        refresh_cookie()

logging.info("🎉 阅读脚本已完成！")

if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{(index - 1) * 0.5}分钟。", PUSH_METHOD)
