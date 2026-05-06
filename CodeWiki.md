# 微信读书自动阅读 - Code Wiki

## 项目概述

本项目是一个微信读书自动阅读脚本，通过模拟阅读请求来实现自动刷阅读时长的功能。项目支持多种消息推送方式，可通过 GitHub Actions 或 Docker 部署运行。

- **项目来源**: 复制自 [wxread](https://github.com/findmover/wxread) 项目
- **主要用途**: 个人学习和研究
- **核心功能**: 自动模拟微信读书阅读请求，增加阅读时长

---

## 目录结构

```
/workspace/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions 工作流配置
├── .gitignore                  # Git 忽略文件配置
├── Dockerfile                  # Docker 镜像构建配置
├── README.md                   # 项目说明文档
├── co.md                       # 附加文档
├── config.py                   # 配置文件（环境变量、headers、cookies）
├── main.py                     # 主程序入口
└── push.py                     # 消息推送模块
```

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        运行环境层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 本地/Python  │  │ GitHub Actions│  │   Docker 容器    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        核心逻辑层                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                      main.py                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │  请求构造   │  │  重试机制   │  │  Cookie刷新  │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   config.py     │  │    push.py      │  │  微信读书API    │
│  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │
│  │ 环境配置  │  │  │  │PushPlus   │  │  │  │ 阅读接口  │  │
│  │ 请求头    │  │  │  │Telegram   │  │  │  │ 刷新接口  │  │
│  │ 数据模板  │  │  │  │WxPusher   │  │  │  │ 修复接口  │  │
│  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 模块职责

| 模块 | 文件 | 职责描述 |
|------|------|----------|
| 主程序 | `main.py` | 核心逻辑实现，包括请求构造、发送、重试、Cookie刷新等 |
| 配置模块 | `config.py` | 环境变量管理、请求头/Cookie解析、阅读数据模板 |
| 推送模块 | `push.py` | 支持多种推送渠道的消息通知功能 |
| CI/CD | `.github/workflows/deploy.yml` | GitHub Actions 定时任务配置 |
| 容器化 | `Dockerfile` | Docker 镜像构建与定时任务配置 |

---

## 核心模块详解

### 1. main.py - 主程序模块

#### 1.1 常量定义

| 常量 | 值 | 说明 |
|------|-----|------|
| `KEY` | `"3c5c8717f3daf09iop3423zafeqoi"` | 签名加密盐值 |
| `COOKIE_DATA` | `{"rq": "%2Fweb%2Fbook%2Fread"}` | Cookie刷新请求体 |
| `READ_URL` | `https://weread.qq.com/web/book/read` | 阅读请求接口 |
| `RENEW_URL` | `https://weread.qq.com/web/login/renewal` | Cookie刷新接口 |
| `FIX_SYNCKEY_URL` | `https://weread.qq.com/web/book/chapterInfos` | SyncKey修复接口 |

#### 1.2 核心函数

##### `encode_data(data)`
- **功能**: 将字典数据编码为 URL 格式字符串
- **参数**: `data` - 待编码的字典
- **返回值**: URL 编码后的字符串
- **实现细节**: 按键排序后使用 `urllib.parse.quote` 编码

##### `cal_hash(input_string)`
- **功能**: 计算自定义哈希值（用于请求签名）
- **参数**: `input_string` - 输入字符串
- **返回值**: 16进制哈希字符串
- **算法**: 双变量异或运算，基于字符位置和 ASCII 码

##### `retry_decorator(max_retries, retry_delay)`
- **功能**: 请求重试装饰器
- **参数**:
  - `max_retries`: 最大重试次数（默认3）
  - `retry_delay`: 初始重试间隔秒数（默认2）
- **特性**: 支持指数退避策略（每次重试间隔翻倍）

##### `get_wr_skey()`
- **功能**: 刷新 Cookie 中的 `wr_skey` 密钥
- **返回值**: 新的 `wr_skey` 值（8位字符串）或 `None`
- **异常**: 网络请求失败时触发重试

##### `fix_no_synckey()`
- **功能**: 修复缺失 synckey 的问题
- **调用时机**: 当阅读响应中不包含 synckey 时

##### `refresh_cookie()`
- **功能**: 刷新 Cookie 并更新全局 cookies
- **行为**: 
  - 成功时更新 `cookies['wr_skey']`
  - 失败时推送错误通知并抛出异常

##### `post_read_request(data)`
- **功能**: 发送阅读请求
- **参数**: `data` - 阅读数据字典
- **返回值**: 响应 JSON 数据

#### 1.3 主流程逻辑

```python
1. 初始化：刷新 Cookie
2. 循环 READ_NUM 次：
   a. 移除旧签名 's'
   b. 随机选择书籍和章节
   c. 更新时间戳相关字段
   d. 计算新签名
   e. 发送阅读请求
   f. 处理响应：
      - 成功：更新进度，等待30秒
      - 无 synckey：调用修复接口
      - Cookie 过期：刷新 Cookie
3. 完成推送通知
```

---

### 2. config.py - 配置模块

#### 2.1 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `READ_NUM` | 阅读次数（每次0.5分钟） | 60（30分钟） |
| `PUSH_METHOD` | 推送方式 | 空字符串 |
| `PUSHPLUS_TOKEN` | PushPlus Token | 空字符串 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 空字符串 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 空字符串 |
| `WXPUSHER_SPT` | WxPusher SPT | 空字符串 |
| `WXREAD_CURL_BASH` | cURL 命令字符串 | None |

#### 2.2 数据结构

##### cookies / headers
- **类型**: `dict`
- **说明**: HTTP 请求所需的 Cookie 和 Header
- **初始化**: 通过 `convert()` 函数从 cURL 命令解析

##### book / chapter
- **类型**: `list`
- **说明**: 书籍ID和章节ID列表，用于随机选择
- **默认书籍**: 三体（`b6632b2071bf49e5b66c4b7`）

##### data
- **类型**: `dict`
- **说明**: 阅读请求的基础数据模板
- **关键字段**:
  - `b`: 书籍ID
  - `c`: 章节ID
  - `ct`: 当前时间戳
  - `rt`: 阅读时长（秒）
  - `ts`: 毫秒时间戳
  - `rn`: 随机数
  - `sg`: SHA256签名
  - `s`: 自定义哈希签名

#### 2.3 核心函数

##### `convert(curl_command)`
- **功能**: 从 cURL 命令提取 headers 和 cookies
- **参数**: `curl_command` - cURL 命令字符串
- **返回值**: `(headers, cookies)` 元组
- **支持格式**:
  - `-H 'Cookie: xxx'` 方式
  - `-b 'xxx'` 方式

---

### 3. push.py - 消息推送模块

#### 3.1 PushNotification 类

##### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `pushplus_url` | str | PushPlus API 地址 |
| `telegram_url` | str | Telegram Bot API 地址模板 |
| `wxpusher_simple_url` | str | WxPusher 极简推送地址模板 |
| `headers` | dict | 默认请求头 |
| `proxies` | dict | 代理配置（从环境变量读取） |

##### 方法

###### `push_pushplus(content, token)`
- **功能**: PushPlus 消息推送
- **重试策略**: 最多5次，失败后随机等待3-6分钟重试
- **超时**: 10秒

###### `push_telegram(content, bot_token, chat_id)`
- **功能**: Telegram 消息推送
- **特性**: 
  - 先尝试代理发送
  - 代理失败后自动直连
- **超时**: 30秒

###### `push_wxpusher(content, spt)`
- **功能**: WxPusher 极简推送
- **重试策略**: 最多5次，失败后随机等待3-6分钟重试
- **超时**: 10秒

#### 3.2 统一推送接口

##### `push(content, method)`
- **功能**: 统一的消息推送入口
- **参数**:
  - `content`: 消息内容
  - `method`: 推送方式（`pushplus`/`telegram`/`wxpusher`）
- **异常**: 无效推送方式时抛出 `ValueError`

---

## 依赖关系

### 模块依赖图

```
                    ┌─────────────┐
                    │   main.py   │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  config.py  │  │   push.py   │  │  requests   │
    └─────────────┘  └──────┬──────┘  │   json      │
                            │         │   hashlib   │
                            │         │   urllib    │
                            │         └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  config.py  │
                     └─────────────┘
```

### 外部依赖

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| `requests` | >=2.32.3 | HTTP 请求 |
| `urllib3` | >=2.2.3 | URL 处理 |
| `certifi` | 2024.8.30 | SSL 证书验证 |
| `charset-normalizer` | 3.4.0 | 字符编码 |
| `idna` | 3.10 | 国际化域名处理 |

---

## 部署方式

### 1. GitHub Actions 部署

**配置文件**: `.github/workflows/deploy.yml`

#### 触发条件
- **定时触发**: 每天北京时间 05:00（UTC 21:00）
- **手动触发**: 支持 `workflow_dispatch`

#### Secrets 配置

| Secret | 说明 |
|--------|------|
| `WXREAD_CURL_BASH` | 微信读书阅读接口的 cURL 命令 |
| `PUSH_METHOD` | 推送方式 |
| `PUSHPLUS_TOKEN` | PushPlus Token |
| `WXPUSHER_SPT` | WxPusher SPT |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |

#### Variables 配置

| Variable | 说明 |
|----------|------|
| `READ_NUM` | 阅读次数 |

#### 工作流步骤
1. 设置 DNS 为 Google DNS
2. 检出代码
3. 设置 Python 3.10 环境
4. 安装依赖
5. 运行主程序

### 2. Docker 部署

**配置文件**: `Dockerfile`

#### 基础镜像
- `python:3.10-slim`

#### 系统依赖
- `cron` - 定时任务

#### Python 依赖
- `requests>=2.32.3`
- `urllib3>=2.2.3`

#### 定时任务
- **执行时间**: 每天凌晨 1:00
- **日志位置**: `/app/logs/YYYY-MM-DD.log`

#### 环境变量
- `TZ=Asia/Shanghai` - 时区设置
- `PATH` - 包含 Python 可执行文件路径

#### 启动命令
```bash
service cron start && tail -f /dev/null
```

### 3. 本地部署

#### 步骤
1. 克隆仓库
2. 安装依赖：`pip install requests urllib3`
3. 配置环境变量或修改 `config.py`
4. 运行：`python main.py`

#### 必需配置
- 设置 `WXREAD_CURL_BASH` 环境变量或手动配置 `headers` 和 `cookies`

---

## 关键算法说明

### 1. 签名计算算法

#### SHA256 签名 (`sg`)
```python
sg = SHA256(f"{ts}{rn}{KEY}")
# ts: 毫秒时间戳
# rn: 随机数
# KEY: 固定盐值
```

#### 自定义哈希 (`s`)
```python
# 1. 编码数据（URL编码，按键排序）
encoded = encode_data(data)

# 2. 双变量异或运算
_7032f5 = 0x15051505
_cc1055 = _7032f5
for i from length-1 downto 0 step 2:
    _7032f5 ^= ord(char[i]) << (length-i) % 30
    _cc1055 ^= ord(char[i-1]) << i % 30

# 3. 返回16进制字符串
return hex(_7032f5 + _cc1055)[2:].lower()
```

### 2. 重试策略

#### 指数退避
```python
delay = retry_delay * (2 ** (retries - 1))
# 第1次重试: 2秒
# 第2次重试: 4秒
# 第3次重试: 8秒
```

#### 推送重试
```python
# 随机等待 3-6 分钟
sleep_time = random.randint(180, 360)
```

---

## 数据流图

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   环境变量    │────▶│  config.py   │────▶│  解析cURL    │
│   配置数据    │     │              │     │  获取headers │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  微信读书API  │◀────│   main.py    │◀────│  构造请求数据 │
│              │     │              │     │  计算签名    │
│ - 阅读接口   │     │ - 发送请求   │     │              │
│ - 刷新接口   │     │ - 处理响应   │     │              │
│ - 修复接口   │     │ - 重试逻辑   │     │              │
└──────┬───────┘     └──────┬───────┘     └──────────────┘
       │                    │
       │                    ▼
       │             ┌──────────────┐
       │             │   push.py    │
       │             │              │
       └────────────▶│ - PushPlus   │
                     │ - Telegram   │
                     │ - WxPusher   │
                     └──────────────┘
```

---

## 常见问题与调试

### 1. Cookie 过期
- **现象**: 响应中不包含 `succ`
- **处理**: 自动调用 `refresh_cookie()` 刷新

### 2. 缺少 synckey
- **现象**: 响应中包含 `succ` 但没有 `synckey`
- **处理**: 调用 `fix_no_synckey()` 修复

### 3. 推送失败
- **PushPlus/Telegram/WxPusher**: 自动重试5次
- **Telegram**: 代理失败后尝试直连

### 4. 日志查看
- **本地**: 控制台直接输出
- **Docker**: `/app/logs/YYYY-MM-DD.log`
- **GitHub Actions**: Actions 运行日志

---

## 安全注意事项

1. **敏感信息**: `WXREAD_CURL_BASH` 包含 Cookie 等敏感信息，应使用 Secrets 管理
2. **Token 保护**: 各种推送 Token 不应硬编码，使用环境变量
3. **日志脱敏**: 注意日志中可能包含敏感信息

---

## 扩展与定制

### 添加新的推送方式
1. 在 `PushNotification` 类中添加新方法
2. 在 `push()` 函数中添加对应分支

### 修改阅读书籍
1. 在 `config.py` 中修改 `book` 和 `chapter` 列表
2. 更新 `data` 字典中的默认书籍信息

### 调整阅读频率
1. 修改 `READ_NUM` 环境变量
2. 修改 GitHub Actions 的 cron 表达式
3. 修改 Dockerfile 中的 cron 任务

---

## 版本历史

| 版本 | 变更内容 |
|------|----------|
| 初始版 | 复制自 wxread 项目 |
| 当前版 | 增加重试机制 |

---

## 参考链接

- [原项目 wxread](https://github.com/findmover/wxread)
- [微信读书网页版](https://weread.qq.com)
