from flask import Flask, render_template, request, jsonify
import os
import sys
import time
import logging
import subprocess
import zipfile
import shutil
import json
import requests
import webbrowser
from threading import Thread
from bs4 import BeautifulSoup  # HTMLの操作に使用
import pythoncom
from win32com.client import Dispatch
from win10toast_click import ToastNotifier

app = Flask(__name__)

# コンソールにも出力するハンドラを追加
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger()
logger.addHandler(console_handler)


def show_config_window(server_dll, web_dll, default_server_link, default_web_link):
    import tkinter as tk
    from tkinter import ttk
    import os
    import subprocess

    # アイコンのパス設定
    icon_path = os.path.join(os.path.dirname(__file__), "image", "icon.ico")
    if not os.path.exists(icon_path):
        print("Icon file not found:", icon_path)

    root = tk.Tk()
    root.title("システムエラー")
    root.geometry("300x300")
    root.configure(bg="navy")
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print("root.iconbitmap() の設定でエラーが発生しました:", e)
        # 例外内容を表示して、失敗しても処理を継続

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TLabel", background="navy", foreground="white", font=("Segoe UI", 12))
    style.configure("TButton", background="navy", foreground="white", font=("Segoe UI", 12))
    style.configure("TEntry", fieldbackground="white", foreground="black", font=("Segoe UI", 12))
    
    # 以下読み込み＆ウィジェット生成処理
    try:
        with open(server_dll, "r", encoding="utf-8") as f:
            server_link = f.read().strip()
    except:
        server_link = default_server_link
    try:
        with open(web_dll, "r", encoding="utf-8") as f:
            web_link = f.read().strip()
    except:
        web_link = default_web_link

    ttk.Label(root, text="Update Server URL:").pack(pady=5)
    server_entry = ttk.Entry(root, width=40)
    server_entry.pack(pady=5)
    server_entry.insert(0, server_link)
    
    ttk.Label(root, text="Web Server URL:").pack(pady=5)
    web_entry = ttk.Entry(root, width=40)
    web_entry.pack(pady=5)
    web_entry.insert(0, web_link)
    
    def on_ok():
        with open(server_dll, "w", encoding="utf-8") as f:
            f.write(server_entry.get().strip())
        with open(web_dll, "w", encoding="utf-8") as f:
            f.write(web_entry.get().strip())

        try:
            
            toaster = ToastNotifier()
            def open_folder_callback():
                folder = os.path.abspath(os.path.dirname(__file__))
                subprocess.Popen(["explorer", folder])
            toaster.show_toast(
                "サーバー更新",
                "接続サーバーを更新しました。もう一度起動してください。",
                icon_path=icon_path,
                duration=10,
                threaded=True,
                callback_on_click=open_folder_callback
            )
        except Exception as ex:
            print("プッシュ通知の設定でエラー:", ex)
        root.destroy()
    
    ttk.Button(root, text="OK", command=on_ok).pack(pady=20)
    
    root.mainloop()



def download_and_prepare_html():
    # web.dll から URL を取得。存在しなければデフォルトリンクで作成する。
    web_dll_path = os.path.join(os.path.dirname(__file__), "web.dll")
    if not os.path.exists(web_dll_path):
        default_link = "http://utooo.s322.xrea.com/installer/index.html"
        with open(web_dll_path, "w", encoding="utf-8") as f:
            f.write(default_link)
    with open(web_dll_path, "r", encoding="utf-8") as f:
         url = f.read().strip()
    
    templates_folder = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_folder, exist_ok=True)
    html_file_path = os.path.join(templates_folder, 'index.html')

    try:
        response = requests.get(url)
        response.encoding = 'utf-8'  # エンコーディングをUTF-8に設定

        # BeautifulSoupを使用してHTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')

        # 特定の<script>タグを削除
        for tag in soup.find_all('script', src="//cache1.value-domain.com/xrea_header.js"):
            tag.decompose()

        # 修正後のHTMLを保存
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        logger.info("HTMLファイルをダウンロードして保存しました。")
    except Exception as e:
        logger.exception("HTMLのダウンロードまたは処理中にエラーが発生しました。")
        sys.exit(1)

@app.route('/')
def index():
    """ダウンロードしたHTMLを表示"""
    desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    target_folder_path = os.path.join(desktop_path, "空想詩低")
    update_available = os.path.exists(target_folder_path)
    return render_template('index.html', update_available=update_available)

