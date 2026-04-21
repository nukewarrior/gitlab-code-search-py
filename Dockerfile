FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/gcs

COPY dist/gcs-linux-x86_64 /usr/local/bin/gcs
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/gcs /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data

ENV GCS_PORT=8765 \
    GCS_WORKDIR=/data \
    GCS_WORKERS=8

EXPOSE 8765
VOLUME ["/data"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
