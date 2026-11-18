# push.py 支持 PushPlus 、wxpusher、Telegram、Email 的消息推送模块
import json
import logging
import os
import random
import re
import smtplib
import ssl
import time
from email.message import EmailMessage

import requests

from config import (
    EMAIL_FROM,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PASSWORD,
    EMAIL_SMTP_PORT,
    EMAIL_SMTP_USE_SSL,
    EMAIL_SMTP_USE_TLS,
    EMAIL_SMTP_USERNAME,
    EMAIL_TO,
    PUSHPLUS_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
    WXPUSHER_SPT,
)

logger = logging.getLogger(__name__)


class PushNotification:
    def __init__(self):
        self.pushplus_url = "https://www.pushplus.plus/send"
        self.telegram_url = "https://api.telegram.org/bot{}/sendMessage"
        self.headers = {'Content-Type': 'application/json'}
        # 从环境变量获取代理设置
        self.proxies = {
            'http': os.getenv('http_proxy'),
            'https': os.getenv('https_proxy')
        }
        self.wxpusher_simple_url = "https://wxpusher.zjiecode.com/api/send/message/{}/{}"

    def push_pushplus(self, content, token, is_success=True):
        """PushPlus消息推送"""
        attempts = 5
        title = f"微信阅读-{'成功' if is_success else '失败'}"
        for attempt in range(attempts):
            try:
                response = requests.post(
                    self.pushplus_url,
                    data=json.dumps({
                        "token": token,
                        "title": title,
                        "content": content
                    }).encode('utf-8'),
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
                logger.info("✅ PushPlus响应: %s", response.text)
                return True
            except requests.exceptions.RequestException as e:
                logger.error("❌ PushPlus推送失败: %s", e)
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)
        return False

    def push_telegram(self, content, bot_token, chat_id):
        """Telegram消息推送，失败时自动尝试直连"""
        url = self.telegram_url.format(bot_token)
        payload = {"chat_id": chat_id, "text": content}

        try:
            response = requests.post(url, json=payload, proxies=self.proxies, timeout=30)
            logger.info("✅ Telegram响应: %s", response.text)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("❌ Telegram代理发送失败: %s", e)
            try:
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error("❌ Telegram发送失败: %s", e)
                return False

    def push_wxpusher(self, content, spt):
        """WxPusher消息推送（极简方式）"""
        attempts = 5
        url = self.wxpusher_simple_url.format(spt, content)

        for attempt in range(attempts):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                logger.info("✅ WxPusher响应: %s", response.text)
                return True
            except requests.exceptions.RequestException as e:
                logger.error("❌ WxPusher推送失败: %s", e)
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)
        return False

    def _send_email_once(self, content, is_success):
        """通过 SMTP 发送一封纯文本邮件"""
        required = {
            "EMAIL_SMTP_HOST": EMAIL_SMTP_HOST,
            "EMAIL_FROM": EMAIL_FROM,
            "EMAIL_TO": EMAIL_TO,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"邮件配置缺失：{', '.join(missing)}")

        recipients = [item.strip() for item in EMAIL_TO.split(",") if item.strip()]
        if not recipients:
            raise ValueError("EMAIL_TO 中未配置有效收件人")

        if bool(EMAIL_SMTP_USERNAME) != bool(EMAIL_SMTP_PASSWORD):
            raise ValueError("EMAIL_SMTP_USERNAME 与 EMAIL_SMTP_PASSWORD 必须同时配置")
        if EMAIL_SMTP_USE_TLS and EMAIL_SMTP_USE_SSL:
            raise ValueError("EMAIL_SMTP_USE_TLS 与 EMAIL_SMTP_USE_SSL 不能同时开启")

        message = EmailMessage()
        message["Subject"] = f"微信阅读-{'成功' if is_success else '失败'}"
        message["From"] = EMAIL_FROM
        message["To"] = ", ".join(recipients)
        message.set_content(content)

        context = ssl.create_default_context()
        if EMAIL_SMTP_USE_SSL:
            with smtplib.SMTP_SSL(
                EMAIL_SMTP_HOST,
                EMAIL_SMTP_PORT,
                timeout=30,
                context=context,
            ) as server:
                if EMAIL_SMTP_USERNAME:
                    server.login(EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=30) as server:
                if EMAIL_SMTP_USE_TLS:
                    server.starttls(context=context)
                if EMAIL_SMTP_USERNAME:
                    server.login(EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD)
                server.send_message(message)

    def push_email(self, content, is_success=True):
        """Email 消息推送"""
        attempts = 3
        for attempt in range(attempts):
            try:
                self._send_email_once(content, is_success)
                logger.info("✅ 邮件发送成功")
                return True
            except ValueError as e:
                logger.error("❌ 邮件配置有误: %s", e)
                return False
            except (smtplib.SMTPException, OSError) as e:
                logger.error("❌ 邮件发送失败: %s", e)
                if attempt < attempts - 1:
                    sleep_time = 2 ** attempt
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)
        return False


"""外部调用"""


def _parse_push_methods(method):
    """解析单个或多个推送渠道，支持逗号、中文逗号、分号和空格分隔"""
    if method in (None, ""):
        return []
    methods = re.split(r"[,，;\s]+", str(method).strip())
    return list(dict.fromkeys(item.lower() for item in methods if item))


def _push_single(notifier, method, content, is_success):
    """发送到单个推送渠道"""
    if method == "pushplus":
        return notifier.push_pushplus(content, PUSHPLUS_TOKEN, is_success)
    if method == "telegram":
        return notifier.push_telegram(content, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    if method == "wxpusher":
        return notifier.push_wxpusher(content, WXPUSHER_SPT)
    if method == "email":
        return notifier.push_email(content, is_success)

    logger.warning(
        "❌ 无效的通知渠道 '%s'，已跳过推送。支持：pushplus、telegram、wxpusher、email",
        method,
    )
    return False


def push(content, method, is_success=True):
    """统一推送接口，支持 PushPlus、Telegram、WxPusher 和 Email，可同时配置多个渠道"""
    methods = _parse_push_methods(method)
    if not methods:
        logger.warning("未配置推送渠道，跳过推送。")
        return False

    notifier = PushNotification()
    results = {}
    for item in methods:
        results[item] = _push_single(notifier, item, content, is_success)

    if len(results) > 1:
        logger.info("推送结果：%s", results)
    return any(results.values())
