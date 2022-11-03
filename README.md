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

``` python -O main.py  --api_id 214092721 --api_hash "1aa3321f398b7fad642a89d1fdac0f19" ```

##### Run with all options
```
python -O main.py  
--api_id 214092721 
--api_hash "1aa3321f398b7fad642a89d1fdac0f19"
--workdir "user_data"
--name "notifier"
run
--update_interval = 1200
--request_delay 1
--send_delay 300
--error_delay 65
--message_delay  1
--attempt_count  3
--last_days 3
```
##### Import forwarding from csv file

``` python main.py  --api_id 214092721 --api_hash "1aa3321f398b7fad642a89d1fdac0f19" import "data_example.csv" ```

##### Recreate database

``` python main.py  --api_id 214092721 --api_hash "1aa3321f398b7fad642a89d1fdac0f19" recreate_db ```
