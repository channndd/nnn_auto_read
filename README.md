# 微信读书自动阅读

本项目复制自 [wxread](https://github.com/findmover/wxread)。感谢分享！

📌 本项目为原项目的复制版本，当前主要用于：

✅ 个人学习和研究用途  
🚧 可能进行后续修改与功能探索（增加了重试、多书籍阅读、概率换书等）  
📂 保留基本原始代码结构及大部分实现逻辑  

---

## 功能特性

- **自动阅读**：模拟微信读书阅读请求，自动刷阅读时长
- **多书籍阅读**：支持多本书籍配置，随机选择书籍和对应章节
- **概率换书**：模拟真实用户阅读行为，支持固定次数或概率换书模式
- **阅读波动**：自动在基础值上做百分比随机波动，每天阅读时长自然差异
- **消息推送**：支持 PushPlus、Telegram、WxPusher 多种推送方式
- **Docker 部署**：内置 cron 定时任务，支持容器化部署

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourname/nnn_auto_read.git
cd nnn_auto_read
```

### 2. 配置 `config.py`

核心配置（环境变量或代码内修改）：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `READ_NUM` | 60 | 基础阅读总次数（约30分钟） |
| `BOOK_READ_COUNT` | 10 | 每本书连续阅读次数（约5分钟） |
| `SWITCH_MODE` | count | 换书模式：`count`(固定次数) / `prob`(概率换书) |

### 3. 填充请求头

在 `config.py` 中填写 `headers` 和 `cookies`，或通过 `WXREAD_CURL_BASH` 环境变量自动解析。

### 4. 运行

```bash
pip install requests
python main.py
```

### 5. Docker 部署

```bash
docker build -t wxread-auto .
docker run -d wxread-auto
```

---

## 核心配置说明

### 环境变量

```bash
# 核心参数（只有这3个）
READ_NUM=60                    # 基础阅读总次数，程序自动 ±20% 波动
BOOK_READ_COUNT=10             # 每本书读几次后换书，程序自动 ±30% 波动
SWITCH_MODE=count              # 换书模式：count / prob

# 推送配置（可选）
PUSH_METHOD=pushplus           # 推送方式：pushplus / telegram / wxpusher
PUSHPLUS_TOKEN=your_token      # PushPlus Token
```

### 书籍配置

在 `config.py` 的 `BOOKS` 中配置书籍和章节映射：

```python
BOOKS = {
    "df332000813ab7ba6g013fc6": [
        "f09320f026af0935e4cd23d", "65b326f026965b9eea6e6e1", ...
    ],
    "b6632b2071bf49e5b66c4b7": [
        "65132ca01b6512bd43d90e3", "c20321001cc20ad4d76f5ae", ...
    ],
}
```

### 按书配置阅读次数

```python
BOOK_READ_COUNTS = {
    "df332000813ab7ba6g013fc6": (8, 15),   # 这本读 8~15 次
    "b6632b2071bf49e5b66c4b7": 12,        # 这本固定读 12 次
}
```

### 换书模式

- **count 模式**：每本书读够次数后换书
- **prob 模式**：概率换书，越读越容易换（初始 5%，每次增加 2%，上限 50%）

---

## 请求字段解释

| 字段 | 示例值 | 解释 |
|------|--------|------|
| `appId` | `wbxxxxxxxxxxxxxxxxxxxxxxxx` | 应用的唯一标识符 |
| `b` | `ce032b305a9bc1ce0b0dd2a` | 书籍或章节的唯一标识符 |
| `c` | `0723244023c072b030ba601` | 内容的唯一标识符，可能是页面或具体段落 |
| `ci` | 60 | 章节或部分的索引 |
| `co` | 336 | 内容的具体位置或页码 |
| `sm` | `[插图]威慑纪元61年...` | 当前阅读的内容描述或摘要 |
| `pr` | 65 | 页码或段落索引 |
| `rt` | 88 | 阅读时长或阅读进度 |
| `ts` | `1727580815581` | 时间戳，表示请求发送的具体时间（毫秒级） |
| `rn` | 114 | 随机数或请求编号，用于标识唯一的请求 |
| `sg` | `bfdf7de2...` | 安全签名，用于验证请求的合法性和完整性 |
| `ct` | `1727580815` | 时间戳，表示请求发送的具体时间（秒级） |
| `ps` | `xxxxxxxx...` | 用户标识符或会话标识符，用于追踪用户或会话 |
| `pc` | `xxxxxxxx...` | 设备标识符或客户端标识符，用于标识用户的设备或客户端 |
| `s` | `fadcb9de` | 校验和或哈希值，用于验证请求数据的完整性 |

---

## 项目结构

```
nnn_auto_read/
├── main.py          # 主逻辑：字段拼接、模拟请求
├── config.py        # 配置：阅读次数、推送 Token、请求头/Cookie、书籍/章节
├── push.py          # 推送模块：PushPlus / Telegram / WxPusher
├── Dockerfile       # Docker 镜像构建
└── README.md        # 项目说明
```

---

## 注意事项

- 本项目仅供个人学习和研究使用
- 请合理控制阅读频率，避免频繁请求
- Cookie 和请求头需要从浏览器开发者工具中获取
