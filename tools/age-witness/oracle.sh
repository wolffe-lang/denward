#!/usr/bin/env bash
set -eu
: "${AGE_ROOT:?}" "${AGE_OUT:?}" "${AGE_REF:?}" "${AGE_KEYS:?}" "${AGE_INPUT:?}" "${AGE_ENGINE:?}" "${LIGHT_CPUS:?}" "${LIGHT_MEM:?}"
exec "$AGE_ENGINE" run --rm --network none --memory "$LIGHT_MEM" \
 --volume "$AGE_ROOT:$AGE_ROOT:ro" --volume "$AGE_REF:$AGE_REF:ro" \
 --volume "$AGE_KEYS:$AGE_KEYS:ro" --volume "$AGE_INPUT:$AGE_INPUT:ro" --volume "$AGE_OUT:$AGE_OUT" \
 --volume "${AGE_TASKSET_LOGDIR:?}:/work/notes/s263-evidence" \
 --env AGE_ROOT --env AGE_OUT --env AGE_REF --env AGE_KEYS --env AGE_INPUT --env LIGHT_CPUS \
 localhost/r41-toolchain:1 bash -c 'taskset -c "$LIGHT_CPUS" python3 -I "$AGE_ROOT/tests/age/mac-interop.py" --phase oracle --reference "$AGE_REF" --keys "$AGE_KEYS" --input "$AGE_INPUT" --output "$AGE_OUT/returned"; exit $?'
