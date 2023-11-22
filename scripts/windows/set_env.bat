@echo off
cd ../..

set ENV_FILE=.env.dev

for /f "tokens=1,* delims==" %%a in ('python scripts\get_ext_env.py %ENV_FILE%') do (
    set %%a=%%b
    echo "%%a=%%b"
)
