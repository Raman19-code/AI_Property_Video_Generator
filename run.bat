@echo off
title AI Property Video Generator
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 goto :nopython

if exist "venv\Scripts\python.exe" goto :haveenv
echo [1/3] Creating virtual environment...
python -m venv venv
if errorlevel 1 goto :fail

:haveenv
if exist "venv\.deps_installed" goto :havedeps
echo [2/3] Installing dependencies - first run only, this takes a few minutes...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
echo done> "venv\.deps_installed"

:havedeps
if exist "%USERPROFILE%\.streamlit\credentials.toml" goto :start
mkdir "%USERPROFILE%\.streamlit" >nul 2>nul
echo [general]> "%USERPROFILE%\.streamlit\credentials.toml"
echo email = "">> "%USERPROFILE%\.streamlit\credentials.toml"

:start
echo [3/3] Starting the app. Your browser will open. Close this window to stop it.
"venv\Scripts\python.exe" -m streamlit run app.py
goto :end

:nopython
echo Python was not found. Install Python 3.10 or newer from python.org and tick "Add python.exe to PATH".
goto :end

:fail
echo.
echo Setup failed. Scroll up to read the error, then see Troubleshooting in README.md

:end
pause
