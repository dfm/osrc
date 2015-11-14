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

# Project files
RUN mkdir -p /osrc
WORKDIR /osrc
ADD . /osrc

# Python packages
RUN conda install --yes --file conda.txt
RUN pip install -r requirements.txt
