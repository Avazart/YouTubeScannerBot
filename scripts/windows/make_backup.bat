@echo off
call set_env.bat

echo.
echo PG_DUMP_PATH: "%PG_DUMP_PATH%"
echo NEW_BACKUP_PATH: "%NEW_BACKUP_PATH%"
echo. 

@echo on
"%PG_DUMP_PATH%" --schema=public --format=p --inserts --file=%NEW_BACKUP_PATH%

pause