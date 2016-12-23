FROM python:3.4

RUN set -ex \
    && apt-get update \
    && apt-get install -y postgresql-client-common libpq-dev

RUN mkdir -p /osrc
WORKDIR /osrc
ADD requirements.txt /osrc/
RUN pip install -r requirements.txt
ADD . /osrc/
