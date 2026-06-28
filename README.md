# OvenMediaEngine — Home Assistant integration

A custom [HACS](https://hacs.xyz/) integration that polls the
[OvenMediaEngine](https://github.com/AirenSoft/OvenMediaEngine) (OME) REST API v1 and exposes its live
statistics as Home Assistant sensors.

It **auto-discovers the full topology** — every virtual host → application → stream — and creates one device
per object, with entities added/removed as streams come and go. Each stream also gets an **`online` binary
sensor** so you can automate on a stream going live or dropping (e.g. OBS connecting/disconnecting).

## Entities

For every vhost, app and stream the integration creates these sensors from OME's `Metrics`:

| Entity | OME field | Notes |
|--------|-----------|-------|
| Total connections | `totalConnections` | per-protocol counts (webrtc/llhls/hls/srt/…) as attributes |
| Max total connections | `maxTotalConnections` | diagnostic |
| Throughput in | `lastThroughputIn` | bit/s |
| Average throughput in/out | `avgThroughputIn` / `Out` | bit/s, diagnostic |
| Max throughput in/out | `maxThroughputIn` / `Out` | bit/s, diagnostic |
| Total bytes in/out | `totalBytesIn` / `Out` | total increasing |

Per **stream** only:

| Entity | Meaning |
|--------|---------|
| Online (binary_sensor, connectivity) | `on` while the stream exists on the server |

## Requirements

- Home Assistant **2024.12** or newer.
- OME REST API reachable from HA. In this repo's deployment the API is published on host port **`<PORT>`**
  (`docker-compose.yml` maps `<PORT>:8081`). Make sure that port mapping exists.
- The API **access token** from `conf/Server.xml` (`<AccessToken>`).

## Install

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories** → add this repo URL, category **Integration**.
2. Install **OvenMediaEngine**, then restart Home Assistant.

### Manual

Copy `custom_components/ovenmediaengine` into your HA `config/custom_components/` directory and restart.

## Configure

**Settings → Devices & Services → Add Integration → OvenMediaEngine**, then provide:

| Field | Example | Notes |
|-------|---------|-------|
| Host | `<SERVER>` | OME host |
| Port | `<PORT>` | host-side API port (`8081` default OME) |
| Access token | `<ACCESS_TOKEN>` | from `Server.xml`; the value may contain a `:` — paste it whole |
| Use HTTPS (TLS) | off | enable for the `8082` TLS API |
| Verify SSL certificate | on | disable only for self-signed certs |

The update interval (default **30 s**) can be changed later via the integration's **Configure** (options).

> **Auth detail:** OME expects `Authorization: Basic base64(<AccessToken>)` — the *entire* token is
> base64-encoded (it is not a `user:password` pair even though it contains a colon). The integration handles
> this for you; just paste the token verbatim.

## Verify the API by hand

```bash
curl -u "<ACCESS_TOKEN>" http://<SERVER>:<PORT>/v1/vhosts
curl -u "<ACCESS_TOKEN>" \
  http://<SERVER>:<PORT>/v1/stats/current/vhosts/default/apps/app
```

(`curl -u` happens to base64 the colon-containing token the same way OME wants, so it is a faithful check.)

## Security

The access token is stored in Home Assistant's config entry (encrypted at rest). **Do not commit a real
token** to version control. Rotate `<AccessToken>` in `Server.xml` if it leaks.
