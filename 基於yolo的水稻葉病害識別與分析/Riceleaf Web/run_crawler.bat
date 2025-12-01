@echo off
setlocal EnableExtensions

REM === 0) 切到此 bat 所在資料夾 ===
cd /d "%~dp0"

if not exist "logs" mkdir "logs"
set "SCHED_LOG=logs\scheduler.log"

echo.>> "%SCHED_LOG%"
echo ===================== >> "%SCHED_LOG%"
echo [START] %date% %time% >> "%SCHED_LOG%"
echo whoami: >> "%SCHED_LOG%"
whoami >> "%SCHED_LOG%" 2>&1
echo cwd: %cd% >> "%SCHED_LOG%"
echo PATH: >> "%SCHED_LOG%"
echo %PATH% >> "%SCHED_LOG%"

REM === 1) 指定 Python 路徑（你的 Conda venv） ===
set "PY=請輸入自己的python路徑"
if not exist "%PY%" (
  echo Python not found at: %PY% >> "%SCHED_LOG%"
  set "PY_EXIT=9009"
  goto AFTER_PY
)
echo Python path: %PY% >> "%SCHED_LOG%"
"%PY%" -V >> "%SCHED_LOG%" 2>&1
"%PY%" -c "import sys; print('Python executable:', sys.executable)" >> "%SCHED_LOG%" 2>&1

REM === 2) 指向爬蟲腳本（用絕對路徑） ===
set "DJANGO_MANAGE=%cd%\manage.py"
if not exist "%CRAWLER%" (
  echo Crawler not found: %CRAWLER% >> "%SCHED_LOG%"
  set "PY_EXIT=2"
  goto AFTER_PY
)

echo Running: "%PY%" "%DJANGO_MANAGE%" rice_crawler --pages 2 >> "%SCHED_LOG%"
"%PY%" "%DJANGO_MANAGE%" rice_crawler --pages 2 >> "%SCHED_LOG%" 2>&1
set "PY_EXIT=%ERRORLEVEL%"

:AFTER_PY
REM === 3) 檢查輸出檔 ===
set "OUT=%cd%\data\crawl_result.json"
powershell -NoProfile -Command ^
  "$p = '%OUT%';" ^
  "if (Test-Path -LiteralPath $p) {" ^
  "  $i = Get-Item -LiteralPath $p;" ^
  "  Write-Output ('[OK] Output: {0} (size={1} bytes, modified={2:yyyy-MM-dd HH:mm:ss})' -f $i.FullName, $i.Length, $i.LastWriteTime)" ^
  "} else {" ^
  "  Write-Output ('[MISS] Output not found: {0}' -f $p)" ^
  "}" >> "%SCHED_LOG%" 2>&1

REM === 4) 附帶 debug：抓最後 50 行 crawl_debug.log 方便定位 ===
powershell -NoProfile -Command ^
  "$d = 'logs/crawl_debug.log';" ^
  "if (Test-Path -LiteralPath $d) {" ^
  "  Write-Output ('[TAIL] ' + (Get-Item $d).FullName);" ^
  "  Get-Content -Tail 50 -Path $d" ^
  "} else {" ^
  "  Write-Output '[TAIL] logs/crawl_debug.log not found.'" ^
  "}" >> "%SCHED_LOG%" 2>&1

echo [END] %date% %time% (python_exit=%PY_EXIT%) >> "%SCHED_LOG%"
echo ===================== >> "%SCHED_LOG%"

endlocal & exit /b %PY_EXIT%
