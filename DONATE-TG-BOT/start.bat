@echo off
chcp 65001 >nul
title Telegram Tips Bot

echo ============================================
echo   Запуск бота чаевых...
echo ============================================
echo.

set PY=
where python >nul 2>nul && set PY=python
if "%PY%"=="" (
    where py >nul 2>nul && set PY=py
)
if "%PY%"=="" (
    echo [ОШИБКА] Python не найден.
    pause
    exit /b 1
)

echo [OK] Python: %PY%
%PY% --version
echo.

REM ===== ПУТЬ К bot.py =====
set "BOT_PATH=C:\Users\wikot\OneDrive\Desktop\Новая папка (2)\bot.py"

if not exist "%BOT_PATH%" (
    echo [ОШИБКА] Файл не найден:
    echo %BOT_PATH%
    pause
    exit /b 1
)

echo [OK] bot.py найден
echo.
echo Запускаю бота...
echo.
%PY% "%BOT_PATH%"

echo.
echo ============================================
echo   Бот остановлен. Код выхода: %errorlevel%
echo ============================================
pause