#!/usr/bin/env bash
set -eu
: "${MANIFEST_ROOT:?}" "${MANIFEST_OUT:?}" "${AGE_ENGINE:?}" "${MANIFEST_LANE:?}"
mkdir -p "$MANIFEST_OUT/tmp" "$MANIFEST_OUT/taskset"
exec "$AGE_ENGINE" run --rm --network none --memory 12g --pids-limit 2048 \
  --volume "$MANIFEST_LANE:$MANIFEST_LANE" \
  --volume "$MANIFEST_OUT/taskset:/work/notes/s263-evidence" \
  --workdir "$MANIFEST_ROOT" \
  --env "DENWARD_WORKSPACE=$MANIFEST_OUT/work" --env "TMPDIR=$MANIFEST_OUT/tmp" \
  --env "MANIFEST_ROOT=$MANIFEST_ROOT" --env CARGO_BUILD_JOBS=2 --env RAYON_NUM_THREADS=2 \
  --env PATH=/opt/s263-rust/bin:/usr/local/bin:/usr/bin:/bin \
  localhost/r41-toolchain:1 bash -c 'taskset -c 6-11 python3 -I -c '\''import os,subprocess; a=sorted(os.sched_getaffinity(0)); print("AFFINITY actual="+str(a),flush=True); assert set(a).issubset(set(range(6,12))) and len(a)>0; subprocess.run(["python3","-I",os.environ["MANIFEST_ROOT"]+"/tools/gate.py","--suite","native"],check=True)'\''; exit $?'
