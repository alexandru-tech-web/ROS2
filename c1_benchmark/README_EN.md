# C1 -- ROS 2 middleware benchmark under controlled network degradation

Artifact for the C1 paper: a comparison of **`rmw_zenoh_cpp`** and
**`rmw_cyclonedds_cpp`** under network degradation applied with `tc netem`,
measured on two layers -- transport (round-trip time on an echo service) and a
full Search-and-Rescue mission.

This file is the English entry point to the artifact. The detailed technical
documentation (`README.md`, in Romanian) remains the reference for day-to-day
work; this file is what a reviewer needs.

## 1. Headline result

Under 200 ms latency with 50 ms jitter (`lat200_jit50`), the two middlewares
behave the same in simulation and differently on real hardware:

| Environment | Middleware | Sample loss | p95 RTT |
|---|---|---|---|
| SIL (loopback) | cyclonedds | 1.8 % | -- |
| SIL (loopback) | zenoh | 1.3 % | -- |
| HIL (two hosts, WiFi) | cyclonedds | 14.7 % | 635.2 ms |
| HIL (two hosts, WiFi) | zenoh | 96.3 % | 7696.9 ms |

The gap is a factor of **12x in p95 RTT** (7696.9 / 635.2 = 12.1) and it does
not appear in loopback testing at all. That is the point of the paper: a
loopback benchmark would have reported these two middlewares as equivalent.

Source of these numbers: `paper/campaign_summary.csv`, aggregated from the raw
campaign by `analyze_campaign.py`. Repetitions per cell: **10 in SIL, 5 in HIL**.

## 2. What is measured

- **Transport layer** -- `bench_client.py` sends requests to
  `bench_echo_server.py` and records round-trip time. Payloads: **64 B**
  (command), **4096 B** (telemetry), **65536 B** (map).
- **Mission layer** -- a full `sar_swarm` mission runs under the same
  degradation; mission-level metrics are extracted by `bench_core.py`.
- **Network conditions** -- 24 conditions defined in `bench_core.CONDITIONS`,
  applied by `netem.py`. They cover loss (independent and bursty),
  latency + jitter, and Gilbert-Elliott channels. See the name map in
  `paper/VERSIUNI.md`.

Cells where the link failed completely are **not silently dropped**: they are
recorded as `received=0` and drawn as an explicit hatched marker in the
figures (`plot_extra.py`, `analyze_campaign.py`). Medians are computed over
surviving samples, with the number of total failures reported alongside.

## 3. Reproducing the results

Requirements: ROS 2 Jazzy, Python 3.12, `tc` (iproute2), plus
`pip install -r requirements.txt`. Applying `netem` needs root.

**Self-checks (no ROS, no root, safe at any time):**

```bash
python3 test_bench_core.py             # unit tests for the pure core
python3 analyze_campaign.py --selftest # end-to-end analysis flow on synthetic data
python3 run_campaign.py --dry          # print the campaign plan, change nothing
```

**SIL -- one machine, loopback:**

```bash
./preflight.sh                         # expected: VERDICT: GO
python3 run_campaign.py --iface lo --reps 5 --out ~/c1_results_full
python3 analyze_campaign.py ~/c1_results_full
```

**HIL -- two machines over a real link.** This is the configuration that
produced the headline result, and it cannot be reproduced on one host. One
machine runs the echo server, the other the client; each runs a Zenoh router
(`router_pi.json5`, `router_m1.json5` -- edit the addresses for your LAN).
Degradation is applied on the real interface with `hil_netem.py`, not on `lo`.

`preflight.sh` is a gate, not a formality: it refuses to run when a residual
`tc` qdisc or a live ROS process from a previous run would contaminate the
measurement.

## 4. Environment versions

Collected read-only from the campaign machine on 2026-07-07
(`paper/VERSIUNI.md`).

| Component | Client host (laptop) | Server host (Raspberry Pi 4) |
|---|---|---|
| Kernel | 6.17.0-35-generic | not recorded |
| Distro | Ubuntu 24.04.4 LTS | not recorded |
| ROS 2 | Jazzy Jalisco | Jazzy Jalisco |
| `rmw_cyclonedds_cpp` | 2.2.3 | not recorded |
| CycloneDDS | 0.10.5 | not recorded |
| `rmw_zenoh_cpp` / zenohd | 0.2.9 | not recorded |

The Raspberry Pi versions were never collected; the placeholders are marked as
such in `paper/VERSIUNI.md` rather than filled with assumed values. This is an
open gap, and it is stated here rather than hidden.

## 5. Repository layout

This artifact lives inside a larger doctoral monorepo. Only `c1_benchmark/` is
part of the C1 paper, and only `c1_benchmark/` is covered by the Apache-2.0
`LICENSE` in this directory.

| Path | Contents |
|---|---|
| `bench_core.py` | pure core: conditions, RTT statistics, campaign plan |
| `bench_client.py`, `bench_echo_server.py` | the transport microbenchmark |
| `netem.py`, `hil_netem.py` | apply / clear the network condition |
| `run_campaign.py` | orchestrator (`--dry` prints the plan) |
| `analyze_campaign.py` | aggregation and paper figures (`--selftest`) |
| `preflight.sh` | environment gate, explicit GO / NO-GO verdict |
| `paper/` | paper sources, figures, version and data manifests |
| `test_*.py` | unit tests for the pure cores |

## 6. Versioning

The tag **`c1-paper-v3.4`** pins the exact tree that produced the paper's
numbers and figures. It is immutable. `main` has moved on since -- most
notably it adds the C2 condition set (`bern_*`, `ge_*`) which is **not** part
of the C1 paper. To reproduce the paper, check out the tag.

## 7. Data availability

The raw campaign data is **not stored in this repository** -- it is measurement
output, not source, and keeping it in git would be wrong for both size and
provenance reasons.

What is in the repository is the evidence that fixes the data:

- `paper/MANIFEST_DATE.md` -- the source of truth. It lists **720 canonical
  summary files** (720 expected, 720 present) with a **SHA256** and a size for
  each, plus a per-cell completeness matrix. Any copy of the data can be
  checked against it byte for byte.
- `paper/campaign_summary.csv` -- the aggregate the paper's tables are built
  from.

Canonical layout of the dataset:

```
<env>/date/<rmw>/<cond>/rep<N>/transport_p<P>_summary.json   (+ transport_p<P>.csv)
env  in {SIL, HIL_WIFI}     rep  1..10 (SIL), 1..5 (HIL)     P in {64, 4096, 65536}
```

**Availability.** The dataset is available from the author on request. A public
deposit with a DOI will be created at publication; the recommended data licence
is CC-BY-4.0, and the archive structure is already specified in
`paper/MANIFEST_DATE.md`. Until then, the SHA256 manifest is what makes the
results checkable: it is a commitment to a fixed dataset made before review,
not after.

## 8. License

Apache-2.0, see `LICENSE` in this directory. The rest of the monorepo is
unpublished work and is not covered.
