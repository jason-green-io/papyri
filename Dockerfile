FROM python:slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    cron \
    git \
    rsyslog \
  && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir tqdm nbtlib Pillow numpy

COPY . /papyri

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

ENV SCHEDULE "0 * * * *"
ENV WEBSERVER true
ENV TYPE java
