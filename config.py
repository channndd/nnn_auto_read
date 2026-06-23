# config.py 自定义配置,包括阅读次数、推送token的填写
import os
import re
import random

"""
可修改区域：
- 环境变量：只保留最核心的 3 个（READ_NUM, BOOK_READ_COUNT, SWITCH_MODE）
- 波动率、概率参数全部内置，不需要维护
"""

def _fluctuate(base, fluctuation_percent):
    """在基础值上做百分比随机波动，结果四舍五入取整"""
    if fluctuation_percent <= 0:
        return base
    factor = 1 + random.uniform(-fluctuation_percent / 100, fluctuation_percent / 100)
    return max(1, round(base * factor))

# ============================================================
# 核心环境变量（只有这3个需要关注）
# ============================================================

# 阅读总次数，默认60次≈30分钟
_READ_NUM_BASE = int(os.getenv('READ_NUM') or 60)
# 每本书连续阅读次数，默认10次≈5分钟
_BOOK_READ_COUNT_BASE = int(os.getenv('BOOK_READ_COUNT') or 10)
# 换书模式: 'count' = 固定次数后换书, 'prob' = 概率换书（更仿真）
SWITCH_MODE = os.getenv('SWITCH_MODE', 'count')

# ============================================================
# 以下参数为内置默认值，不需要环境变量
# ============================================================

# 阅读总次数波动 ±20%（如 60±20% = 48~72）
READ_NUM = _fluctuate(_READ_NUM_BASE, 20)
# 每本书阅读次数波动 ±30%（如 10±30% = 7~13）
BOOK_READ_COUNT = _fluctuate(_BOOK_READ_COUNT_BASE, 30)

# 概率换书参数（仅 SWITCH_MODE='prob' 时生效）
SWITCH_BASE_PROB = 0.05      # 基础换书概率 5%
SWITCH_PROB_INCREASE = 0.02  # 每连续读一次增加 2%，上限 50%

# 按书籍配置阅读次数（代码内配置，非环境变量）
# 格式: "book_id": 次数 或 "book_id": (min, max)
BOOK_READ_COUNTS = {}
# 需要推送时可选，可选pushplus、wxpusher、telegram
PUSH_METHOD = "" or os.getenv('PUSH_METHOD')
# pushplus推送时需填
PUSHPLUS_TOKEN = "" or os.getenv("PUSHPLUS_TOKEN")
# telegram推送时需填
TELEGRAM_BOT_TOKEN = "" or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "" or os.getenv("TELEGRAM_CHAT_ID")
# wxpusher推送时需填
WXPUSHER_SPT = "" or os.getenv("WXPUSHER_SPT")
# read接口的bash命令，本地部署时可对应替换headers、cookies
curl_str = os.getenv('WXREAD_CURL_BASH')

# headers、cookies是一个省略模版，本地或者docker部署时对应替换
cookies = {

}

headers = {

}


# 书籍与对应章节映射
BOOKS = {
    "df332000813ab7ba6g013fc6": [
        "f09320f026af0935e4cd23d", "65b326f026965b9eea6e6e1", "a3c320b026ca3c65c297000", "7ef321f02967ef605fc8aef",
        "82132e402af82161242862a", "4c5320902b64c5bde74a8bf", "cfe323102becfecdb2760af", "0aa32fc02bf0aa1883c60ae",
        "eae326902cdeae27d77c749", "8f5324f02b38f53295a731e", "bd432fb02a1bd4c9ab736c3"
    ],
    "b6632b2071bf49e5b66c4b7": [
        "65132ca01b6512bd43d90e3", "c20321001cc20ad4d76f5ae", "c51323901dc51ce410c121b", "aab325601eaab3238922e53",
        "d3d322001ad3d9446802347", "45c322601945c48cce2e120", "c9f326d018c9f0f895fb5e4", "8f132430178f14e45fce0f7",
        "16732dc0161679091c5aeb1", "e4d32d5015e4da3b7fbb1fa"
    ],
    "8cb322605e2c008cb4c4217": [
        "92c3210025c92cc22753209", "98d321b025d98dce83da05a", "f8932dd0264f899139df0ae", "697324802676974ce5aceab",
        "c9e32940268c9e1074f5bc6", "65b326f026965b9eea6e6e1", "c45328f0274c45147dee704", "9b832a602829b86192511b5",
        "1af32e502831afa34a7fe44", "1af32e502831afa34a7fe44"
    ]
}

# 保留独立列表供兼容使用
book = list(BOOKS.keys())
chapter = [c for chs in BOOKS.values() for c in chs]

"""
建议保留区域|默认读三体，其它书籍自行测试时间是否增加
这里b对应书籍ID，c对应章节ID
"""
data = {
    'appId': 'wb182564874663h1130303403',
    'b': 'df332000813ab7ba6g013fc6',
    'c': 'f09320f026af0935e4cd23d',
    'ci': 53,
    'co': 354,
    'sm': '江河日下Mac刚问世的时候曾引发追捧，但',
    'pr': 0,
    'rt': 14,
    'ts': 1782200567409,
    'rn': 327,
    'sg': 'af6087e285cc8d57f2fe3d605311eb4d3866f5cfff826d3bf591f67aaccb41af',
    'ct': 1782200567,
    'ps': 'b3332f207a9f6c13g010c1e',
    'pc': '64b32fc07a9f6c13g0165f9',
    's': '560210c4',
}


def convert(curl_command):
    """提取bash接口中的headers与cookies
    支持 -H 'Cookie: xxx' 和 -b 'xxx' 两种方式的cookie提取
    """
    # 提取 headers
    headers_temp = {}
    for match in re.findall(r"-H '([^:]+): ([^']+)'", curl_command):
        headers_temp[match[0]] = match[1]

    # 提取 cookies
    cookies = {}
    
    # 从 -H 'Cookie: xxx' 提取
    cookie_header = next((v for k, v in headers_temp.items() 
                         if k.lower() == 'cookie'), '')
    
    # 从 -b 'xxx' 提取
    cookie_b = re.search(r"-b '([^']+)'", curl_command)
    cookie_string = cookie_b.group(1) if cookie_b else cookie_header
    
    # 解析 cookie 字符串
    if cookie_string:
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key.strip()] = value.strip()
    
    # 移除 headers 中的 Cookie/cookie
    headers = {k: v for k, v in headers_temp.items() 
              if k.lower() != 'cookie'}

    return headers, cookies


headers, cookies = convert(curl_str) if curl_str else (headers, cookies)
