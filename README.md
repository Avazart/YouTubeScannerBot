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

```
export DEBUG=on
export WITHOUT_SENDING=off
export APP_DATA="../app_data/release"
export LOG_DIR="/home/app_data/release/logs"
export BOT_TOKEN="5670291437:AbGk1Zu_fghjkRBYDZXgp6qwFX6d0Z9egigz"
export BOT_ADMIN_IDS=1361728070,1361728070
export CRON_SCHEDULE="55 8,11,13,17,19,20 * * *"
export SEND_DELAY=300
export REDIS_URL=redis://redis
export REDIS_QUEUE=youtube_scanner:queue
export POSTGRES_USER=postgres_user
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=postgres_db
export POSTGRES_PORT=5432
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@database:${POSTGRES_PORT}/${POSTGRES_DB}"
```
###### Run bot

python -m app

