#!/usr/bin/env bash
# Runs all 12 configurations x 3 repetitions. Usage: ./run_all.sh   (ENGINE=psync ./run_all.sh if libaio fails)
set -euo pipefail
cd "$(dirname "$0")"
REPS=${REPS:-3}
ENGINE=${ENGINE:-libaio}
LAB=/tmp/fio-lab
mkdir -p "$LAB" results
command -v fio >/dev/null || { echo "fio not installed: sudo apt install fio -y"; exit 1; }
# Pre-create the 1 GiB test file once so every run reads/writes the same, fully allocated file
[ -f "$LAB/db-test.bin" ] || dd if=/dev/zero of="$LAB/db-test.bin" bs=1M count=1024 status=none
{
  echo "date: $(date -Is)"; echo "fio: $(fio --version)"; uname -a
  echo "engine: $ENGINE"; echo "target: $LAB ($(df -T $LAB | tail -1))"
  lscpu | grep -E 'Model name|^CPU\(s\)'; free -h | head -2
} > results/environment.txt
for job in jobs/*.fio; do
  name=$(basename "$job" .fio)
  for r in $(seq 1 "$REPS"); do
    echo ">>> $name rep $r"
    sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true
    fio "$job" --ioengine="$ENGINE" --output="results/${name}_rep${r}.json" --output-format=json
  done
done
echo "Done. Now run: python3 analyze.py"
