#!/bin/bash
for c in satoruemr-nouveau-1 satoruemr-couchdb-1 satoruemr-haproxy-1 satoruemr-api-1 satoruemr-sentinel-1 satoruemr-nginx-1 satoruemr-dir-cht-upgrade-service-1; do
  created=$(docker inspect "$c" --format '{{.Created}}')
  restarts=$(docker inspect "$c" --format '{{.RestartCount}}')
  started=$(docker inspect "$c" --format '{{.State.StartedAt}}')
  status=$(docker inspect "$c" --format '{{.State.Status}}')
  printf '%-45s Created: %s  Restarts: %s  Started: %s  Status: %s\n' "$c" "$created" "$restarts" "$started" "$status"
done
