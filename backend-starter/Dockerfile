FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}

CMD ["bash", "-lc", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn starter.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
