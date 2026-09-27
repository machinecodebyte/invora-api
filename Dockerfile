FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.lock ./
RUN pip install --no-cache-dir --requirement requirements.lock

COPY app ./app

COPY alembic ./alembic
COPY alembic.ini ./

USER app

EXPOSE 8000

CMD ["python", "-m", "app.server"]
