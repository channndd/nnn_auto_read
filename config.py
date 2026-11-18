# config.py 自定义配置,包括阅读次数、推送token的填写
import os
import re
import random
import shlex

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


def _env_bool(name, default):
    """解析布尔环境变量，未配置时使用默认值"""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_secret_file(path):
    """读取敏感配置文件，不在异常信息中输出文件内容"""
    if not path:
        return ""
    expanded = os.path.expandvars(os.path.expanduser(path))
    try:
        with open(expanded, "r", encoding="utf-8") as secret_file:
            return secret_file.read().strip()
    except OSError as exc:
        raise ValueError(f"无法读取敏感配置文件：{expanded}") from exc

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
# 需要推送时可选，支持单渠道或多渠道，例如：email,telegram
PUSH_METHOD = "" or os.getenv("PUSH_METHODS") or os.getenv("PUSH_METHOD")
# pushplus推送时需填
PUSHPLUS_TOKEN = "" or os.getenv("PUSHPLUS_TOKEN")
# telegram推送时需填
TELEGRAM_BOT_TOKEN = "" or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "" or os.getenv("TELEGRAM_CHAT_ID")
# wxpusher推送时需填
WXPUSHER_SPT = "" or os.getenv("WXPUSHER_SPT")

# email推送时支持 provider 预设：qq、163、gmail、outlook、custom
EMAIL_PROVIDER = (os.getenv("EMAIL_PROVIDER") or "custom").strip().lower()
_EMAIL_PROVIDER_PRESETS = {
    "qq": {"host": "smtp.qq.com", "port": 587, "tls": True, "ssl": False},
    "163": {"host": "smtp.163.com", "port": 587, "tls": True, "ssl": False},
    "gmail": {"host": "smtp.gmail.com", "port": 587, "tls": True, "ssl": False},
    "outlook": {"host": "smtp.office365.com", "port": 587, "tls": True, "ssl": False},
    "custom": {"host": "", "port": 587, "tls": True, "ssl": False},
}
if EMAIL_PROVIDER not in _EMAIL_PROVIDER_PRESETS:
    raise ValueError(
        "EMAIL_PROVIDER 仅支持：qq、163、gmail、outlook、custom"
    )
_EMAIL_PRESET = _EMAIL_PROVIDER_PRESETS[EMAIL_PROVIDER]

# SMTP 基础配置；已有环境变量优先于 provider 预设
EMAIL_SMTP_HOST = "" or os.getenv("EMAIL_SMTP_HOST") or _EMAIL_PRESET["host"]
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT") or _EMAIL_PRESET["port"])
EMAIL_SMTP_USERNAME = "" or os.getenv("EMAIL_SMTP_USERNAME")
EMAIL_SMTP_USE_TLS = _env_bool("EMAIL_SMTP_USE_TLS", _EMAIL_PRESET["tls"])
EMAIL_SMTP_USE_SSL = _env_bool("EMAIL_SMTP_USE_SSL", _EMAIL_PRESET["ssl"])
# 密码文件优先于环境变量，适合 Docker Secret/只读挂载文件
EMAIL_SMTP_PASSWORD_FILE = "" or os.getenv("EMAIL_SMTP_PASSWORD_FILE")
EMAIL_SMTP_PASSWORD = (
    _read_secret_file(EMAIL_SMTP_PASSWORD_FILE)
    if EMAIL_SMTP_PASSWORD_FILE
    else "" or os.getenv("EMAIL_SMTP_PASSWORD")
)
# 发件人默认使用登录账号，收件人默认使用发件人
EMAIL_FROM = "" or os.getenv("EMAIL_FROM") or EMAIL_SMTP_USERNAME
EMAIL_TO = "" or os.getenv("EMAIL_TO") or EMAIL_FROM
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


def _parse_curl_args(curl_command):
    """将 Bash/cURL 命令拆分为参数，兼容单双引号、换行和常见长/短参数"""
    try:
        return shlex.split(curl_command, posix=True)
    except ValueError as exc:
        raise ValueError(f"WXREAD_CURL_BASH 引号或转义格式有误：{exc}") from exc


def _take_option_value(tokens, index, short_option, long_option):
    """读取命令行选项值，支持 --header=xxx、-H xxx 和 -Hxxx"""
    token = tokens[index]
    if token in (short_option, long_option):
        if index + 1 >= len(tokens):
            raise ValueError(f"WXREAD_CURL_BASH 中 {token} 缺少参数值")
        return tokens[index + 1], index + 2

    for prefix in (f"{long_option}=", f"{short_option}="):
        if token.startswith(prefix):
            return token[len(prefix):], index + 1

    if token.startswith(short_option) and len(token) > len(short_option):
        return token[len(short_option):], index + 1

    return None, index


def _parse_cookie_string(cookie_string):
    """解析 Cookie 字符串，兼容分号后有无空格"""
    parsed = {}
    for item in re.split(r";\s*", cookie_string.strip()):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key.strip():
            parsed[key.strip()] = value.strip()
    return parsed


def convert(curl_command):
    """提取 Bash/cURL 命令中的 headers 与 cookies"""
    if not curl_command or not curl_command.strip():
        raise ValueError("WXREAD_CURL_BASH 为空")

    tokens = _parse_curl_args(curl_command)
    headers_temp = {}
    cookie_parts = []

    index = 0
    while index < len(tokens):
        start_index = index
        header_value, index = _take_option_value(tokens, index, "-H", "--header")
        if header_value is not None:
            name, separator, value = header_value.partition(":")
            if not separator or not name.strip():
                raise ValueError(f"WXREAD_CURL_BASH 中 Header 格式有误：{header_value}")
            headers_temp[name.strip()] = value.strip()
            continue

        cookie_value, index = _take_option_value(tokens, index, "-b", "--cookie")
        if cookie_value is not None:
            cookie_parts.append(cookie_value)

        if index == start_index:
            index += 1

    cookie_header = next(
        (value for key, value in headers_temp.items() if key.lower() == "cookie"),
        "",
    )
    if cookie_header:
        cookie_parts.insert(0, cookie_header)

    cookies = {}
    for cookie_string in cookie_parts:
        cookies.update(_parse_cookie_string(cookie_string))

    headers = {
        key: value for key, value in headers_temp.items()
        if key.lower() != "cookie"
    }

    if not headers and not cookies:
        raise ValueError(
            "WXREAD_CURL_BASH 未解析到 Header 或 Cookie，请确认复制的是 read 接口的 Bash/cURL 命令"
        )

    return headers, cookies


def validate_request_config():
    """启动前校验请求配置，避免把配置缺失误报成密钥刷新失败"""
    if not headers or not cookies:
        raise ValueError(
            "请求配置缺失：请设置 WXREAD_CURL_BASH，或在 config.py 中填写 headers 和 cookies"
        )


headers, cookies = convert(curl_str) if curl_str else (headers, cookies)
