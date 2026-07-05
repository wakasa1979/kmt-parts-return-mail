# -*- coding: utf-8 -*-
"""
KMT パーツ返却申請メール送信システム - 翌8:56自動送信スクリプト
GitHub Actions から毎日 23:56 UTC (JST 8:56) に実行される想定。

処理内容:
1. ReturnMail_SendQueue から status=pending の行をすべて取得
2. 各行について、実際にメールを送信
3. 送信できたら ReturnMail_History に記録し、SendQueue から削除
4. 送信に失敗した行は削除せず残す（次回実行時に再試行される）
"""
import sys

import config
import mailer
import sheets_client


def process_queue():
    pending_rows = sheets_client.get_pending_queue_rows()

    if not pending_rows:
        print("送信待ちのキューはありません。")
        return

    print(f"{len(pending_rows)}件の送信待ちキューを処理します。")

    # 行番号が大きい方から処理する（削除時に後続行の番号がズレないようにするため）
    pending_rows.sort(key=lambda x: x[0], reverse=True)

    to_list, cc_list = sheets_client.get_recipients()

    success_count = 0
    failure_count = 0

    for row_number, row_data, header in pending_rows:
        record = dict(zip(header, row_data))

        mail_type = record.get("mail_type", "")
        send_target_date = record.get("send_target_date", "")
        y2_serials = [s for s in record.get("y2_serials", "").split(",") if s]
        y5_serials = [s for s in record.get("y5_serials", "").split(",") if s]
        queue_id = record.get("queue_id", "")

        try:
            if mail_type == "collection":
                subject, body = mailer.build_collection_mail(send_target_date, y2_serials, y5_serials)
            elif mail_type == "no_collection":
                subject, body = mailer.build_no_collection_mail(send_target_date)
            else:
                raise ValueError(f"不明な mail_type です: {mail_type}")

            mailer.send_mail(subject, body, to_list, cc_list)
            sheets_client.add_history_record(mail_type, send_target_date, y2_serials, y5_serials)
            sheets_client.delete_queue_row(row_number)

            print(f"[成功] queue_id={queue_id} を送信し、Historyに記録・SendQueueから削除しました。")
            success_count += 1

        except Exception as e:
            print(f"[失敗] queue_id={queue_id} の送信中にエラーが発生しました: {e}")
            failure_count += 1

    print(f"処理完了: 成功 {success_count} 件、失敗 {failure_count} 件")

    if failure_count > 0:
        # 失敗があった場合はGitHub Actions側で失敗として検知できるよう、
        # 終了コードを1にする
        sys.exit(1)


if __name__ == "__main__":
    process_queue()
