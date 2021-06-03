FROM python:3.9.5-slim-buster

ENV PYTHONUNBUFFERED=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_NO_CACHE_DIR=on

RUN python -mpip install poetry tox && mkdir /app

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN POETRY_VIRTUALENVS_CREATE=false poetry install --no-interaction --no-ansi

COPY app /app/app

RUN tox && rm -rf .tox

CMD [ "python", "-m", "app" ]
