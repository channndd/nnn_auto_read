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
    "8e232ec02198e296a067180","1ff325f02181ff1de7742fc","37632cd021737693cfc7149","b6d32b90216b6d767d2f0dc",
    "3c5327902153c59dc0488e1","98f3284021498f137082c2e","6f4322302126f4922f45dec","70e32fb021170efdf2eca12",
    "c7432af0210c74d97b01b1c","9bf32f301f9bf31c7ff0a60"
]

"""
建议保留区域|默认读三体，其它书籍自行测试时间是否增加
这里b对应书籍ID，c对应章节ID
"""
data = {
    'appId': 'wb182564874663h674087715',
    'b': 'b6632b2071bf49e5b66c4b7',
    'c': '8e232ec02198e296a067180',
    'ci': 25,
    'co': 377,
    'sm': '§251关于看的一些东西让我们觉得神秘，',
    'pr': 98,
    'rt': 12,
    'ts': 1763808108545,
    'rn': 790,
    'sg': 'aa91b13cd5a49c9428c10bbfe0eb4ba6be8666f70c628052972178bc17890c96',
    'ct': 1763808108,
    'ps': '302325707a835b8dg0147d0',
    'pc': '204321907a835b88g011cd3',
    's': '37b22048',
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
