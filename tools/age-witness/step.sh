#!/usr/bin/env bash
set -eu
: "${AGE_ROOT:?}" "${AGE_OUT:?}" "${AGE_REF:?}" "${AGE_CPUS:?}" "${AGE_ENGINE:?}" "${AGE_IMAGE:?}"
mkdir -p "$AGE_OUT/tmp"
exec "$AGE_ENGINE" run --rm --network none --memory 6g --pids-limit 2048 \
  --volume "$AGE_ROOT:$AGE_ROOT" --volume "$AGE_OUT:$AGE_OUT" --volume "$AGE_REF:$AGE_REF:ro" \
  --workdir "$AGE_ROOT" \
  --env "AGE_ROOT=$AGE_ROOT" --env "AGE_OUT=$AGE_OUT" --env "AGE_REF=$AGE_REF" \
  --env "AGE_CPUS=$AGE_CPUS" --env "TMPDIR=$AGE_OUT/tmp" \
  --env CARGO_BUILD_JOBS=2 --env RAYON_NUM_THREADS=2 \
  --env PATH=/opt/s263-rust/bin:/usr/local/bin:/usr/bin:/bin \
  "$AGE_IMAGE" bash -c 'taskset -c "$AGE_CPUS" bash "$AGE_ROOT/tools/age-witness/inner.sh" "$1"; exit $?' bash "$1"
