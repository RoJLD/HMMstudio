#!/bin/sh
set -e
cat > /usr/share/nginx/html/config.js <<EOF
window.__ACADEMY_CONFIG__ = {
  studioUrl: "${STUDIO_URL:-}",
  title: "${ACADEMY_TITLE:-HMM Academy}"
};
EOF
