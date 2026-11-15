# CS559 Lab 10: Simulating Database Storage Workloads with FIO

**Author:** Ashutosh Kumar Jha
**Chosen database:** PostgreSQL (OLTP use case). See `report.md` for justification and workload mapping.

## Contents
| File | Purpose |
|---|---|
| `jobs/*.fio` | 12 job files: cases A-D x queue depth 1, 8, 32 |
| `run_all.sh` | Runs every job 3 times, saves JSON + environment info |
| `analyze.py` | Parses JSON, writes `summary.csv`, `summary.md`, `plots/*.png` |
| `results/` | Raw FIO JSON outputs and `environment.txt` (created by the run) |
| `report.md` | Report draft (convert to PDF after adding your results) |

## Cases
| Case | Pattern | Block size | Read mix | Queue depths |
|---|---|---|---|---|
| A | randread | 4 KiB | 100% | 1, 8, 32 |
| B | randrw | 4 KiB | 70% | 1, 8, 32 |
| C | randrw | 8 KiB | 30% | 1, 8, 32 |
| D | read | 256 KiB | 100% | 1, 8, 32 |

Fixed for every run: ioengine=libaio, direct=1, size=1g, runtime=45 s, ramp_time=5 s, numjobs=1, group_reporting, percentiles 50/95/99, 3 repetitions.

## How to run
```bash
sudo apt update && sudo apt install fio -y
fio --version
df -h /tmp                 # need > 1 GiB free
./run_all.sh               # about 12 x 3 x 50 s = 30 minutes
python3 analyze.py         # needs: pip install matplotlib
```
- If libaio/direct I/O fails (common on WSL or some filesystems): `ENGINE=psync ./run_all.sh`, then document the engine and reason in the report.
- `run_all.sh` only touches `/tmp/fio-lab/db-test.bin`. Never point it at a raw device.
- Check job syntax without running: `fio --parse-only jobs/A_randread_4k_qd1.fio`
- Run on an otherwise idle machine; close other applications.

## Reproducibility notes
`results/environment.txt` records date, FIO version, kernel, CPU, memory, engine and the filesystem of the target. The page cache is dropped before each run when sudo allows it.
