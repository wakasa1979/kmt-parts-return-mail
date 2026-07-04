# -*- coding: utf-8 -*-
"""保留通知メールの実送信テスト（実時刻使用）"""
import time_rules
import mailer

judgment = time_rules.judge_action()
print(f"判定結果: {judgment}")

if judgment["action"] != "hold":
    print(f"現在は hold ゾーンではありません（action={judgment['action']}）。テスト中止。")
else:
    y2_test = ["TEST-Y2-001", "TEST-Y2-002"]
    y5_test = ["TEST-Y5-001"]
    subject, body = mailer.build_hold_notice_mail(
        judgment["processed_at"], judgment["mail_date"], y2_test, y5_test
    )
    print("--- 件名 ---")
    print(subject)
    print("--- 本文 ---")
    print(body)
    mailer.send_internal_notice(subject, body)
    print("送信完了。kmt_parts_control@kmtech.jp の受信を確認してください。")
