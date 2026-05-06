# config.py 自定义配置,包括阅读次数、推送token的填写
import os
import re

"""
可修改区域
默认使用本地值如果不存在从环境变量中获取值
"""

# 阅读次数 默认30分钟
READ_NUM = int(os.getenv('READ_NUM') or 60)
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
    "b6632b2071bf49e5b66c4b7"
]

# 章节
chapter = [
    "65132ca01b6512bd43d90e3","c20321001cc20ad4d76f5ae","c51323901dc51ce410c121b","aab325601eaab3238922e53",
    "d3d322001ad3d9446802347","45c322601945c48cce2e120","c9f326d018c9f0f895fb5e4","8f132430178f14e45fce0f7",
    "16732dc0161679091c5aeb1","e4d32d5015e4da3b7fbb1fa"
]

"""
建议保留区域|默认读三体，其它书籍自行测试时间是否增加
这里b对应书籍ID，c对应章节ID
"""
data = {
    'appId': 'wb182564874663h2089991305',
    'b': '3ee32870813ab905cg018b90',
    'c': '65132ca01b6512bd43d90e3',
    'ci': 11,
    'co': 397,
    'sm': '[插图]德国人缺少了什么1在今天的德国人',
    'pr': 84,
    'rt': 17,
    'ts': 1778073945872,
    'rn': 547,
    'sg': '47125e3b3bf426d2e3e294ac8c3d81e77eaea1fb662d3aa57ce53c88164980e2',
    'ct': 1778073945,
    'ps': '42432c807a99201ag01553a',
    'pc': '17e321107a99201bg018e5f',
    's': 'cc3b0132',
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
