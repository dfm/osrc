FROM debian:wheezy

MAINTAINER John Foster &lt;johntfosterjr@gmail.com&gt;

ENV HOME /root

RUN apt-get update
RUN apt-get -yq install gcc \
                        build-essential \
                        wget \
                        bzip2 \
                        tar \
                        libghc6-zlib-dev

#Build HDF5
RUN wget http://www.hdfgroup.org/ftp/HDF5/current/src/hdf5-1.8.14.tar.bz2; \
    tar xjvf hdf5-1.8.14.tar.bz2; \
    cd hdf5-1.8.14; \
    ./configure --prefix=/usr/local/hdf5; \
    make && make install; \
    cd ..; \
    rm -rf /hdf5-1.8.14 /hdf5-1.8.14.tar.bz2 


sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key 19274DEF
sudo echo "deb http://ppa.launchpad.net/v-launchpad-jochen-sprickerhof-de/pcl/ubuntu maverick main" >> /etc/apt/sources.list
sudo apt-get update
sudo apt-get install libboost-all-dev libeigen3-dev libflann-dev libvtk5-dev libqhull-dev

#Add redis
RUN         apt-get update && apt-get install -y redis-server

# Add osrc
RUN         apt-get -yq install git && \
            git clone https://github.com/wm/osrc.git && \
            cd osrc

#Add python
RUN         apt-get install -y python python-dev python-pip

RUN         cd osrc && \
            pip install -r requirements.txt
