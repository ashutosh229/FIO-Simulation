#!/usr/bin/env python3
"""Parse FIO JSON outputs -> summary.csv, summary.md and plots (mean +/- std over repetitions)."""
import json, glob, re, os, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

CASES = {"A": "randread 4K (100% R)", "B": "randrw 4K (70% R)", "C": "randrw 8K (30% R)", "D": "seq read 256K"}
rows = {}
for f in sorted(glob.glob("results/*_rep*.json")):
    m = re.match(r"results/([ABCD])_.*_qd(\d+)_rep(\d+)\.json", f)
    if not m: continue
    case, qd, rep = m.group(1), int(m.group(2)), int(m.group(3))
    j = json.load(open(f))["jobs"][0]
    rd, wr = j["read"], j["write"]
    iops = rd["iops"] + wr["iops"]
    bw = (rd["bw"] + wr["bw"]) / 1024  # KiB/s -> MiB/s
    # weighted-average latency across read/write ops (us)
    n = rd["total_ios"] + wr["total_ios"]
    avg = (rd["lat_ns"]["mean"] * rd["total_ios"] + wr["lat_ns"]["mean"] * wr["total_ios"]) / n / 1000
    def pct(side, p):
        return side["clat_ns"].get("percentile", {}).get(p, 0) / 1000 if side["total_ios"] else 0
    # report the worse (larger) of read/write percentile for mixed workloads
    p95 = max(pct(rd, "95.000000"), pct(wr, "95.000000")); p99 = max(pct(rd, "99.000000"), pct(wr, "99.000000"))
    rows.setdefault((case, qd), []).append(dict(iops=iops, bw=bw, avg=avg, p95=p95, p99=p99))

def ms(key, k):
    v = [r[key] for r in rows[k]]
    return st.mean(v), (st.stdev(v) if len(v) > 1 else 0.0)

keys = sorted(rows)
if not keys: raise SystemExit("No result files found in results/. Run ./run_all.sh first.")
with open("summary.csv", "w") as c, open("summary.md", "w") as m:
    hdr = ["Case", "Pattern", "QD", "Reps", "IOPS", "IOPS sd", "BW MiB/s", "Avg lat us", "P95 us", "P99 us", "P99 sd"]
    c.write(",".join(hdr) + "\n"); m.write("| " + " | ".join(hdr) + " |\n|" + "---|" * len(hdr) + "\n")
    for k in keys:
        v = [ms(x, k) for x in ("iops", "bw", "avg", "p95", "p99")]
        r = [k[0], CASES[k[0]], k[1], len(rows[k]), f"{v[0][0]:.0f}", f"{v[0][1]:.0f}", f"{v[1][0]:.1f}", f"{v[2][0]:.1f}", f"{v[3][0]:.1f}", f"{v[4][0]:.1f}", f"{v[4][1]:.1f}"]
        c.write(",".join(map(str, r)) + "\n"); m.write("| " + " | ".join(map(str, r)) + " |\n")

os.makedirs("plots", exist_ok=True)
for key, label, fname, logy in [("iops", "IOPS", "iops_vs_qd", True), ("bw", "Bandwidth (MiB/s)", "bw_vs_qd", True),
                                ("avg", "Average latency (us)", "avg_latency_vs_qd", True), ("p99", "P99 latency (us)", "p99_latency_vs_qd", True)]:
    plt.figure(figsize=(6, 4))
    for case in CASES:
        ks = [k for k in keys if k[0] == case]
        if not ks: continue
        mu = [ms(key, k)[0] for k in ks]; sd = [ms(key, k)[1] for k in ks]
        plt.errorbar([k[1] for k in ks], mu, yerr=sd, marker="o", capsize=3, label=f"{case}: {CASES[case]}")
    plt.xscale("log", base=2); plt.xticks([1, 8, 32], ["1", "8", "32"])
    if logy: plt.yscale("log")
    plt.xlabel("Queue depth (iodepth)"); plt.ylabel(label); plt.grid(alpha=.3); plt.legend(fontsize=7); plt.tight_layout()
    plt.savefig(f"plots/{fname}.png", dpi=150); plt.close()
print("Wrote summary.csv, summary.md, plots/*.png")
