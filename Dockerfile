FROM ubuntu:trusty
MAINTAINER Dan F-M

# Debian
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y build-essential wget

# Anaconda
RUN wget --no-check-certificate https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
    chmod +x miniconda.sh && \
    ./miniconda.sh -b
ENV PATH=/root/miniconda3/bin:$PATH
RUN conda update --yes conda

# Python packages
RUN conda install --yes \
    flask==0.10.1 \
    pip==7.1.2 \
    psycopg2==2.6.1 \
    sqlalchemy==1.0.9 \
    tornado==4.2.1
RUN pip install \
    flask-sqlalchemy==2.1

# Project files
RUN mkdir -p /osrc
WORKDIR /osrc
ADD . /osrc
