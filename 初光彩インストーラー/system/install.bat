@echo off
chcp 65001 > NUL
set LOGFILE=install.log

REM ログファイルに日時を記録
echo [%date% %time%] Starting installation... >> %LOGFILE%

REM pipのアップデート
python.exe -m pip install --upgrade pip >> %LOGFILE% 2>&1

REM 必要なPythonモジュールをインストール
pip install pygame >> %LOGFILE% 2>&1
pip install opencv-python >> %LOGFILE% 2>&1
pip install numpy >> %LOGFILE% 2>&1
pip install tk >> %LOGFILE% 2>&1
pip install Flask >> %LOGFILE% 2>&1
pip install requests >> %LOGFILE% 2>&1
pip install beautifulsoup4 >> %LOGFILE% 2>&1
pip install pywin32 >> %LOGFILE% 2>&1
pip install win10toast_click >> %LOGFILE% 2>&1

REM インストール完了メッセージをログに記録
echo [%date% %time%] Dependencies installed successfully! >> %LOGFILE%
