"""Constants for the OvenMediaEngine integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ovenmediaengine"

# Config entry / flow keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USE_TLS = "use_tls"
CONF_ACCESS_TOKEN = "access_token"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PORT = 8081
DEFAULT_TLS_PORT = 8082
DEFAULT_USE_TLS = False
DEFAULT_VERIFY_SSL = True
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 5

UPDATE_LISTENER_TIMEOUT = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# Object kinds used to build stable unique ids: "vhost", "app", "stream"
KIND_VHOST = "vhost"
KIND_APP = "app"
KIND_STREAM = "stream"

# Protocols reported under Metrics.connections
CONNECTION_PROTOCOLS = (
    "webrtc",
    "llhls",
    "hls",
    "srt",
    "ovt",
    "file",
    "push",
    "thumbnail",
)

MANUFACTURER = "AirenSoft"
MODEL_SERVER = "OvenMediaEngine Server"
MODEL_VHOST = "Virtual Host"
MODEL_APP = "Application"
MODEL_STREAM = "Stream"
