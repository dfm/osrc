FROM python:3.4

ARG REQUIREMENTS_TXT=requirements.txt

ADD $REQUIREMENTS_TXT /tmp/requirements.txt

RUN set -ex \
    && pkgs=' \
        python-dev \
    ' \
    && apt-get update \
    && apt-get install -y \
        $pkgs libpq-dev \
    && pip3 install -r /tmp/requirements.txt \
    && apt-get purge -y --auto-remove $pkgs \
    && rm -rf /usr/src/python ~/.cache