# グローバル変数; サーバー起動時に初期化
last_ping = time.time()

@app.route('/keep_alive', methods=['POST'])
def keep_alive():
    """クライアントからの接続維持確認"""
    global last_ping
    last_ping = time.time()
    logger.debug("クライアントから接続確認を受信しました。")
    return jsonify({"status": "alive"})

def monitor_keep_alive():
    """定期的にkeep_alive信号を監視し、5秒以上途絶えた場合にサーバーを終了する"""
    while True:
        time_since_last = time.time() - last_ping
        if time_since_last > 20:
            logger.info("5秒以上keep_aliveが受信されなかったため、サーバーを終了します。")
            os._exit(0)
        time.sleep(1)

@app.route('/tab_closed', methods=['POST'])
def tab_closed():
    """タブが閉じられた通知を受け取ったらサーバーを終了する"""
    logger.info("タブが閉じられた通知を受信しました。サーバーを終了します。")
    os._exit(0)
    return "", 200




def find_file_in_paths(filename, paths):
    """指定されたパスリストからファイルを検索して見つかった最初のパスを返す"""
    while True:
        for path in paths:
            for root, _, files in os.walk(path):
                if filename in files:
                    return os.path.join(root, filename)
        logger.info("ファイルが見つかるのを待っています...")
        time.sleep(5)  # 5秒待機して再試行

@app.route('/install', methods=['POST'])
def install():
    """
    指定URLを新しいタブで開き、ZIPファイルを手動でダウンロード。
    ダウンロードフォルダーまたはデスクトップからファイルを検出して展開する。
    """
    try:
        # install.batの実行
        logger.info("install.batを実行して依存関係をインストールします。")
        bat_file_path = os.path.join(os.path.dirname(__file__), "install.bat")
        log_file_path = os.path.join(os.path.dirname(__file__), "install.log")

        with open(log_file_path, 'w', encoding='utf-8') as log_file:
            result = subprocess.run(bat_file_path, shell=True, stdout=log_file, stderr=log_file, text=True)
        
        if result.returncode != 0:
            logger.error(f"install.batの実行に失敗しました。詳細はinstall.logを確認してください。")
            return jsonify({"status": "error", "message": "install.batの実行に失敗しました。"})

        logger.info("install.batの実行が完了しました。")

        # server.dllからupdate.JSONのURLを取得
        server_dll = os.path.join(os.path.dirname(__file__), "server.dll")
        with open(server_dll, "r", encoding="utf-8") as f:
            update_json_url = f.read().strip()

        # update.JSONからダウンロードリンクを取得
        response = requests.get(update_json_url)
        if response.status_code == 200:
            update_data = response.json()
            download_url = update_data.get("ダウンロードリンク")
            if not download_url:
                logger.warning("update.JSONにダウンロードリンクが指定されていません。デフォルトリンクを使用します。")
                download_url = "https://drive.google.com/uc?export=download&id=1gfMITjF9jInXoK2L9f7u-EkOTLNlVcL8"
        else:
            logger.warning("update.JSONの取得に失敗しました。デフォルトリンクを使用します。")
            download_url = "https://drive.google.com/uc?export=download&id=1gfMITjF9jInXoK2L9f7u-EkOTLNlVcL8"

        logger.info(f"新しいタブでダウンロードページを開きます: {download_url}")
        webbrowser.open_new(download_url)

        # デスクトップ上に既存のフォルダーがある場合、インストールをスキップ
        desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        target_folder_name = "空想詩低"
        target_folder_path = os.path.join(desktop_path, target_folder_name)

        if os.path.exists(target_folder_path):
            logger.info(f"既存のフォルダーが見つかりました: {target_folder_path}。インストールをスキップします。")
            return jsonify({"status": "skipped", "message": "既存のフォルダーがあるためインストールをスキップしました。"})

        # ファイル検索
        logger.info("ダウンロードフォルダーとデスクトップでファイルを検索しています...")
        downloads_path = os.path.join(os.environ['USERPROFILE'], 'Downloads')
        target_filename = "空想詩低.zip"
        
        zip_file_path = find_file_in_paths(target_filename, [downloads_path, desktop_path])

        if not zip_file_path:
            logger.error("ファイルが見つかりませんでした。手動でダウンロードを確認してください。")
            return jsonify({"status": "error", "message": "ファイルが見つかりませんでした。"})

        logger.info(f"ZIPファイルを検出しました: {zip_file_path}。展開を開始いたします。")

        # ZIPファイルの解凍
        logger.info("ZIPファイルを解凍中...")
        extract_path = os.path.join(os.path.dirname(__file__), "extracted")
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        logger.info("解凍完了。")

        # 展開したフォルダーをデスクトップに移動
        extracted_items = os.listdir(extract_path)
        if len(extracted_items) != 1:
            logger.error("解凍したファイル構造が予期したものではありません。")
            return jsonify({"status": "error", "message": "解凍したファイル構造が予期したものではありません。"})

        extracted_folder_path = os.path.join(extract_path, extracted_items[0])
        os.rename(extracted_folder_path, target_folder_path)
        logger.info(f"フォルダーをデスクトップに移動して名前を変更: {target_folder_path}")

        # ZIPファイルを削除
        os.remove(zip_file_path)
        logger.info(f"ZIPファイルを削除しました: {zip_file_path}")

        return jsonify({"status": "success", "message": "インストール完了しました。"})

    except Exception as e:
        logger.exception("インストール中にエラーが発生しました。")
        return jsonify({"status": "error", "message": f"例外が発生しました: {str(e)}"})

