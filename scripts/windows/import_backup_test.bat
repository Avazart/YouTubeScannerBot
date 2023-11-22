@echo off
call set_env.bat


echo.
echo LAST_BACKUP_PATH: "%LAST_BACKUP_PATH%"
echo.

echo on
"%PSQL_PATH%" -f "scripts\drop_schema.sql"
"%PSQL_PATH%" -f %LAST_BACKUP_PATH%
rem "%PSQL_PATH%" -f "scripts\drop_destinations.sql"
rem "%PSQL_PATH%" -f "scripts\make_dev_db.sql"

@echo off
echo.
echo LAST_BACKUP_PATH: "%LAST_BACKUP_PATH%"
echo.

pause