# -*- coding: utf-8 -*-
"""
KMT パーツ返却申請メール送信システム - メール本文生成 & SMTP送信
"""
import os
import smtplib
import ssl
import certifi
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

import config


def _build_serial_line(building_label, serials):
    """
    Y2: S/N：”XXXX”,”XXXX”,”XXXX”　合計XX台
    0件の場合は Y2: S/N：回収なし
    """
    if not serials:
        return f"{building_label}: S/N：回収なし"
    quoted = ",".join(f"”{s}”" for s in serials)
    return f"{building_label}: S/N：{quoted}　合計{len(serials)}台"


def build_collection_mail(mail_date, y2_serials, y5_serials):
    """回収依頼ありメールの件名・本文を組み立てる"""
    subject = f"【Mesa2】セットパーツ回収連絡メール{mail_date}回収分"

    y2_line = _build_serial_line("Y2", y2_serials)
    y5_line = _build_serial_line("Y5", y5_serials)

    y2_count = len(y2_serials)
    y5_count = len(y5_serials)
    total_count = y2_count + y5_count

    table = (
        "建屋\t個数\n"
        f"Y2\t{y2_count}\n"
        f"Y5\t{y5_count}"
    )

    body = f"""各位
お疲れ様です。本日（{mail_date}）分セットパーツ回収のご連絡です。

{y2_line}
{y5_line}

倉庫ご担当者様、お疲れ様です。
本日、回収いただくKitは以下の通りです。ご対応の程よろしくお願いいたします。

クリテック行き Dirty Kit 合計{total_count}件
{table}

以上よろしくお願いいたします。
"""
    return subject, body


def build_no_collection_mail(mail_date):
    """回収依頼なしメールの件名・本文を組み立てる"""
    subject = "【Mesa2】セットパーツ回収連依頼ありません"
    body = f"""各位
お疲れ様です。本日（{mail_date}）分セットパーツ回収の依頼はございません。
以上よろしくお願いいたします。
"""
    return subject, body


def build_hold_notice_mail(processed_at_str, mail_date, y2_serials, y5_serials):
    """送信保留（時間外実行）の内部通知メール"""
    subject = "■回収連絡メール保留あり"

    y2_line = _build_serial_line("Y2", y2_serials)
    y5_line = _build_serial_line("Y5", y5_serials)

    # processed_at_str: "YYYY-MM-DD HH:MM:SS"
    dt_part, time_part = processed_at_str.split(" ")
    yyyy, mm, dd = dt_part.split("-")
    hh, mi, _ = time_part.split(":")

    body = f"""各位
お疲れ様です。本日セットパーツ回収の連絡メールが送信対象時間外に実行されたため、
以下のセットについて「保留（送信処理未実施）」としました。

{y2_line}
{y5_line}

上記の回収連絡は{mm}月{dd}日{hh}時{mi}分に実行されましたが、対応時間外のためキャンセルされました。
本日のFRAT貼り付けがあればそちらと合わせて合算処理をお願いします。
本日貼り付け分がない場合は13:00以降に上記のS/Nの回収依頼を送信願います。
"""
    return subject, body


def _get_smtp_password():
    pw = os.environ.get(config.SMTP_PASSWORD_ENV)
    if not pw:
        raise RuntimeError(
            f"環境変数 {config.SMTP_PASSWORD_ENV} が設定されていません。"
        )
    return pw


def send_mail(subject, body, to_list, cc_list=None):
    """
    kmt_parts_control@kmtech.jp を表示元・返信先として、
    mail.kmtech.jp:465 (SSL) 経由で y-wakasa@kmtech.jp 認証で送信する。
    """
    if cc_list is None:
        cc_list = []
    if not to_list:
        raise ValueError("宛先(To)が設定されていません。先に宛先設定を行ってください。")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header("KMT Parts Control", "utf-8")), config.MAIL_FROM_DISPLAY))
    msg["Reply-To"] = config.MAIL_REPLY_TO
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    all_recipients = to_list + cc_list

    password = _get_smtp_password()
    context = ssl.create_default_context(cafile=certifi.where())

    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=context) as server:
        server.login(config.SMTP_USER, password)
        server.sendmail(config.MAIL_FROM_DISPLAY, all_recipients, msg.as_string())


def send_internal_notice(subject, body):
    """内部通知（保留通知など）を INTERNAL_NOTIFY_TO 宛に送信"""
    send_mail(subject, body, [config.INTERNAL_NOTIFY_TO])
