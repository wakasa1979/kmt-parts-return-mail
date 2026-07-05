# -*- coding: utf-8 -*-
"""
KMT パーツ返却申請メール送信システム - GUIメイン
起動方法: python3 app.py
"""
import tkinter as tk
from tkinter import messagebox
import threading

import config
import time_rules
import mailer
import sheets_client

# ===== モダンなカラーパレット =====
COLOR_BG = "#1e2530"
COLOR_PANEL = "#2a3441"
COLOR_ACCENT = "#4f8ef7"
COLOR_ACCENT_HOVER = "#6ba3ff"
COLOR_TEXT = "#e8edf5"
COLOR_SUBTEXT = "#9aa5b5"

# 入力欄は明るめの配色に変更
COLOR_ENTRY_BG = "#f5f7fa"
COLOR_ENTRY_FG = "#1e2530"
COLOR_ENTRY_BORDER = "#c8d0da"

# ボタン色（Label疑似ボタンで使用）
COLOR_BTN_PRIMARY = "#4f8ef7"
COLOR_BTN_PRIMARY_HOVER = "#6ba3ff"
COLOR_BTN_SECONDARY = "#3a4657"
COLOR_BTN_SECONDARY_HOVER = "#48576c"
COLOR_BTN_TEXT_LIGHT = "#ffffff"
COLOR_BTN_TEXT_ON_SECONDARY = "#e8edf5"

FONT_TITLE = ("Hiragino Sans", 20, "bold")
FONT_LABEL = ("Hiragino Sans", 12, "bold")
FONT_ENTRY = ("Hiragino Sans", 12)
FONT_BUTTON = ("Hiragino Sans", 13, "bold")


class PseudoButton(tk.Label):
    """macOS Aquaテーマでも色指定が効く、Labelベースの疑似ボタン"""

    def __init__(self, parent, text, command, bg, fg, hover_bg, font=FONT_BUTTON, **kwargs):
        super().__init__(
            parent, text=text, font=font, bg=bg, fg=fg,
            cursor="hand2", padx=20, pady=14, **kwargs
        )
        self.command = command
        self.bg_normal = bg
        self.bg_hover = hover_bg
        self._enabled = True

        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_click(self, event):
        if self._enabled and self.command:
            self.command()

    def _on_enter(self, event):
        if self._enabled:
            self.configure(bg=self.bg_hover)

    def _on_leave(self, event):
        if self._enabled:
            self.configure(bg=self.bg_normal)

    def set_enabled(self, enabled):
        self._enabled = enabled
        if enabled:
            self.configure(bg=self.bg_normal, cursor="hand2")
        else:
            self.configure(bg="#555f6e", cursor="arrow")


class ReturnMailApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MESAキット回収依頼")
        self.root.configure(bg=COLOR_BG)
        self.root.geometry("980x780")

        self.entries = {}  # building -> [Entry, ...]

        self._build_ui()

    # ------------------------------------------------------------------
    # UI構築
    # ------------------------------------------------------------------
    def _build_ui(self):
        # タイトルバー
        title_frame = tk.Frame(self.root, bg=COLOR_BG)
        title_frame.pack(fill="x", padx=30, pady=(24, 10))

        tk.Label(
            title_frame, text="MESAキット回収依頼", font=FONT_TITLE,
            bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(side="left")

        settings_btn = PseudoButton(
            title_frame, text="⚙ 宛先設定", command=self.open_recipients_dialog,
            bg=COLOR_BTN_SECONDARY, fg=COLOR_BTN_TEXT_ON_SECONDARY,
            hover_bg=COLOR_BTN_SECONDARY_HOVER, font=FONT_LABEL
        )
        settings_btn.configure(padx=14, pady=6)
        settings_btn.pack(side="right")

        # 建屋ごとの入力エリア
        for building, meta in config.BUILDINGS.items():
            self._build_building_panel(building, meta["max_slots"])

        # ボタンエリア
        btn_frame = tk.Frame(self.root, bg=COLOR_BG)
        btn_frame.pack(fill="x", padx=30, pady=(10, 24))

        self.send_btn = PseudoButton(
            btn_frame, text="上記KITの回収依頼を送信", command=self.on_send_collection,
            bg=COLOR_BTN_PRIMARY, fg=COLOR_BTN_TEXT_LIGHT, hover_bg=COLOR_BTN_PRIMARY_HOVER
        )
        self.send_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.no_collection_btn = PseudoButton(
            btn_frame, text="回収依頼無しメールを送信", command=self.on_send_no_collection,
            bg=COLOR_BTN_SECONDARY, fg=COLOR_BTN_TEXT_ON_SECONDARY, hover_bg=COLOR_BTN_SECONDARY_HOVER
        )
        self.no_collection_btn.pack(side="left", expand=True, fill="x", padx=(8, 0))

        # ステータスバー
        self.status_var = tk.StringVar(value="準備完了")
        status_bar = tk.Label(
            self.root, textvariable=self.status_var, font=("Hiragino Sans", 10),
            bg=COLOR_BG, fg=COLOR_SUBTEXT, anchor="w"
        )
        status_bar.pack(fill="x", padx=30, pady=(0, 14))

    def _build_building_panel(self, building, max_slots):
        panel = tk.Frame(self.root, bg=COLOR_PANEL)
        panel.pack(fill="x", padx=30, pady=8)

        header = tk.Frame(panel, bg=COLOR_PANEL)
        header.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(
            header, text=f"{building}棟", font=FONT_LABEL,
            bg=COLOR_PANEL, fg=COLOR_ACCENT
        ).pack(side="left")
        tk.Label(
            header, text=f"（最大{max_slots}件）", font=("Hiragino Sans", 10),
            bg=COLOR_PANEL, fg=COLOR_SUBTEXT
        ).pack(side="left", padx=(6, 0))

        grid = tk.Frame(panel, bg=COLOR_PANEL)
        grid.pack(fill="x", padx=18, pady=(0, 16))

        cols = 4
        entries = []
        for i in range(max_slots):
            r, c = divmod(i, cols)
            cell = tk.Frame(grid, bg=COLOR_PANEL)
            cell.grid(row=r, column=c, padx=6, pady=4, sticky="ew")
            grid.grid_columnconfigure(c, weight=1)

            tk.Label(
                cell, text=f"{i + 1}", font=("Hiragino Sans", 9),
                bg=COLOR_PANEL, fg=COLOR_SUBTEXT, width=2
            ).pack(side="left")

            # 明るめの入力欄（枠線をFrameで作って立体感を出す）
            entry_wrap = tk.Frame(
                cell, bg=COLOR_ENTRY_BORDER
            )
            entry_wrap.pack(side="left", fill="x", expand=True, padx=(4, 0))

            entry = tk.Entry(
                entry_wrap, font=FONT_ENTRY, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
                insertbackground=COLOR_ENTRY_FG, relief="flat",
                highlightthickness=0, bd=0
            )
            entry.pack(fill="x", expand=True, ipady=5, padx=1, pady=1)
            entries.append(entry)

        self.entries[building] = entries

    # ------------------------------------------------------------------
    # データ取得
    # ------------------------------------------------------------------
    def _collect_serials(self, building):
        return [e.get().strip() for e in self.entries[building] if e.get().strip()]

    def _clear_all_entries(self):
        for entries in self.entries.values():
            for e in entries:
                e.delete(0, tk.END)

    # ------------------------------------------------------------------
    # 送信処理
    # ------------------------------------------------------------------
    def on_send_collection(self):
        y2 = self._collect_serials("Y2")
        y5 = self._collect_serials("Y5")

        if not y2 and not y5:
            messagebox.showwarning("入力なし", "シリアル番号が1件も入力されていません。")
            return

        confirm = messagebox.askyesno(
            "送信確認",
            f"Y2: {len(y2)}件\nY5: {len(y5)}件\n\nこの内容で回収依頼メールを送信しますか？"
        )
        if not confirm:
            return

        self._run_async(lambda: self._process_send("collection", y2, y5))

    def on_send_no_collection(self):
        confirm = messagebox.askyesno(
            "送信確認", "「回収依頼無し」メールを送信しますか？"
        )
        if not confirm:
            return
        self._run_async(lambda: self._process_send("no_collection", [], []))

    def _run_async(self, func):
        self.status_var.set("処理中...")
        self.send_btn.set_enabled(False)
        self.no_collection_btn.set_enabled(False)

        def wrapper():
            try:
                func()
            except Exception as e:
                self.root.after(0, lambda: self._on_error(e))
            else:
                self.root.after(0, self._on_success)

        threading.Thread(target=wrapper, daemon=True).start()

    def _on_success(self):
        self.status_var.set("完了しました")
        self.send_btn.set_enabled(True)
        self.no_collection_btn.set_enabled(True)
        self._clear_all_entries()

    def _on_error(self, error):
        self.status_var.set("エラーが発生しました")
        self.send_btn.set_enabled(True)
        self.no_collection_btn.set_enabled(True)
        messagebox.showerror("エラー", str(error))

    def _process_send(self, mail_type, y2, y5):
        judgment = time_rules.judge_action()
        action = judgment["action"]
        mail_date = judgment["mail_date"]

        if action == "hold":
            subject, body = mailer.build_hold_notice_mail(
                judgment["processed_at"], mail_date, y2, y5
            )
            mailer.send_internal_notice(subject, body)
            self.root.after(0, lambda: messagebox.showinfo(
                "送信キャンセル",
                "メール送信を実施できるのは13:00-翌朝8:55までです。"
                "先ほど送信しようとした内容はキャンセルしました。\n"
                "本日貼り付け分と合算して13:00以降に再度処理を行ってください。\n"
                "（送信キャンセルになった旨をチームメンバーに共有します。）"
            ))
            return

        if action == "queue":
            sheets_client.add_to_send_queue(mail_type, mail_date, y2, y5)
            self.root.after(0, lambda: messagebox.showinfo(
                "送信予約完了",
                f"翌朝7:00に自動送信されるよう予約しました。（対象日: {mail_date}）"
            ))
            return

        to_list, cc_list = sheets_client.get_recipients()
        if mail_type == "collection":
            subject, body = mailer.build_collection_mail(mail_date, y2, y5)
        else:
            subject, body = mailer.build_no_collection_mail(mail_date)

        mailer.send_mail(subject, body, to_list, cc_list)
        sheets_client.add_history_record(mail_type, mail_date, y2, y5)
        self.root.after(0, lambda: messagebox.showinfo("送信完了", "メールを送信しました。"))

    # ------------------------------------------------------------------
    # 宛先設定ダイアログ
    # ------------------------------------------------------------------
    def open_recipients_dialog(self):
        try:
            to_list, cc_list = sheets_client.get_recipients()
        except Exception as e:
            messagebox.showerror("エラー", f"宛先情報の取得に失敗しました:\n{e}")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("宛先設定")
        dialog.configure(bg=COLOR_BG)
        dialog.geometry("520x440")

        tk.Label(
            dialog, text="送信先メールアドレス設定", font=FONT_LABEL,
            bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(pady=(20, 10))

        tk.Label(
            dialog, text="To（1行に1アドレス）", font=("Hiragino Sans", 10),
            bg=COLOR_BG, fg=COLOR_SUBTEXT
        ).pack(anchor="w", padx=24)
        to_text = tk.Text(
            dialog, height=6, font=FONT_ENTRY, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
            insertbackground=COLOR_ENTRY_FG, relief="flat", padx=8, pady=6
        )
        to_text.pack(fill="x", padx=24, pady=(4, 12))
        to_text.insert("1.0", "\n".join(to_list))

        tk.Label(
            dialog, text="CC（1行に1アドレス）", font=("Hiragino Sans", 10),
            bg=COLOR_BG, fg=COLOR_SUBTEXT
        ).pack(anchor="w", padx=24)
        cc_text = tk.Text(
            dialog, height=6, font=FONT_ENTRY, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG,
            insertbackground=COLOR_ENTRY_FG, relief="flat", padx=8, pady=6
        )
        cc_text.pack(fill="x", padx=24, pady=(4, 12))
        cc_text.insert("1.0", "\n".join(cc_list))

        def save():
            new_to = [l.strip() for l in to_text.get("1.0", "end").splitlines() if l.strip()]
            new_cc = [l.strip() for l in cc_text.get("1.0", "end").splitlines() if l.strip()]
            try:
                sheets_client.set_recipients(new_to, new_cc)
            except Exception as e:
                messagebox.showerror("エラー", f"保存に失敗しました:\n{e}")
                return
            messagebox.showinfo("保存完了", "宛先設定を保存しました。")
            dialog.destroy()

        save_btn = PseudoButton(
            dialog, text="保存", command=save,
            bg=COLOR_BTN_PRIMARY, fg=COLOR_BTN_TEXT_LIGHT, hover_bg=COLOR_BTN_PRIMARY_HOVER
        )
        save_btn.configure(padx=20, pady=10)
        save_btn.pack(pady=10)


def main():
    root = tk.Tk()
    app = ReturnMailApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
