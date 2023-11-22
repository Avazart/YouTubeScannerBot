@echo off
call set_env.bat

echo.
echo %ALEMBIC_PATH%
echo.

echo on
%ALEMBIC_PATH% upgrade head

pause