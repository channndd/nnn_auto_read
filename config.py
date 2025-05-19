# config.py 自定义配置,包括阅读次数、推送token的填写
import os
import re

"""
可修改区域
默认使用本地值如果不存在从环境变量中获取值
"""

# 阅读次数 默认40次/20分钟
READ_NUM = int(os.getenv('READ_NUM') or 40)
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


# 书籍
book = [
    "66f329607225313f66f5e78"
]

# 章节
chapter = [
    "70c322b0318970c639dfd4e","28f324e0318a28f0b864c62","154325b0318b1543843a9ca","f8c32bb0318cf8c1f23df37",
    "e46320d0318de46de7e1759","b7b320c0318eb7b16ecfa23","35232ea0318f352fe25d868"
]

"""
建议保留区域|默认读三体，其它书籍自行测试时间是否增加
"""
data = {
    'appId': 'wb182564874663h1484727348',
    'b': '66f329607225313f66f5e78',
    'c': '154325b0318b1543843a9ca',
    'ci': 395,
    'co': 362,
    'sm': '八关于新信徒的天国和勇气，我们已经受到充',
    'pr': 89,
    'rt': 13,
    'ts': 1747621040799,
    'rn': 64,
    'sg': '34652c3e77349891951ebf2b9d4a9f8d832bfeea2c9ee3c43803da5b2ab5d63a',
    'ct': 1747621040,
    'ps': '928320e07a6aa871g018d90',
    'pc': 'eb7324407a6aa875g017735',
    's': '9a969578',
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
