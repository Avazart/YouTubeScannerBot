@echo off
cd ../..

set ENV_FILE=.env.dev

set PSQL_PATH="C:\Program Files\PostgreSQL\14\bin\psql.exe"
set ALEMBIC_PATH="venv\Scripts\alembic.exe"

for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "%%a=%%b"
    echo "%%a=%%b"
)

set BACKUP_DIR=%APP_DATA%\backups

echo "BACKUP_DIR=%BACKUP_DIR%"