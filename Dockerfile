FROM python:3.11

WORKDIR /youtube_scanner

COPY ./requirements.txt /youtube_scanner

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . /youtube_scanner