### This bot periodically scans YouTube channels for new videos and sends links to them on Telegram

#### Download source

``` git clone https://github.com/Avazart/youtube_scanner.git ```

#### Register your user bot in telegram

Get your own Telegram API key from [https://my.telegram.org/apps](https://my.telegram.org/apps).

#### Install python

https://www.python.org/downloads/

#### Install python libraries

``` pip install -r requirements.txt  ```

#### Run

##### Run bot

``` python -O main.py  --work_dir user_data --token "7881291637:AAGk1Zu_xlPwRcYDZXgg6qwFx5d0d0eViz" run ```


##### Run with all options
```
python -O main.py  
--token "7881291637:AAGk1Zu_xlPwRcYDZXgg6qwFx5d0d0eViz"
--workdir "user_data"
run
--update_interval  1200
--request_delay 1
--send_delay 300
--error_delay 65
--message_delay  1
--attempt_count  3
--last_days 3
```

##### Recreate database

``` python main.py  --workdir "user_data" recreate_db ```

##### Import data from json file

``` python main.py  --workdir "user_data" import "backup.json" ```

##### Export data from json file

``` python main.py  --workdir "user_data" export "backup.json" ```

