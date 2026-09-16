#!/bin/bash
set -e
SRC=/mnt/c/Projects/EMRCHT/cht-core/api/build/static/webapp
DEST=satoruemr-api-1:/service/api/build/static/webapp

for f in main.js runtime.js polyfills.js scripts.js styles.css index.html; do
  docker cp "$SRC/$f" "$DEST/$f"
  echo "Copied: $f"
done

docker restart satoruemr-api-1
echo "API container restarted!"
