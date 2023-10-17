@echo off
setlocal enabledelayedexpansion
call set_env.bat

echo %ALEMBIC_PATH%
%ALEMBIC_PATH% upgrade head

endlocal
pause