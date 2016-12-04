FROM ubuntu:trusty
MAINTAINER Dan F-M

# System requirements
RUN apt-get update -y && \
    apt-get upgrade -y
RUN apt-get install -y build-essential python3-dev python3-pip libpq-dev

# Project files
RUN mkdir -p /osrc
WORKDIR /osrc
ADD . /osrc

# Python deps
RUN pip3 install -r requirements.txt

# CMD python3
