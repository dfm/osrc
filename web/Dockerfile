FROM ubuntu:precise
MAINTAINER Dan F-M

# Debian
RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y build-essential wget

# Anaconda
RUN wget --no-check-certificate https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
RUN chmod +x miniconda.sh
RUN ./miniconda.sh -b
ENV PATH=/root/miniconda3/bin:$PATH
RUN /root/miniconda3/bin/conda update --yes conda

# Python packages
RUN /root/miniconda3/bin/conda install --yes flask sqlalchemy psycopg2 tornado pip
RUN /root/miniconda3/bin/pip install flask-sqlalchemy

# Project files
ADD /osrc /osrc
ADD /scripts /scripts
ADD /local.py /local.py
