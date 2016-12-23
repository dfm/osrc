FROM python:3.4

RUN set -ex \
    && apt-get update \
    && apt-get install -y libpq-dev

RUN mkdir -p /osrc
WORKDIR /osrc
ADD . /osrc
RUN pip install -r requirements.txt
