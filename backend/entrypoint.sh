#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

echo "Running database migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting Gunicorn..."
exec gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000
