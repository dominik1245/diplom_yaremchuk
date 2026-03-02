@echo off
cd /d "%~dp0"
title Доступний Дім - Сервер

echo Папка проєкту: %CD%
echo.
if not exist "config\settings.py" (
    echo [Помилка] Це не папка "Доступний Дім". Запусти run.bat з папки Duplom_dominik.
    echo Очікуваний шлях: ...\Duplom_dominik
    pause
    exit /b 1
)

set PY=venv\Scripts\python.exe
if not exist "%PY%" (
    echo [Помилка] Не знайдено venv. Створюю...
    python -m venv venv
    if errorlevel 1 (
        echo Не вдалося створити venv. Встанови Python з python.org
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    "%PY%" -m pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo Застосовую міграції...
"%PY%" manage.py migrate
if errorlevel 1 (
    echo [Помилка] Міграції не застосувалися.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Сервер: http://127.0.0.1:8000/
echo   Зупинити: Ctrl+C
echo ========================================
echo.
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000/"

"%PY%" manage.py runserver 127.0.0.1:8000

echo.
echo Сервер зупинено.
pause
