# FlowFIO

Run and manage FIO storage benchmarks– https://linux.die.net/man/1/fio

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
- See info + charts (IOPS, bandwidth, latency)


# Run Test
<img width="1728" height="962" alt="image" src="https://github.com/user-attachments/assets/131e43e0-0766-4062-9196-38110aebd6bd" />

# Config Layer
something like a semantic layer is in the works. still thinking about UX...
<img width="1728" height="956" alt="image" src="https://github.com/user-attachments/assets/25fa8e60-8cff-4750-917b-c2254e19455e" />

