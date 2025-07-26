# FIO Dashboard

Web UI for FIO storage benchmarks.

## Run

```bash
docker-compose up --build
```

http://localhost:8050

## What

- Configure FIO params (direct I/O, block size, jobs, queue depth)
- Run tests
- See charts (IOPS, bandwidth, latency)
- JSON output in `test-data/`
