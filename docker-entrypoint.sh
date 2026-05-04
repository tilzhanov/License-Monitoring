#!/bin/sh
# Fix /data ownership for pre-existing volumes created before non-root migration,
# then drop privileges to the app user via gosu.
set -e

if [ "$(id -u)" = "0" ]; then
    chown -R app:app /data
    exec gosu app "$@"
fi

exec "$@"
