#!/bin/sh

# The Docker Compose worker service overrides this command and remains the only
# local RQ worker. Render opts into the embedded topology explicitly.
set -u

log() {
    printf '%s\n' "$*" >&2
}

stop_embedded_processes() {
    signal_name=$1
    trap - TERM INT
    log "Received ${signal_name}; stopping Invora API and embedded RQ worker..."
    kill -TERM "$api_pid" "$worker_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
    wait "$worker_pid" 2>/dev/null || true
    exit 0
}

case "${RUN_EMBEDDED_WORKER:-false}" in
    false)
        log "Starting Invora API..."
        exec python -m app.server
        ;;
    true)
        ;;
    *)
        log "RUN_EMBEDDED_WORKER must be true or false."
        exit 64
        ;;
esac

log "Starting embedded Invora RQ worker..."
python -m app.modules.jobs.worker &
worker_pid=$!

log "Starting Invora API..."
python -m app.server &
api_pid=$!

trap 'stop_embedded_processes TERM' TERM
trap 'stop_embedded_processes INT' INT

# POSIX sh has no portable wait-for-any-child primitive. Polling the direct
# child PIDs keeps failures visible and tears down the remaining process.
while :; do
    if ! kill -0 "$worker_pid" 2>/dev/null; then
        wait "$worker_pid"
        worker_status=$?
        log "Embedded Invora RQ worker exited with status ${worker_status}; stopping API."
        kill -TERM "$api_pid" 2>/dev/null || true
        wait "$api_pid" 2>/dev/null || true
        exit "$worker_status"
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
        wait "$api_pid"
        api_status=$?
        log "Invora API exited with status ${api_status}; stopping embedded RQ worker."
        kill -TERM "$worker_pid" 2>/dev/null || true
        wait "$worker_pid" 2>/dev/null || true
        exit "$api_status"
    fi

    sleep 1
done
