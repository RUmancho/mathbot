@echo off

:: cd /d "C:\path\to\your\repo"
start "" "cmd.exe" /k "autosaver.bat"
git add .
set /p commit_message="Введите сообщение коммита: "
git commit -m "%commit_message%"
git push

pause