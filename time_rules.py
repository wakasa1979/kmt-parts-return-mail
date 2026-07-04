# -*- coding: utf-8 -*-
"""
KMT パーツ返却申請メール送信システム - 時間帯判定ロジック
"""
import datetime

import config


def now_jst():
    """現在時刻をJSTで取得（bash/pythonのタイムゾーン設定に依存しない）"""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def judge_action(dt=None):
    """
    時刻に応じたアクションを判定する。

    戻り値: dict
      {
        "action": "immediate" | "hold" | "queue",
        "mail_date": "YYYY年MM月DD日" 形式の、メールに記載すべき日付,
        "mail_date_iso": "YYYY-MM-DD",
      }
    """
    if dt is None:
        dt = now_jst()

    t = (dt.hour, dt.minute)

    # 06:00 <= t < 08:55 : 即時送信・当日日付
    if (6, 0) <= t < (8, 55):
        action = "immediate"
        mail_dt = dt

    # 08:55 <= t < 13:00 : キャンセル・保留通知
    elif (8, 55) <= t < (13, 0):
        action = "hold"
        mail_dt = dt

    # 13:00 <= t <= 23:59 : キュー登録・翌日日付
    elif (13, 0) <= t:
        action = "queue"
        mail_dt = dt + datetime.timedelta(days=1)

    # 0:00-5:59 は運用上発生しない想定だが、フォールバックとして即時扱いにする
    else:
        action = "immediate"
        mail_dt = dt

    return {
        "action": action,
        "mail_date": mail_dt.strftime("%Y年%m月%d日"),
        "mail_date_iso": mail_dt.strftime("%Y-%m-%d"),
        "processed_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
    }
