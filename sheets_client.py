# -*- coding: utf-8 -*-
"""
KMT パーツ返却申請メール送信システム - Google Sheets 連携モジュール
"""
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ヘッダー定義
HEADERS_SEND_QUEUE = [
    "queue_id", "created_at", "mail_type", "send_target_date",
    "y2_serials", "y5_serials", "status"
]
HEADERS_HISTORY = [
    "processed_at", "collection_date", "mail_type",
    "y2_serials", "y5_serials", "y2_count", "y5_count", "total_count"
]
HEADERS_RECIPIENTS = [
    "type", "email"
]


def get_service():
    """Google Sheets API サービスオブジェクトを取得"""
    creds = service_account.Credentials.from_service_account_file(
        config.SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def _get_sheet_values(service, sheet_name, range_suffix="A:Z"):
    result = service.spreadsheets().values().get(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{sheet_name}!{range_suffix}"
    ).execute()
    return result.get("values", [])


def ensure_headers(service, sheet_name, headers):
    """シートの1行目が空、またはヘッダーと異なる場合は書き込む"""
    values = _get_sheet_values(service, sheet_name, "A1:Z1")
    if not values or values[0] != headers:
        service.spreadsheets().values().update(
            spreadsheetId=config.SPREADSHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [headers]}
        ).execute()


def setup_all_headers():
    """3シート分のヘッダーを一括セットアップ"""
    service = get_service()
    ensure_headers(service, config.SHEET_SEND_QUEUE, HEADERS_SEND_QUEUE)
    ensure_headers(service, config.SHEET_HISTORY, HEADERS_HISTORY)
    ensure_headers(service, config.SHEET_RECIPIENTS, HEADERS_RECIPIENTS)


def append_row(service, sheet_name, row):
    service.spreadsheets().values().append(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{sheet_name}!A:Z",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]}
    ).execute()


def add_history_record(mail_type, collection_date, y2_serials, y5_serials):
    """送信履歴を History シートに追記"""
    service = get_service()
    now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    y2_count = len(y2_serials)
    y5_count = len(y5_serials)
    row = [
        now_jst.strftime("%Y-%m-%d %H:%M:%S"),
        collection_date,
        mail_type,
        ",".join(y2_serials) if y2_serials else "",
        ",".join(y5_serials) if y5_serials else "",
        str(y2_count),
        str(y5_count),
        str(y2_count + y5_count),
    ]
    append_row(service, config.SHEET_HISTORY, row)


def add_to_send_queue(mail_type, send_target_date, y2_serials, y5_serials):
    """翌8:56送信待ちとして SendQueue シートに追記"""
    service = get_service()
    now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    queue_id = now_jst.strftime("%Y%m%d%H%M%S")
    row = [
        queue_id,
        now_jst.strftime("%Y-%m-%d %H:%M:%S"),
        mail_type,
        send_target_date,
        ",".join(y2_serials) if y2_serials else "",
        ",".join(y5_serials) if y5_serials else "",
        "pending",
    ]
    append_row(service, config.SHEET_SEND_QUEUE, row)
    return queue_id


def get_pending_queue_rows():
    """status=pending の行を (行番号, 行データ) のリストで返す（行番号は1始まり、ヘッダー含む）"""
    service = get_service()
    values = _get_sheet_values(service, config.SHEET_SEND_QUEUE, "A:Z")
    if not values:
        return []
    header = values[0]
    status_idx = header.index("status") if "status" in header else 6
    rows = []
    for i, row in enumerate(values[1:], start=2):
        padded = row + [""] * (len(header) - len(row))
        if len(padded) > status_idx and padded[status_idx] == "pending":
            rows.append((i, padded, header))
    return rows


def delete_queue_row(row_number):
    """SendQueue の指定行を削除（行番号は1始まり、シート上の実際の行番号）"""
    service = get_service()
    sheet_meta = service.spreadsheets().get(spreadsheetId=config.SPREADSHEET_ID).execute()
    sheet_id = None
    for s in sheet_meta["sheets"]:
        if s["properties"]["title"] == config.SHEET_SEND_QUEUE:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        raise ValueError(f"シートが見つかりません: {config.SHEET_SEND_QUEUE}")

    requests = [{
        "deleteDimension": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": row_number - 1,
                "endIndex": row_number,
            }
        }
    }]
    service.spreadsheets().batchUpdate(
        spreadsheetId=config.SPREADSHEET_ID,
        body={"requests": requests}
    ).execute()


def get_recipients():
    """Recipients シートから To / CC のアドレスリストを取得"""
    service = get_service()
    values = _get_sheet_values(service, config.SHEET_RECIPIENTS, "A:Z")
    to_list, cc_list = [], []
    if not values or len(values) < 2:
        return to_list, cc_list
    header = values[0]
    type_idx = header.index("type") if "type" in header else 0
    email_idx = header.index("email") if "email" in header else 1
    for row in values[1:]:
        if len(row) <= max(type_idx, email_idx):
            continue
        rtype = row[type_idx].strip().lower()
        email = row[email_idx].strip()
        if not email:
            continue
        if rtype == "to":
            to_list.append(email)
        elif rtype == "cc":
            cc_list.append(email)
    return to_list, cc_list


def set_recipients(to_list, cc_list):
    """Recipients シートを To / CC のリストで上書き（既存行はクリアしてから書き直す）"""
    service = get_service()
    rows = [HEADERS_RECIPIENTS]
    for email in to_list:
        rows.append(["to", email])
    for email in cc_list:
        rows.append(["cc", email])

    # 既存データをクリア
    service.spreadsheets().values().clear(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{config.SHEET_RECIPIENTS}!A:Z",
        body={}
    ).execute()
    # 書き直し
    service.spreadsheets().values().update(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{config.SHEET_RECIPIENTS}!A1",
        valueInputOption="RAW",
        body={"values": rows}
    ).execute()
