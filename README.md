# FlowFIO

Simple MVP web app to run and manage FIO storage benchmarks.

<img src="https://media.licdn.com/dms/image/v2/D4E03AQElteWnLMJmhA/profile-displayphoto-shrink_400_400/B4EZReEdFjHgAg-/0/1736745014460?e=1756339200&v=beta&t=N3aATXmVw8Kg8s9LVMFESFetLuY1IDp3batIBiF1FzQ" width="80">

## Run
```bash
docker-compose up --build
```

Open dashboard on port 8050 over docker/orbstack default-network.
http://localhost:8050

## What
- Configure FIO params (direct I/O, block size, jobs, queue depth)
- Run tests
- See charts (IOPS, bandwidth, latency)
- JSON output in `test-data/`
