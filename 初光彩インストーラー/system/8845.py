import os
import subprocess

# このスクリプト自身のディレクトリを基準にする
base_dir = os.path.dirname(os.path.abspath(__file__))

# 必要なパスの設定
icon_path = os.path.join(base_dir, "image", "icon.ico")
script_path = os.path.join(base_dir, "app.py")
output_dir = os.path.join(base_dir, "..")  # 出力先ディレクトリ
batch_file = os.path.join(base_dir, "install.bat")

# 各ファイルの存在確認
if not os.path.exists(icon_path):
    print(f"Icon file not found: {icon_path}")
if not os.path.exists(script_path):
    print(f"Script file not found: {script_path}")
if not os.path.exists(batch_file):
    print(f"Batch file not found: {batch_file}")

# PyInstallerのコマンドを構築
cmd = [
    "pyinstaller",
    "--onefile",      # 単一の実行可能ファイルにする
    "--noconsole",    # コンソールウィンドウを表示しない
    f"--icon={icon_path}",        # アイコンを指定
    f"--name=初光彩",             # 実行ファイル名
    f"--distpath={output_dir}",   # 出力先ディレクトリ
    f"--add-data={batch_file};.",  # install.batを同梱（Windows環境用のセパレータはセミコロン）
    script_path    # 実行するスクリプト
]

print("PyInstallerのコマンド:")
print(" ".join(cmd))

# PyInstallerコマンドの実行
try:
    print("PyInstallerを実行中...")
    result = subprocess.run(cmd, check=True, text=True, capture_output=True, encoding='utf-8')
    print("実行結果:")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("エラーが発生しました:")
    print(e.stderr)

# 実行後の確認
print(f"出力された実行ファイルは: {output_dir} に配置されます")