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
    EMAIL_PROVIDER,
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

    def _email_connection_configs(self):
        """返回主 SMTP 连接和可能的备用连接，163 邮箱支持 587/TLS 与 465/SSL 自动切换"""
        primary = {
            "port": EMAIL_SMTP_PORT,
            "use_tls": EMAIL_SMTP_USE_TLS,
            "use_ssl": EMAIL_SMTP_USE_SSL,
            "label": "当前配置",
        }
        configs = [primary]

        if EMAIL_PROVIDER == "163":
            if (
                primary["port"] == 587
                and primary["use_tls"]
                and not primary["use_ssl"]
            ):
                configs.append({
                    "port": 465,
                    "use_tls": False,
                    "use_ssl": True,
                    "label": "备用配置 465/SSL",
                })
            elif (
                primary["port"] == 465
                and primary["use_ssl"]
                and not primary["use_tls"]
            ):
                configs.append({
                    "port": 587,
                    "use_tls": True,
                    "use_ssl": False,
                    "label": "备用配置 587/TLS",
                })

        return configs

    def _send_email_once(self, content, is_success, connection_config):
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

        use_tls = connection_config["use_tls"]
        use_ssl = connection_config["use_ssl"]
        if use_tls and use_ssl:
            raise ValueError("EMAIL_SMTP_USE_TLS 与 EMAIL_SMTP_USE_SSL 不能同时开启")

        message = EmailMessage()
        message["Subject"] = f"微信阅读-{'成功' if is_success else '失败'}"
        message["From"] = EMAIL_FROM
        message["To"] = ", ".join(recipients)
        message.set_content(content)

        context = ssl.create_default_context()
        port = connection_config["port"]
        if use_ssl:
            with smtplib.SMTP_SSL(
                EMAIL_SMTP_HOST,
                port,
                timeout=30,
                context=context,
            ) as server:
                if EMAIL_SMTP_USERNAME:
                    server.login(EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(EMAIL_SMTP_HOST, port, timeout=30) as server:
                if use_tls:
                    server.starttls(context=context)
                if EMAIL_SMTP_USERNAME:
                    server.login(EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD)
                server.send_message(message)

    def push_email(self, content, is_success=True):
        """Email 消息推送，连接异常时自动尝试备用端口和加密方式"""
        connection_errors = (
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPConnectError,
            TimeoutError,
            ConnectionError,
            OSError,
        )
        configs = self._email_connection_configs()
        last_error = None

        for index, connection_config in enumerate(configs):
            label = connection_config["label"]
            try:
                self._send_email_once(content, is_success, connection_config)
            except ValueError as exc:
                logger.error("❌ 邮件配置有误: %s", exc)
                return False
            except connection_errors as exc:
                last_error = exc
                logger.error(
                    "❌ 邮件发送失败（%s，%s:%s）: %s",
                    label,
                    EMAIL_SMTP_HOST,
                    connection_config["port"],
                    exc,
                )
                if index + 1 < len(configs):
                    fallback = configs[index + 1]
                    logger.info(
                        "尝试备用 SMTP 连接：%s:%s（TLS=%s，SSL=%s）",
                        EMAIL_SMTP_HOST,
                        fallback["port"],
                        fallback["use_tls"],
                        fallback["use_ssl"],
                    )
                continue
            except smtplib.SMTPException as exc:
                last_error = exc
                logger.error("❌ 邮件发送失败（%s）: %s", label, exc)
                return False
            else:
                logger.info("✅ 邮件发送成功（%s）", label)
                return True

        if last_error:
            logger.error("❌ 所有 SMTP 连接方式均失败: %s", last_error)
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
