#!/bin/sh
# Usage: ./make_map SERVER_ENDPOINT TOKEN PMR_MANIFEST_URL

curl -H "Content-Type: application/json" -X POST \
     -H "Authorization: Bearer $2" \
     -d '{"source":"'$3'"}' \
     $1/make/map

echo 'curl -H "Authorization: Bearer '$2'" '$1'/make/log/PID'
