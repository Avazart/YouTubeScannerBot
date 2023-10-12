@echo off
setlocal enabledelayedexpansion

set ENV_FILE=..\..\.env.dev
for /f "usebackq tokens=1,2 delims== " %%a in ("%ENV_FILE%") do (
    set "%%a=%%b"
    echo "%%a=%%b"
)

set "BACKUP_FOLDER=..\..\app_data\"
set "dt=%time%_%date%"
set "dt=!dt:.=_!"
set "dt=!dt::=_!"
set "dt=!dt:,=_!"
set "BACKUP_FILE=%BACKUP_FOLDER%backup_%dt%%.sql"


"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe" ^
--schema=public ^
--format=p ^
--inserts ^
--file=%BACKUP_FILE%

endlocal
pause