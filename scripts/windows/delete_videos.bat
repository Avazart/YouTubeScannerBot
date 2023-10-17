setlocal enabledelayedexpansion
call set_env.bat
echo %PSQL_PATH%
%PSQL_PATH% -f "scripts\delete_videos.sql"

endlocal
pause