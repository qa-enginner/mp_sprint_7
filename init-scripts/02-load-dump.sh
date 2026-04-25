#!/bin/bash

set -e
set -u

# Wait for PostgreSQL to be ready
until pg_isready -U "$POSTGRES_USER"; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

echo "Loading database dump into movies database..."

# Load the dump into movies database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "movies" < /docker-entrypoint-initdb.d/database_dump.sql

echo "Database dump loaded successfully into movies database."