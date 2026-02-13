FROM python:3.12

WORKDIR /app

COPY pyproject.toml /app
COPY tfmkt tfmkt

ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

RUN /bin/bash -c "poetry shell"
