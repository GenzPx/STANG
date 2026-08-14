# Deployment

## Development

```bash
stang encode data.json data.stg
stang verify data.stg
```

## Production Considerations

- Use process management (systemd, supervisor).
- Set environment variables in `.env`.
- Configure logging.
- Restrict file permissions.
- Back up `.stg` files regularly.
- Implement health checks.

## systemd Example

```ini
[Unit]
Description=STANG Service
After=network.target

[Service]
Type=simple
User=stang
WorkingDirectory=/opt/stang
EnvironmentFile=/opt/stang/.env
ExecStart=/opt/stang/.venv/bin/stang verify /opt/stang/data.stg
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Docker

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install -e .
CMD ["stang", "--help"]
```

### docker-compose.yml

```yaml
version: "3.9"
services:
  stang:
    build: .
    volumes:
      - ./data:/app/data
```

Docker is optional.
