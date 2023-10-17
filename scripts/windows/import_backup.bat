@echo off
call set_env.bat

for /f %%i in ('python3.11 scripts\backup.py --dir %BACKUP_DIR% last') do (
  set "LAST_BACKUP_PATH=%%i"
)

echo LAST_BACKUP_PATH: "%LAST_BACKUP_PATH%"

%PSQL_PATH% -f "scripts\drop_schema.sql"
%PSQL_PATH% -f %LAST_BACKUP_PATH%
%PSQL_PATH% -f "scripts\drop_destinations.sql"
%PSQL_PATH% -f "scripts\make_dev_db.sql"

echo LAST_BACKUP_PATH: "%LAST_BACKUP_PATH%"

pause