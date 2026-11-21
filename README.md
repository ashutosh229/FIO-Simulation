<div align="center">

# FIO Database Storage Workload Benchmark

**A reproducible benchmarking suite that emulates PostgreSQL-style OLTP and analytics storage I/O with [FIO](https://github.com/axboe/fio), then turns the raw JSON output into tables and plots.**

![FIO](https://img.shields.io/badge/FIO-3.36-orange)
![Python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20WSL2-FCC624?logo=linux&logoColor=black)
![I/O engine](https://img.shields.io/badge/io__engine-libaio-informational)
![Runs](https://img.shields.io/badge/matrix-4%20cases%20%C3%97%203%20queue%20depths%20%C3%97%203%20reps-success)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

---

## Table of contents

- [Overview](#overview)
- [Experiment design](#experiment-design)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Outputs](#outputs)
- [Results](#results)
- [Methodology notes](#methodology-notes)
- [Limitations](#limitations)
- [Repository structure](#repository-structure)
- [Troubleshooting](#troubleshooting)
- [Safety](#safety)
- [License](#license)

## Overview

Databases are ultimately limited by how their storage layer behaves under specific access patterns. This project answers a
practical question: **how do IOPS, bandwidth and latency (average and tail) change with I/O pattern, block size, read/write mix
and queue depth on a given storage device?**

Rather than installing a database, it uses FIO to reproduce the *shape* of PostgreSQL's storage traffic:

| Database behaviour | FIO emulation |
|---|---|
| Indexed point lookups that miss the cache | Small random reads |
| Transactional page reads plus dirty-page write-back | Random read/write mix |
| 8 KiB page I/O under heavy updates | Random mix at 8 KiB, write-dominated |
| Table scans, analytics, backups | Large sequential reads |

The suite automates the whole pipeline: **12 job files, 3 repetitions each, JSON capture, environment recording, statistical
summary and plotting.**

## Experiment design

### Workload cases

| Case | Pattern (`rw`) | Block size | Read share | PostgreSQL I/O it approximates |
|---|---|---|---|---|
| **A** | `randread` | 4 KiB | 100% | Cache-missing index and point lookups |
| **B** | `randrw` | 4 KiB | 70% | Read-heavy transactional mix |
| **C** | `randrw` | 8 KiB | 30% | Update-heavy workload at PostgreSQL's native page size |
| **D** | `read` | 256 KiB | 100% | Sequential scans, analytics, backups |

Each case is run at **queue depths 1, 8 and 32**, giving 12 configurations and 36 runs in total.

### Fixed parameters

| Parameter | Value | Why |
|---|---|---|
| `ioengine` | `libaio` | Native asynchronous I/O, required to sustain queue depth |
| `direct` | `1` | Bypass the guest page cache so the storage path is measured |
| `size` | `1g` | Fixed 1 GiB working file |
| `runtime` / `ramp_time` | `45 s` / `5 s` | Warm-up excluded from statistics |
| `time_based` | `1` | Every run lasts the same wall time |
| `numjobs` | `1` | Single submitter, so queue depth is the only concurrency variable |
| `group_reporting` | `1` | Aggregate statistics |
| `percentile_list` | `50:95:99` | Median and tail latency |
| Repetitions | `3` | Mean and standard deviation per configuration |

Only `rw`, `bs`, `rwmixread` and `iodepth` vary between job files, so differences in the results are attributable to those
parameters.

## Quick start

### Requirements

| Requirement | Notes |
|---|---|
| Linux (native or WSL2) | The included results were collected on WSL2 |
| FIO 3.x | `sudo apt install fio` |
| Python 3.8+ and `matplotlib>=3.8.0` | Only needed for analysis |
| About 1 GiB free in `/tmp` | For the test file |
| About 30 minutes | 36 runs of roughly 50 s each (45 s runtime plus 5 s ramp) |

### Run

```bash
# 1. Install FIO and verify
sudo apt update && sudo apt install fio -y
fio --version

# 2. Python environment for the analysis step
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Make sure the target has space and the runner is executable
df -h /tmp
chmod +x run_all.sh

# 4. Run the full matrix (about 30 minutes) on an otherwise idle machine
./run_all.sh

# 5. Generate summary.csv, summary.md and plots/*.png
python3 analyze.py
```

Validate a job file's syntax without running it:

```bash
fio --parse-only jobs/A_randread_4k_qd1.fio
```

## Configuration

`run_all.sh` is configured through environment variables:

| Variable | Default | Description |
|---|---|---|
| `ENGINE` | `libaio` | I/O engine. Use `ENGINE=psync ./run_all.sh` if `libaio` or direct I/O is unsupported on your filesystem |
| `REPS` | `3` | Repetitions per configuration |

```bash
ENGINE=psync ./run_all.sh        # fallback engine (document this in any report)
REPS=5 ./run_all.sh              # tighter confidence intervals
```

Per run, the script:

1. Creates the 1 GiB test file once (`/tmp/fio-lab/db-test.bin`) so every run uses the same fully allocated file
2. Records the environment to `results/environment.txt`
3. Syncs and drops the page cache when `sudo` permits it (failure is tolerated)
4. Executes FIO and writes `results/<job>_rep<N>.json`

## Outputs

| Path | Contents |
|---|---|
| `results/*_rep*.json` | Raw FIO JSON for each of the 36 runs |
| `results/environment.txt` | Date, FIO version, kernel, CPU, memory, engine and target filesystem |
| `summary.csv` | Mean and standard deviation per configuration (machine-readable) |
| `summary.md` | Same table in Markdown |
| `plots/iops_vs_qd.png` | IOPS versus queue depth |
| `plots/bw_vs_qd.png` | Bandwidth versus queue depth |
| `plots/avg_latency_vs_qd.png` | Average latency versus queue depth |
| `plots/p99_latency_vs_qd.png` | P99 latency versus queue depth |

All plots use log axes and show standard-deviation error bars over the repetitions.

## Results

Mean over 3 runs. Environment: **WSL2** (kernel 5.15.146.1), Intel Core i5-12450H (12 logical CPUs), 7.6 GiB RAM, ext4 on a
WSL2 virtual disk, FIO 3.36, `libaio`, `direct=1`.

| Case | Pattern | QD | IOPS | IOPS sd | BW (MiB/s) | Avg lat (µs) | P95 (µs) | P99 (µs) | P99 sd |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | randread 4K, 100% R | 1 | 17,354 | 1,136 | 67.8 | 57.1 | 111.8 | 204.5 | 27.3 |
| A | randread 4K, 100% R | 8 | 107,357 | 5,397 | 419.4 | 74.2 | 148.5 | 221.5 | 11.8 |
| A | randread 4K, 100% R | 32 | 195,961 | 12,887 | 765.5 | 163.5 | 263.5 | 880.6 | 99.7 |
| B | randrw 4K, 70% R | 1 | 7,509 | 220 | 29.3 | 131.9 | 233.8 | 545.5 | 23.6 |
| B | randrw 4K, 70% R | 8 | 34,612 | 2,723 | 135.2 | 231.4 | 998.1 | 1,608.4 | 62.0 |
| B | randrw 4K, 70% R | 32 | 50,637 | 1,429 | 197.8 | 631.7 | 1,805.0 | 5,450.4 | 496.2 |
| C | randrw 8K, 30% R | 1 | 5,319 | 475 | 41.6 | 187.4 | 1,166.0 | 1,927.9 | 246.1 |
| C | randrw 8K, 30% R | 8 | 16,637 | 596 | 130.0 | 480.5 | 2,342.9 | 7,372.8 | 511.9 |
| C | randrw 8K, 30% R | 32 | 18,365 | 487 | 143.5 | 1,743.1 | 10,507.6 | 28,530.0 | 2,198.5 |
| D | seq read 256K | 1 | 1,359 | 38 | 339.8 | 733.0 | 981.7 | 1,280.7 | 77.4 |
| D | seq read 256K | 8 | 5,919 | 14 | 1,479.8 | 1,350.7 | 1,805.0 | 2,097.2 | 14.2 |
| D | seq read 256K | 32 | 6,393 | 87 | 1,598.5 | 5,004.3 | 7,154.3 | 9,295.2 | 1,131.5 |

### Key findings

- **IOPS and bandwidth measure different things.** At QD8, random 4 KiB reads (A) deliver 18× the IOPS of sequential 256 KiB
  reads (D) but only 28% of its bandwidth (419 vs 1,480 MiB/s). Use IOPS for lookup-style workloads and bandwidth for scans.
- **Deeper queues trade latency for throughput.** For case A, QD1 to QD32 raises IOPS 11× while P99 latency rises 4.3×
  (205 to 881 µs).
- **Returns diminish quickly.** From QD8 to QD32, case C gains only 10% IOPS and case D only 8%, while P99 grows 3.9× and
  4.4× respectively. Case D delivers 93% of its QD32 bandwidth already at QD8, which points to a saturation ceiling near
  1.5 to 1.6 GiB/s.
- **Writes are expensive and variable.** Adding 30% writes (A to B) cuts IOPS by 68% at QD8 and multiplies P99 latency by
  7.3×.
- **Tail latency tells a different story than the average.** Case C at QD32 has a 1.7 ms average but a 28.5 ms P99.
- **Results are repeatable.** Throughput standard deviation is at most 8.9% of the mean; the trends above are far larger than
  the run-to-run noise.

**Practical takeaway:** a moderate queue depth (about 8 on this setup) captures most of the throughput without the latency
penalty of deeper queues, and capacity decisions should be driven by tail latency rather than averages.

## Methodology notes

- **Throughput** is read plus write combined; bandwidth is converted to MiB/s (base 2).
- **Average latency** is the operation-weighted mean of total latency (`lat`) across reads and writes.
- **P95 / P99** are completion-latency (`clat`) percentiles. For mixed workloads the *larger* of the read and write percentile
  is reported, so these figures mainly reflect the slower direction (typically writes).
- **Sanity checks:** bandwidth equals IOPS × block size, and IOPS matches queue depth ÷ average latency to within about 1%,
  confirming the requested depth was actually kept outstanding. The raw JSON `iodepth_level` field shows 100% of I/O issued
  at the configured depth.
- **Cosmetic note:** `ioengine` appears twice in the JSON global options because the script passes `--ioengine` on the command
  line in addition to the job file. Both values are identical.

## Limitations

- **Synthetic workload.** FIO generates storage I/O only. It does not model SQL execution, locking, query planning, shared
  buffers, WAL `fsync` or checkpoint bursts.
- **Direct I/O.** PostgreSQL mostly uses buffered I/O through the OS page cache. `direct=1` is used here to isolate the
  storage path.
- **Uniform random offsets.** Real databases have skewed hot sets that caches largely absorb.
- **Virtualised target.** The included results come from an ext4 virtual disk inside WSL2. Host-side caching is not visible or
  controllable from the guest, and dropping caches inside WSL does not clear host caches. Treat absolute numbers as specific to
  that machine and compare *across configurations*, not against datasheet figures.
- **Single submitter.** `numjobs=1` means a per-thread submission limit cannot be separated from a device limit.
- **Case A block size.** Case A uses 4 KiB blocks (a standard point-lookup profile) although PostgreSQL pages are 8 KiB.

## Repository structure

```text
.
├── README.md
├── LICENSE
├── requirements.txt
├── run_all.sh              # runs every job REPS times, saves JSON + environment info
├── analyze.py              # parses JSON -> summary.csv, summary.md, plots/*.png
├── jobs/                   # 12 FIO job files: cases A-D x queue depth 1, 8, 32
│   ├── A_randread_4k_qd{1,8,32}.fio
│   ├── B_randrw_4k_qd{1,8,32}.fio
│   ├── C_randrw_8k_qd{1,8,32}.fio
│   └── D_read_256k_qd{1,8,32}.fio
├── results/                # raw FIO JSON and environment.txt (generated)
├── plots/                  # generated figures
├── summary.csv             # generated
├── summary.md              # generated
└── report.md               # written analysis of the results
```

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `fio not installed` | `sudo apt install fio -y` |
| `libaio` or direct I/O errors | Filesystem or environment does not support it. Re-run with `ENGINE=psync ./run_all.sh` and note the change in your report |
| `No result files found in results/` | `analyze.py` ran before `run_all.sh`. Run the benchmark first |
| `ModuleNotFoundError: matplotlib` | Activate your virtual environment and `pip install -r requirements.txt` |
| `Permission denied` on `./run_all.sh` | `chmod +x run_all.sh` |
| Cache drop fails silently | Expected without `sudo`. The script continues, but cold-cache behaviour is less strictly enforced |
| Very noisy results | Close other applications, run on an idle machine, and consider `REPS=5` |
| Running from `/mnt/c` on WSL | The test file lives in `/tmp` (the Linux filesystem), which is correct. Do not point the job files at `/mnt/c`, as I/O there goes through a slow translation layer |

## Safety

`run_all.sh` writes only to `/tmp/fio-lab/db-test.bin`. **Never point the job files at a raw block device** (for example
`/dev/sdX`) with write workloads, because cases B and C write data and would destroy its contents.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Ashutosh Kumar Jha.

Built for CS559 (System Design), Lab 10.
