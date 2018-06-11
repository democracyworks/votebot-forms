#!/bin/sh

set -euo pipefail
IFS=$'\n\t'

if [[ -n "${DATABASE_USERNAME:-}" ]]; then
  export DATABASE_URL="postgres://${DATABASE_USERNAME}:${DATABASE_PASSWORD}@localhost:5432/postgres"
fi

exec newrelic-admin run-program uwsgi uwsgi.ini
