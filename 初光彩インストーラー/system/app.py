from flask import Flask, render_template, request, jsonify
import os
import subprocess
from threading import Thread
import webbrowser
import sys
import requests
import zipfile
import logging
from bs4 import BeautifulSoup  # HTMLの操作に使用
import pythoncom
from win32com.client import Dispatch
import time


app = Flask(__name__)

# コンソールにも出力するハンドラを追加
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger()
logger.addHandler(console_handler)

def download_and_prepare_html():
    """
    サーバー起動時に指定されたURLからHTMLをダウンロードし、
    指定のスクリプトを削除して保存。既存ファイルがある場合は上書きする。
    """
    url = "http://utooo.s322.xrea.com/index.html"
    templates_folder = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_folder, exist_ok=True)
    html_file_path = os.path.join(templates_folder, 'index.html')

    try:
        logger.info(f"HTMLをダウンロードしています: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # 不要なスクリプトタグを削除
            for script in soup.find_all("script", {"src": "//cache1.value-domain.com/xrea_header.js"}):
                script.decompose()

            # ファイルが既に存在する場合、上書き
            if os.path.exists(html_file_path):
                logger.info(f"既存のHTMLファイルを置き換えます: {html_file_path}")

            # 処理済みHTMLを保存
            with open(html_file_path, 'w', encoding='utf-8') as file:
                file.write(str(soup))
            logger.info(f"HTMLを保存しました: {html_file_path}")
        else:
            logger.error(f"HTMLのダウンロードに失敗しました: ステータスコード {response.status_code}")
            sys.exit(1)
    except Exception as e:
        logger.exception("HTMLのダウンロードまたは処理中にエラーが発生しました。")
        sys.exit(1)


@app.route('/')
def index():
    """ダウンロードしたHTMLを表示"""
    return render_template('index.html')


@app.route('/keep_alive', methods=['POST'])
def keep_alive():
    """クライアントからの接続維持確認"""
    logger.debug("クライアントから接続確認を受信しました。")
    return jsonify({"status": "alive"})


@app.route('/tab_closed', methods=['POST'])
def tab_closed():
    """タブが閉じられた通知を受け取る"""
    logger.debug("タブが閉じられました。サーバーを停止します。")
    try:
        stop_server()
    except RuntimeError as e:
        logger.error(f"サーバー停止エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})
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
        # ダウンロードURLを新しいタブで開く
        download_url = "https://drive.google.com/uc?export=download&id=1gfMITjF9jInXoK2L9f7u-EkOTLNlVcL8"
        logger.info("新しいタブでダウンロードページを開きます。")
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



def open_browser():
    """サーバー起動後にブラウザでページを開く"""
    webbrowser.open_new('http://127.0.0.1:5000')


def stop_server():
    """サーバーを停止"""
    logger.debug("サーバーを停止します。")
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('サーバーの停止処理がサポートされていません。')
    func()


if __name__ == "__main__":
    try:
        download_and_prepare_html()  # サーバー起動前にHTMLをダウンロード
        Thread(target=open_browser).start()
        app.run(debug=True, use_reloader=False)
    except SystemExit as e:
        logger.debug(f"Flaskのシステム終了: {e}")
        sys.exit(0)
