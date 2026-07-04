# -*- coding: utf-8 -*-
"""時間帯ルールの境界値テスト（実時刻に依存しない）"""
import datetime
import time_rules

test_cases = [
    ("05:59", datetime.datetime(2026, 7, 4, 5, 59)),
    ("06:00", datetime.datetime(2026, 7, 4, 6, 0)),
    ("08:54", datetime.datetime(2026, 7, 4, 8, 54)),
    ("08:55", datetime.datetime(2026, 7, 4, 8, 55)),
    ("12:59", datetime.datetime(2026, 7, 4, 12, 59)),
    ("13:00", datetime.datetime(2026, 7, 4, 13, 0)),
    ("23:59", datetime.datetime(2026, 7, 4, 23, 59)),
    ("00:00", datetime.datetime(2026, 7, 4, 0, 0)),
]

print(f"{'時刻':<8} {'action':<10} {'mail_date':<14} {'mail_date_iso'}")
print("-" * 50)
for label, dt in test_cases:
    result = time_rules.judge_action(dt)
    print(f"{label:<8} {result['action']:<10} {result['mail_date']:<14} {result['mail_date_iso']}")
