# Docker Clock Synchronization Fix

## Problem
JWT tokens expire immediately after refresh due to clock sync issues between Docker container and Supabase server.

## Solutions

### 1. Add to docker-compose.yml
```yaml
services:
  backend:
    # ... existing config
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro
    environment:
      - TZ=UTC
```

### 2. Add NTP sync to Dockerfile
```dockerfile
# Add to your Dockerfile
RUN apt-get update && apt-get install -y ntp ntpdate
RUN ntpdate -s time.nist.gov
```

### 3. Check host system time
```bash
# On your host system
date
timedatectl status
sudo ntpdate -s time.nist.gov
```

### 4. Restart containers with time sync
```bash
docker-compose down
docker-compose up -d
```

### 5. Verify time sync in container
```bash
docker exec -it <container-name> date
# Should match: date
```

## Alternative: JWT Tolerance Buffer

If clock sync can't be fixed immediately, add tolerance for JWT validation:

```python
# Add to auth client or JWT validation
import os
JWT_CLOCK_SKEW_TOLERANCE = int(os.getenv('JWT_CLOCK_SKEW_TOLERANCE', '300'))  # 5 minutes
```