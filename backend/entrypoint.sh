#!/bin/sh
set -e

python manage.py migrate --noinput

# Only ever seed local development data, and only the first time the `db`
# volume is created (schema applied, zero users yet) — never touches a
# volume that already has data, so it won't collide with real deployments.
if [ "${DJANGO_DEBUG:-false}" = "true" ]; then
    has_users=$(python manage.py shell -c "from api.models import User; print(int(User.objects.exists()))" | tail -n1)
    if [ "$has_users" = "0" ]; then
        echo "Fresh database detected — seeding sample development data..."
        python manage.py seed_dev_data
    fi
fi

exec "$@"
