### This bot periodically scans YouTube channels for new videos and sends links to them on Telegram

#### Download source

``` git clone https://github.com/Avazart/YouTubeScannerBot.git ```

#### Register your user bot in telegram

For get your own bot token key use https://t.me/BotFather

#### Install python

https://www.python.org/downloads/

#### Install python libraries

``` pip install -r requirements.txt  ```

#### Run

###### Set environment

export TOKEN="5640591437:AAGk1fu_UlPwRhfDZXgp613FX5d56Z9eVigh"
export BOT_ADMIN_IDS=13616534099;13616534066
export WORK_DIR="."
export DATABASE_URL="sqlite+aiosqlite:///database.sqlite"
export DEBUG=on
export WITHOUT_SENDING=off

###### Run bot

python main.py

