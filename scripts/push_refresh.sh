#!/usr/bin/env bash
# Retry publication races without repeating provider calls or forcing the branch.
set -euo pipefail
for attempt in 1 2 3 4 5; do
  git pull --rebase origin main
  if git push origin HEAD:main; then
    exit 0
  fi
  echo "Publication raced another refresh; retrying (${attempt}/5)." >&2
  sleep "$((attempt * 2))"
done
echo 'Refresh data was collected, but publication failed after five attempts.' >&2
exit 1
