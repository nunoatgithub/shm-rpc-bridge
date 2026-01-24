#!/usr/bin/env python3
"""Usage: python log_stats.py <logfile>"""

import re
import sys
from collections import defaultdict

REQ_PATTERN = re.compile(r"request written \((\d+) bytes\).*srb_(\w+)_req")
RESP_PATTERN = re.compile(r"srb_(\w+)_resp.*response \((\d+) bytes\)")

stats = defaultdict(lambda: {"req": [], "resp": []})

with open(sys.argv[1]) as f:
    for line in f:
        if m := REQ_PATTERN.search(line):
            stats[m.group(2)]["req"].append(int(m.group(1)))
        elif m := RESP_PATTERN.search(line):
            stats[m.group(1)]["resp"].append(int(m.group(2)))

all_req = [b for s in stats.values() for b in s["req"]]
all_resp = [b for s in stats.values() for b in s["resp"]]

def freq(sizes):
    from collections import Counter
    c = Counter(sizes)
    total = len(sizes)
    return [(sz, n, n/total*100) for sz, n in c.most_common()]

print(f"Channels: {len(stats)}")
print(f"Total requests: {len(all_req):,}, bytes: {sum(all_req):,}")
print(f"Total responses: {len(all_resp):,}, bytes: {sum(all_resp):,}")
print(f"Biggest request: {max(all_req):,}" if all_req else "Biggest request: 0")
print(f"Biggest response: {max(all_resp):,}" if all_resp else "Biggest response: 0")

def print_distribution(title, items):
    print(f"\n{title}:")
    if not items:
        print("  (none)")
        return
    size_strs = [f"{sz:,}" for sz, _, _ in items]
    count_strs = [f"{cnt:,}" for _, cnt, _ in items]
    pct_strs = [f"{pct:.1f}%" for _, _, pct in items]
    size_w = max(len(s) for s in size_strs + ["Size"]) + 2
    count_w = max(len(s) for s in count_strs + ["Count"]) + 2
    pct_w = max(len(s) for s in pct_strs + ["%"]) + 2
    # header
    print(f"  {'Size':>{size_w}}{'Count':>{count_w}}{'%':>{pct_w}}")
    print(f"  {'-'* (size_w) }{'-'* (count_w) }{'-'* (pct_w) }")
    for ssz, scnt, spct in items:
        ssz_s = f"{ssz:,}"
        scnt_s = f"{scnt:,}"
        spct_s = f"{spct:.1f}%"
        print(f"  {ssz_s:>{size_w}}{scnt_s:>{count_w}}{spct_s:>{pct_w}}")

print_distribution("Request size distribution", freq(all_req))
print_distribution("Response size distribution", freq(all_resp))

# per-channel printing moved to bottom; define a printer that produces an aligned table
def print_per_channel_table(stats):
    items = []
    for ch, s in stats.items():
        req_cnt = len(s["req"]) ; req_bytes = sum(s["req"])
        resp_cnt = len(s["resp"]) ; resp_bytes = sum(s["resp"])
        total = req_bytes + resp_bytes
        items.append((ch, req_cnt, req_bytes, resp_cnt, resp_bytes, total))
    if not items:
        print("\nPer channel:\n  (none)")
        return
    items.sort(key=lambda x: x[5], reverse=True)
    ch_strs = [ch for ch, *_ in items]
    reqc_strs = [f"{rc:,}" for _, rc, _, _, _, _ in items]
    reqb_strs = [f"{rb:,}" for _, _, rb, _, _, _ in items]
    respc_strs = [f"{pc:,}" for _, _, _, pc, _, _ in items]
    respb_strs = [f"{pb:,}" for _, _, _, _, pb, _ in items]
    tot_strs = [f"{t:,}" for *_, t in items]
    ch_w = max(len(s) for s in ch_strs + ["Channel"]) + 2
    reqc_w = max(len(s) for s in reqc_strs + ["ReqCnt"]) + 2
    reqb_w = max(len(s) for s in reqb_strs + ["ReqBytes"]) + 2
    respc_w = max(len(s) for s in respc_strs + ["RespCnt"]) + 2
    respb_w = max(len(s) for s in respb_strs + ["RespBytes"]) + 2
    tot_w = max(len(s) for s in tot_strs + ["TotalBytes"]) + 2
    print("\nPer channel:")
    header = f"  {'Channel':>{ch_w}}{'ReqCnt':>{reqc_w}}{'ReqBytes':>{reqb_w}}{'RespCnt':>{respc_w}}{'RespBytes':>{respb_w}}{'TotalBytes':>{tot_w}}"
    print(header)
    print("  " + "-" * (len(header)-2))
    for ch, rc, rb, pc, pb, tot in items:
        rc_s = f"{rc:,}"
        rb_s = f"{rb:,}"
        pc_s = f"{pc:,}"
        pb_s = f"{pb:,}"
        tot_s = f"{tot:,}"
        print(f"  {ch:>{ch_w}}{rc_s:>{reqc_w}}{rb_s:>{reqb_w}}{pc_s:>{respc_w}}{pb_s:>{respb_w}}{tot_s:>{tot_w}}")

# call per-channel table at the end
print_per_channel_table(stats)
