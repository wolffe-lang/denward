#!/usr/bin/env bash
set -eu
: "${AGE_ENGINE:?}"
exec "$AGE_ENGINE" "$@"
