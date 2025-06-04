#!/bin/bash

WEBHOOK_URL="https://hooks.slack.com/services/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"
MESSAGE="$1"

curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"${MESSAGE}\"}" \
  "${WEBHOOK_URL}"