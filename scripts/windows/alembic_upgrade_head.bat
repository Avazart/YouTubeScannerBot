@echo off
setlocal enabledelayedexpansion


set ENV_FILE=..\..\.env.dev
for /f "usebackq tokens=1,2 delims== " %%a in ("%ENV_FILE%") do (
    set "%%a=%%b"
    echo "%%a=%%b"
)

cd ..\..
venv\Scripts\alembic.exe upgrade head

endlocal
pause