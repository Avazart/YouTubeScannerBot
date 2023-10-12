@echo off
setlocal enabledelayedexpansion

set ENV_FILE=..\..\.env.dev
set BACKUP_FILE=..\..\app_data\backup.sql

for /f "usebackq tokens=1,2 delims== " %%a in ("%ENV_FILE%") do (
    set "%%a=%%b"
    echo "%%a=%%b"
)
"C:\Program Files\PostgreSQL\14\bin\psql.exe"  -f "..\drop_schema.sql"
"C:\Program Files\PostgreSQL\14\bin\psql.exe"  -f %BACKUP_FILE%

endlocal
pause