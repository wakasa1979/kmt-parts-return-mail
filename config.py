# -*- coding: utf-8 -*-
"""
KMT パーツ返却申請メール送信システム - 設定ファイル
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ===== Google Sheets 設定 =====
SPREADSHEET_ID = "1e_GthM95-qeEKN3R3zSksv1udQ0OHQ6W3lYOGpXX00I"
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "credentials", "service-account-key.json")

SHEET_SEND_QUEUE = "ReturnMail_SendQueue"
SHEET_HISTORY = "ReturnMail_History"
SHEET_RECIPIENTS = "ReturnMail_Recipients"

# ===== SMTP 設定 =====
SMTP_HOST = "mail.kmtech.jp"
SMTP_PORT = 465
SMTP_USER = "y-wakasa@kmtech.jp"
# SMTPパスワードは環境変数から取得（ローカル実行時は .env、GitHub Actionsでは Secrets）
SMTP_PASSWORD_ENV = "KMT_SMTP_PASSWORD"

MAIL_FROM_DISPLAY = "kmt_parts_control@kmtech.jp"
MAIL_REPLY_TO = "kmt_parts_control@kmtech.jp"

# 内部通知（送信保留時）の宛先
INTERNAL_NOTIFY_TO = "kmt_parts_control@kmtech.jp"

# ===== 棟（建屋）設定 =====
BUILDINGS = {
    "Y2": {"max_slots": 8, "label": "Y2"},
    "Y5": {"max_slots": 16, "label": "Y5"},
}

# ===== 時間帯ルール（JST） =====
# 06:00-08:55 : 即時送信・当日日付
# 08:55-13:00 : 送信キャンセル・保留通知
# 13:00-23:59 : 翌8:56まで待機・翌日日付
TIME_IMMEDIATE_START = (6, 0)
TIME_IMMEDIATE_END = (8, 55)
TIME_HOLD_START = (8, 55)
TIME_HOLD_END = (13, 0)
TIME_QUEUE_START = (13, 0)
TIME_QUEUE_END = (23, 59)

SCHEDULED_SEND_HOUR = 8
SCHEDULED_SEND_MINUTE = 56
