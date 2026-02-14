FROM python:3.12

WORKDIR /app

COPY pyproject.toml /app
COPY tfmkt tfmkt

ENV PYTHONPATH=/app

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --without dev
