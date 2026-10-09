# TrafficLens Network Experiments & Benchmarking

This directory contains network performance benchmark scripts and instructions for testing network impairment, connection reuse latency, rate limiting, and backend fault tolerance.

---

## 1. Connection Reuse Benchmark (Persistent Keep-Alive vs New TCP Connection)

Run the automated benchmark script to compare HTTP keep-alive persistent connection reuse against per-request TCP handshakes:

```bash
python -m experiments.benchmark
```

### Expected Output
The script measures 50 requests in both modes, inserts records into the `connection_benchmarks` PostgreSQL table, and outputs JSON to `experiments/results/benchmark_results.json`:

```json
{
  "timestamp": "2026-10-09T16:00:00Z",
  "request_count": 50,
  "persistent_median_latency_ms": 4.2,
  "persistent_average_latency_ms": 4.5,
  "new_connection_median_latency_ms": 18.7,
  "new_connection_average_latency_ms": 19.2,
  "overhead_saved_ms": 14.5
}
```

---

## 2. Interactive Network Delay Experiment

1. Open the TrafficLens Web Dashboard at `http://localhost:8501`.
2. Click **Add 300 ms delay to Orders**.
3. Send requests to `/gateway/orders/orders`.
4. Observe the p50/p95 latency spike on the dashboard chart and the status badge for Orders transition to **Slow**.

---

## 3. Backend Stop / Failure Simulation Experiment

1. Open the TrafficLens Web Dashboard at `http://localhost:8501`.
2. Click **Stop Notifications service**.
3. Send requests to `/gateway/notifications/send`.
4. Observe the Notification Service health state transition to **Down** on the health table and gateway returning **HTTP 502 Bad Gateway**.
5. Click **Restart Notifications service** to recover the service.

---

## 4. Optional Linux Netem Network Impairment (Advanced)

On Linux systems, you can inject packet delay or loss at the network interface level using `tc`:

```bash
# Add 100ms delay to loopback interface
sudo tc qdisc add dev lo root netem delay 100ms

# Remove delay
sudo tc qdisc del dev lo root
```
