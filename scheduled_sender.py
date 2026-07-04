# -*- coding: utf-8 -*-
"""
KMT パーツ返却申請メール送信システム - 定期実行用送信スクリプト
毎日 JST 8:56 に GitHub Actions から実行される想定。
SendQueue の status=pending を全て処理し、送信済みは行削除する。
"""
import sys
import mailer
import sheets_client


def main():
    pending_rows = sheets_client.get_pending_queue_rows()

    if not pending_rows:
        print("送信待ちのキューはありません。")
        return

    print(f"{len(pending_rows)}件のキューを処理します。")

    to_list, cc_list = sheets_client.get_recipients()

    # 行番号が大きい順に処理（削除時のズレ防止）
    pending_rows_sorted = sorted(pending_rows, key=lambda x: x[0], reverse=True)

    success_count = 0
    error_count = 0

    for row_number, row_data, header in pending_rows_sorted:
        try:
            record = dict(zip(header, row_data))
            mail_type = record.get("mail_type", "")
            send_target_date = record.get("send_target_date", "")
            y2_serials = [s for s in record.get("y2_serials", "").split(",") if s]
            y5_serials = [s for s in record.get("y5_serials", "").split(",") if s]

            if mail_type == "collection":
                subject, body = mailer.build_collection_mail(send_target_date, y2_serials, y5_serials)
            else:
                subject, body = mailer.build_no_collection_mail(send_target_date)

            mailer.send_mail(subject, body, to_list, cc_list)
            sheets_client.add_history_record(mail_type, send_target_date, y2_serials, y5_serials)
            sheets_client.delete_queue_row(row_number)

            print(f"送信成功: row={row_number}, mail_type={mail_type}, date={send_target_date}")
            success_count += 1

        except Exception as e:
            print(f"送信失敗: row={row_number}, error={e}", file=sys.stderr)
            error_count += 1

    print(f"完了: 成功={success_count}, 失敗={error_count}")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