@app.route('/get_update_link', methods=['GET'])
def get_update_link():
    try:
        with open(os.path.join(os.path.dirname(__file__), "server.dll"), 'r', encoding='utf-8') as f:
            link = f.read().strip()
        return jsonify({"status": "success", "update_link": link})
    except Exception as e:
        logger.exception("更新リンクの取得中にエラーが発生しました。")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/set_update_link', methods=['POST'])
def set_update_link():
    try:
        new_link = request.form.get("update_link")
        if not new_link:
            return jsonify({"status": "error", "message": "リンクが提供されませんでした。"}), 400
        with open(os.path.join(os.path.dirname(__file__), "server.dll"), 'w', encoding='utf-8') as f:
            f.write(new_link)
        logger.info(f"更新リンクを更新しました: {new_link}")
        return jsonify({"status": "success", "message": "更新リンクを保存しました。"})
    except Exception as e:
        logger.exception("更新リンクの保存中にエラーが発生しました。")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update', methods=['POST'])
def update():
    """
    update.JSONから最新のアップデート情報を取得し、
    指定の操作を実行後、同じディレクトリーにversion.txtへ更新バージョンを追記します。
    """
    try:
        # サーバー起動時にブラウザを開かないようにフラグを設定
        os.environ["NO_AUTO_BROWSER"] = "1"

        with open(os.path.join(os.path.dirname(__file__), "server.dll"), 'r', encoding='utf-8') as f:
            update_url = f.read().strip()
        response = requests.get(update_url)
        if response.status_code != 200:
            return jsonify({"status": "error", "message": "アップデート情報を取得できませんでした。"}), 500

        update_info = response.json()
        updates = update_info.get("updates", [])
        version_file = os.path.join(os.path.dirname(__file__), "version.txt")

        # 既存のバージョンを読み込む
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as vf:
                existing_versions = vf.read().splitlines()
        else:
            existing_versions = []

        desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        updated_versions = []

        # バージョンを逆順に処理
        for update in reversed(updates):
            new_version = update.get("version", "unknown")

            # 新しいバージョンが既に存在する場合はスキップ
            if new_version in existing_versions:
                logger.info(f"バージョン {new_version} は既にアップデートされています。")
                continue

            logger.info(f"バージョン {new_version} のアップデートを開始します。")

            # ファイル追加
            file_addition = update.get("ファイル追加")
            if file_addition:
                if isinstance(file_addition, dict):
                    additions = file_addition.items()
                elif isinstance(file_addition, list) and len(file_addition) == 2:
                    additions = [(file_addition[0], file_addition[1])]
                else:
                    additions = []
                    logger.warning("ファイル追加の形式が不正です。")
                
                for dest_path, file_url in additions:
                    full_dest = os.path.normpath(os.path.join(desktop_path, dest_path))
                    if os.path.isdir(full_dest):
                        full_dest = os.path.join(full_dest, os.path.basename(file_url))
                    os.makedirs(os.path.dirname(full_dest), exist_ok=True)
                    r = requests.get(file_url)
                    if r.status_code == 200:
                        with open(full_dest, 'wb') as f:
                            f.write(r.content)
                        logger.info(f"ファイル追加: {full_dest}")
                    else:
                        logger.warning(f"ファイル追加失敗: {dest_path}")
                time.sleep(2)  # 2秒待機

            # ファイル・フォルダー削除
            deletions = update.get("ファイルフォルダー削除", [])
            if isinstance(deletions, str):
                deletions = [deletions]
            for target in deletions:
                full_target = os.path.normpath(os.path.join(desktop_path, target))
                if os.path.exists(full_target):
                    if os.path.isfile(full_target):
                        os.remove(full_target)
                        logger.info(f"削除: {full_target}")
                    elif os.path.isdir(full_target):
                        shutil.rmtree(full_target)
                        logger.info(f"削除: {full_target}")
                else:
                    logger.info(f"削除対象が存在しません: {full_target}")
            time.sleep(2)  # 2秒待機

            # フォルダー作成
            folder_creation = update.get("フォルダー作成")
            if folder_creation:
                if isinstance(folder_creation, dict):
                    creations = folder_creation.items()
                elif isinstance(folder_creation, list) and len(folder_creation) == 2:
                    creations = [(folder_creation[0], folder_creation[1])]
                else:
                    creations = []
                    logger.warning("フォルダー作成の形式が不正です。")
                for dest_path, folder_name in creations:
                    if os.path.splitext(folder_name)[1]:
                        logger.warning(f"フォルダー作成対象として不適切な名前を検出しました（ファイル名と思われるためスキップ）: {folder_name}")
                        continue
                    full_dest_parent = os.path.normpath(os.path.join(desktop_path, dest_path))
                    os.makedirs(full_dest_parent, exist_ok=True)
                    full_dest = os.path.join(full_dest_parent, folder_name)
                    os.makedirs(full_dest, exist_ok=True)
                    logger.info(f"フォルダー作成: {full_dest}")
                time.sleep(2)  # 2秒待機

            # ファイル作成
            file_creation = update.get("ファイル作成")
            if file_creation:
                if isinstance(file_creation, dict):
                    creations = file_creation.items()
                elif isinstance(file_creation, list) and len(file_creation) == 2:
                    creations = [(file_creation[0], file_creation[1])]
                else:
                    creations = []
                    logger.warning("ファイル作成の形式が不正です。")
                for dest_path, file_name in creations:
                    folder = os.path.normpath(os.path.join(desktop_path, dest_path))
                    os.makedirs(folder, exist_ok=True)
                    full_file = os.path.join(folder, file_name)
                    with open(full_file, 'a', encoding='utf-8') as f:
                        f.write("")
                    logger.info(f"ファイル作成: {full_file}")
                time.sleep(2)  # 2秒待機

            # 削除＆追加：指定パスのファイル・フォルダーを削除してから、
            # 指定のリンクのファイルをその場所に配置する
            del_and_add = update.get("削除＆追加")
            if del_and_add:
                if isinstance(del_and_add, dict):
                    for dest_path, file_url in del_and_add.items():
                        full_dest = os.path.normpath(os.path.join(desktop_path, dest_path))
                        # 既存のファイルまたはフォルダーを削除
                        if os.path.exists(full_dest):
                            if os.path.isfile(full_dest):
                                os.remove(full_dest)
                                logger.info(f"既存のファイルを削除しました: {full_dest}")
                            elif os.path.isdir(full_dest):
                                shutil.rmtree(full_dest)
                                logger.info(f"既存のフォルダーを削除しました: {full_dest}")
                        # 指定リンクのファイルをダウンロードして配置
                        os.makedirs(os.path.dirname(full_dest), exist_ok=True)
                        r = requests.get(file_url)
                        if r.status_code == 200:
                            with open(full_dest, 'wb') as f:
                                f.write(r.content)
                            logger.info(f"削除＆追加: {full_dest}")
                        else:
                            logger.warning(f"削除＆追加失敗: {dest_path}")
                else:
                    logger.warning("削除＆追加の形式が不正です。")
                time.sleep(2)  # 2秒待機

            # Pythonライブラリーのインストール
            library_install = update.get("ライブラリーインストール")
            if library_install:
                if isinstance(library_install, list):
                    for lib in library_install:
                        logger.info(f"ライブラリ {lib} のインストールを開始します。")
                        result = subprocess.run(
                            [sys.executable, "-m", "pip", "install", lib],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        if result.returncode == 0:
                            logger.info(f"ライブラリ {lib} のインストールに成功しました。")
                        else:
                            logger.error(f"ライブラリ {lib} のインストールに失敗しました。エラー: {result.stderr}")
                else:
                    logger.warning("ライブラリーインストールの形式が不正です。")
                time.sleep(2)  # 2秒待機

            # version.txtへの追記
            with open(version_file, 'a', encoding='utf-8') as vf:
                vf.write(f"{new_version}\n")
            logger.info(f"version.txtにアップデートバージョン {new_version} を追記しました。")
            updated_versions.append(new_version)

        return jsonify({
            "status": "success",
            "message": "アップデート完了しました。",
            "updated_versions": updated_versions,
            "existing_versions": existing_versions
        })

    except Exception as e:
        logger.exception("アップデート中にエラーが発生しました。")
        return jsonify({"status": "error", "message": f"例外が発生しました: {str(e)}"}), 500

@app.route('/create_shortcut', methods=['POST'])
def create_shortcut():
    """デスクトップ上に実行ファイルのショートカットを作成"""
    try:
        desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        target_path = os.path.join(desktop_path, '空想詩低', '空想詩低.exe')
        shortcut_path = os.path.join(desktop_path, '空想詩低.lnk')

        if not os.path.exists(target_path):
            logging.error(f"ターゲットファイルが見つかりません: {target_path}")
            return jsonify({"status": "error", "message": f"ターゲットファイルが見つかりません: {target_path}"})

        pythoncom.CoInitialize()
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.Save()

        logging.info("ショートカットを作成しました。")
        return jsonify({"status": "success", "message": "ショートカットを作成しました。"})

    except Exception as e:
        logging.exception("ショートカット作成中にエラーが発生しました。")
        return jsonify({"status": "error", "message": f"例外が発生しました: {str(e)}"})



def stop_server():
    """サーバーを停止"""
    logger.debug("サーバーを停止します。")
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('サーバーの停止処理がサポートされていません。')
    func()

# モジュールレベルでグローバル変数を宣言
browser_opened = False

# モジュールレベルでグローバル変数を宣言
browser_opened = False

if __name__ == "__main__":
    # server.dll が存在しなければ、デフォルトリンクを書き込む
    server_dll = os.path.join(os.path.dirname(__file__), "server.dll")
    default_update_link = "http://utooo.s322.xrea.com/installer/update.JSON"
    if not os.path.exists(server_dll):
        with open(server_dll, "w", encoding="utf-8") as f:
            f.write(default_update_link)
        logger.info(f"server.dllが見つからなかったため、デフォルトリンクを設定しました: {default_update_link}")
    
    # web.dll の用意（存在しなければ自動作成）
    web_dll = os.path.join(os.path.dirname(__file__), "web.dll")
    default_web_link = "http://utooo.s322.xrea.com/installer/index.html"
    if not os.path.exists(web_dll):
        with open(web_dll, "w", encoding="utf-8") as f:
            f.write(default_web_link)
    
    # web.dll に保存されたリンク先が存在するか確認（タイムアウト3秒）
    with open(web_dll, "r", encoding="utf-8") as f:
        web_link = f.read().strip()
    try:
        r = requests.get(web_link, timeout=3)
        if r.status_code != 200:
            raise Exception("存在しないサイト")
    except:
        logger.warning("web.dll に保存されたリンク先が存在しないため、設定ウィンドウを表示します。")
        default_server_link = default_update_link
        show_config_window(server_dll, web_dll, default_server_link, default_web_link)
    
    try:
        download_and_prepare_html()  # サーバー起動前にHTMLをダウンロード
        Thread(target=monitor_keep_alive, daemon=True).start()
        
        def run_server():
            app.run(debug=True, use_reloader=False)
        Thread(target=run_server).start()
        
        # 環境変数 "NO_AUTO_BROWSER" が設定されていなければ、3秒後にローカルURLを開くが、
        # 同時に開ける回数は1回までに制限する
        if not os.environ.get("NO_AUTO_BROWSER"):
            def delayed_open_browser():
                global browser_opened
                time.sleep(3)
                if not browser_opened:
                    os.startfile("http://127.0.0.1:5000")
                    browser_opened = True
            Thread(target=delayed_open_browser).start()
        
    except SystemExit as e:
        logger.debug(f"Flaskのシステム終了: {e}")
        sys.exit(0)