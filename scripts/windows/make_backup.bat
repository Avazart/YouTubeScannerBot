@echo off
call set_env.bat


for /f %%i in ('python3.11 scripts\backup.py --dir %BACKUP_DIR% new') do (
  set "NEW_BACKUP_PATH=%%i"
)
echo NEW_BACKUP_PATH: "%NEW_BACKUP_PATH%"

%PG_DUMP_PATH% --schema=public --format=p --inserts --file=%NEW_BACKUP_PATH%
pause