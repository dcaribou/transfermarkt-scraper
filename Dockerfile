FROM python:3.11

WORKDIR /app

RUN apt-get update && \
    apt-get -y install gcc python3-dev

COPY pyproject.toml /app
COPY tfmkt tfmkt
COPY scrapy.cfg .

ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

RUN /bin/bash -c "poetry shell"
