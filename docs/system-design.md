# System design and offline alert pipeline

## Design goals

- Camera processing and inference work without internet access.
- The default data path remains on one device; no cloud account or subscription is required.
- Optional LAN notifications work only while the local network is available.
- WAN-dependent notifications are explicitly opt-in and disclose the external service boundary.

## Component architecture

```text
Camera sensor
    |
    | CSI-2 on Pi (or USB / laptop webcam for POC)
    v
Capture service --> Motion detector --> Bounded event queue
                                          |
                                          v
                                  Local inference worker
                                          |
                          +---------------+---------------+
                          |                               |
                          v                               v
                 Local snapshot store               Event database
                          |                               |
                          +---------------+---------------+
                                          |
                                          v
                             LAN dashboard / local webhook
```

On the laptop POC, `src/laptop_poc.py` captures a frame, detects motion, calls Ollama synchronously, and appends the result to `events.jsonl`. The Raspberry Pi design should separate capture from inference with a bounded queue, then use a database and retention policy as event volume grows.

## Event record

A useful event record includes:

- Unique event ID and local timestamp with time zone.
- Detection status and classes with confidence scores.
- Snapshot filename or local database reference.
- Model name/version and pipeline version.
- Optional camera ID and zone ID.
- Processing outcome, including inference errors and dropped-queue events.

Do not put passwords, API keys, or other credentials in event metadata. Store only the information needed for operation and review.

## Offline behavior versus notifications

**Offline means no internet is required for capture, local inference, storage, and review from the device itself.** The Pi can continue recording selected events when the WAN is down. It cannot deliver a message to a remote phone if the phone is outside the local network and there is no internet path.

Notification options:

1. **Local IP dashboard:** Serve a small event page on the Pi and open it from a device on the same Wi-Fi/LAN, for example `http://<pi-address>:<port>`. This requires only local connectivity. Use authentication, firewall restrictions, and preferably HTTPS if credentials or images are accessed over Wi-Fi. A static IP or DHCP reservation makes the address easier to find.
2. **LAN webhook or MQTT:** POST an event to a receiver on the home LAN, or publish to a broker such as a self-hosted MQTT broker. Both sender and receiver remain local. Restrict access to the LAN and authenticate the receiver.
3. **WhatsApp or other hosted messaging:** WhatsApp Business/Cloud API involves Meta's external service, internet connectivity, credentials, and its own policies/costs. It is not an offline or cloud-free alert channel. If chosen, send minimal event metadata rather than images unless there is a clear need, and make the external data transfer explicit.

Do not expose a raw camera dashboard or webhook port to the public internet. For remote access, use a properly secured VPN into the home network rather than unauthenticated port forwarding. A VPN still depends on an external network connection for off-site access.

## Privacy and reliability controls

- No default cloud upload; outbound integrations are disabled unless configured.
- Keep local storage access limited to the service account and trusted LAN clients.
- Use authentication, network segmentation, and an allowlist for webhook destinations.
- Add snapshot retention and disk-space alarms; avoid unlimited event storage.
- Apply cooldowns, motion zones, and confidence thresholds to reduce alert noise.
- Preserve error events locally when inference or delivery fails. Retry only bounded LAN delivery attempts, and avoid allowing a failed receiver to block frame capture.
- Make the recording indicator, retention policy, and camera field of view clear to household members and comply with applicable privacy laws.
