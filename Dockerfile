FROM ubuntu:18.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y && \
    apt-get install -y build-essential \
      gfortran \
      git \
      libadns1-dev \
      libatlas-base-dev \
      libblas-dev \
      libcurl4-gnutls-dev \
      libevent-dev \
      libfreetype6-dev \
      liblapack-dev \
      libmemcached-dev \
      libmysqlclient-dev \
      libpcre3 \
      libpcre3-dev \
      libpng-dev \
      libpq-dev \
      libsqlite3-dev \
      libssl-dev \
      libxml2 \
      libxml2-dev \
      libxslt1-dev \
      libxslt1.1 \
      python-dev \
      python-pil \
      python-libxml2 \
      python-pip \
      python-virtualenv \
      sqlite3 \
      zlib1g-dev \
      curl && \
    apt-get autoremove && \
    apt-get clean

COPY . /app
WORKDIR /app

RUN virtualenv env
ENV VIRTUAL_ENV=/opt/macula/env
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install contextlib2 && \
    pip install -r requirements.txt

EXPOSE 80

ENTRYPOINT ["/app/deploy-scripts/load_ssm_wrapper"]
