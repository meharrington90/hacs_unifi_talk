# ![logo](logo.png) HACS UniFi Talk (ha-sip)

Integrate your **UniFi Talk** SIP extension with the powerful **ha-sip** add-on to make and receive calls, play TTS or audio files, collect DTMF, route incoming calls by PIN, and wire the whole thing into Home Assistant Automations or **Node-RED**.

- One-click setup via Config Flow (Supervisor-aware).
- Writes the **ha-sip** add-on configuration for you (`sip_global`, `sip`, `tts`, `webhook`).
- Optional SSH to your UniFi Console to auto-fetch your SIP password from FreeSWITCH.
- First-class **services** for all call controls.
- A **sensor** that reflects the latest call state.
- A ready-to-use **automation blueprint** for routing incoming call events.
- Importable **Node-RED** flows.

> This integration **targets the ha-sip add-on** (`c7744bff_ha-sip`) from  
> **arnonym/ha-plugins**: https://github.com/arnonym/ha-plugins

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [How it works](#how-it-works)
- [Configuration (Config Flow fields)](#configuration-config-flow-fields)
- [Services](#services)
- [Examples](#examples)
- [Incoming events \& sensor](#incoming-events--sensor)
- [Automation blueprint](#automation-blueprint)
- [Node-RED flows (importable)](#node-red-flows-importable)
- [Troubleshooting](#troubleshooting)
- [Development \& CI](#development--ci)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Config Flow**
  - Validates `ha-sip` is installed and running (Supervisor API).
  - Sets `sip_global`, `sip`, `tts`, `webhook` in add-on options.
  - Restarts add-on to apply changes.
  - Optional SSH fetch of UniFi Talk SIP password:
    `fs_cli -x 'user_data <EXT>@talk.com param password'`.

- **Services** (wrappers over `hassio.addon_stdin`)
  - `hacs_unifi_talk.dial`
  - `hacs_unifi_talk.hangup`
  - `hacs_unifi_talk.send_dtmf`
  - `hacs_unifi_talk.transfer`
  - `hacs_unifi_talk.bridge_audio`
  - `hacs_unifi_talk.play_message`
  - `hacs_unifi_talk.play_audio_file`
  - `hacs_unifi_talk.stop_playback`
  - `hacs_unifi_talk.answer`

- **Webhook + Event fan-out**
  - Registers your webhook id and **fires** a HA event `hacs_unifi_talk_webhook`
    with the exact JSON from ha-sip (includes `event`, `parsed_caller`, `internal_id`, etc.).
  - Perfect for Node-RED’s **events: all** node.

- **Sensor**: `sensor.unifi_talk_last_call`
  - `state`: last event (`incoming_call`, `call_established`, `dtmf_digit`, `entered_menu`, `playback_done`, `ring_timeout`, `timeout`, `call_disconnected`)
  - `attributes`: `caller`, `parsed_caller`, `sip_account`, `internal_id`, `last_dtmf_digit`, `last_type`, `last_message`, `last_audio_file`, `updated`

- **Blueprint**: **ha-sip Incoming Call Router**
  - Input: your webhook id
  - Choose branches per `event` with editable action sequences.

---

## Requirements

- Home Assistant **OS** or **Supervised** (Supervisor API available).
- **ha-sip** add-on (`c7744bff_ha-sip`) installed (Repository: `https://github.com/arnonym/ha-plugins`).
- A UniFi Console with Talk and a **3rd-party SIP device** extension (your `username` / extension).

---

## Installation

1) **Install ha-sip add-on**
   - Settings → Add-ons → **Add-on Store** → ⋮ → *Repositories* → add `https://github.com/arnonym/ha-plugins`
   - Install **Home Assistant SIP/VoIP Gateway** (ha-sip) → **Start**.

2) **Install this Integration**
   - HACS → Integrations → **Custom Repositories**
     - URL: `https://github.com/meharrington90/hacs_unifi_talk` (Type: *Integration*)
   - Install → Restart HA if prompted.

3) **Add Integration**
   - Settings → Devices & Services → **Add Integration** → *HACS UniFi Talk (ha-sip)*
   - Fill the form (see next section) and **Submit**.  
     The integration validates the add-on, writes its options, and restarts it.

4. **Incoming call automations**
   - Use our **Blueprint** (below) or Node-RED flows (below).
   - Or create a Webhook Trigger automation with your webhook id and branch on `{{ trigger.json.event }}`.

---

## How it works
```
UniFi Talk (SIP) <---> ha-sip add-on <----> Home Assistant
↑ ↑
| (webhook JSON) | (services)
└───────────── HACS UniFi Talk integration
├─ wraps ha-sip commands as HA services
├─ registers a webhook id and re-emits events
└─ tracks live state in a sensor
```

- **Outbound**: You call `hacs_unifi_talk.*` services → integration sends `hassio.addon_stdin` to **ha-sip**.
- **Inbound**: ha-sip posts to your **webhook id** → integration (a) updates the sensor, (b) re-emits the payload as a HA event `hacs_unifi_talk_webhook` for Automations/Node-RED.

---

## Configuration (Config Flow fields)

| Field | Default | Notes |
|------|---------|------|
| **SIP host** | `192.168.1.1` | Your UniFi Talk IP/DNS |
| **SIP port** | `5060` | Port for SIP |
| **Username** | `0001` | Your UniFi Talk **extension** |
| **Password** | *(blank)* | Must obtain from Unifi Host |
| **Realm** | `*` | SIP realm |
| **Answer mode** | `listen` | `listen` or `accept` |
| **Settle time** | `1` | Seconds after connect before playing |
| **Incoming call file** | *(blank)* | e.g. `/config/sip-1-incoming.yaml` |
| **TTS engine entity** | `tts.home_assistant_cloud` | Any HA TTS entity id |
| **TTS language** | `en` | e.g. `en` or `en-US` |
| **TTS voice** | *(blank)* | If supported by engine |
| **TTS debug print** | `false` | Logs available engines/voices |
| **Webhook id** | *(auto)* | Leave empty to auto-generate |
| **Cache dir** | `/config/audio_cache` | Must exist |
| **Name server** | *(blank)* | Comma-separated list, for SRV |
| **Global options** | *(blank)* | Advanced ha-sip CLI flags |
| **SIP options** | *(blank)* | Advanced per-account flags |
| **Enable SSH** | `false` | Fetch SIP password from UniFi |
| **SSH host/port/user/password** | – | For password fetch via FreeSWITCH |

> On submit, the integration writes the ha-sip options (`sip_global`, `sip`, `tts`, `webhook`) and **restarts** the add-on.

---

## Services

The integration normalizes simple numbers like `**620` or `+1800…` to SIP URIs  
`sip:**620@<sip_host>` / `sip:+1800…@<sip_host>`.

| Service | Purpose | Key fields |
|---|---|---|
| `hacs_unifi_talk.dial` | Place a call (optionally speak a message / present a menu) | `number`, `ring_timeout`, `sip_account`, `menu`, `webhook_to_call` |
| `hacs_unifi_talk.hangup` | Hang up an active call | `number` |
| `hacs_unifi_talk.send_dtmf` | Send DTMF to active call | `number`, `digits`, `method` (`in_band`/`rfc2833`/`sip_info`) |
| `hacs_unifi_talk.transfer` | Transfer a call | `number`, `transfer_to` |
| `hacs_unifi_talk.bridge_audio` | Bridge two calls’ audio | `number`, `bridge_to` |
| `hacs_unifi_talk.play_message` | TTS to call | `number`, `message`, `tts_language?`, `cache_audio?`, `wait_for_audio_to_finish?` |
| `hacs_unifi_talk.play_audio_file` | Play a file | `number`, `audio_file`, `cache_audio?`, `wait_for_audio_to_finish?` |
| `hacs_unifi_talk.stop_playback` | Stop TTS/audio playback | `number` |
| `hacs_unifi_talk.answer` | Answer by **internal id** | `number [internal id]`, `menu?`, `webhook_to_call?` |

## Examples:

> The integration normalizes plain numbers like `**620` or `+1800…` into SIP URIs
> `sip:**620@<sip_host>` / `sip:+1800…@<sip_host>`.

- **Dial with TTS message**
```
{
  service: hacs_unifi_talk.dial
  data:
    number: "+18008675309"
    ring_timeout: 15
    menu:
      message: "There is a silent alarm. Mode: {{ states('alarm_control_panel.home_alarm') }}."
}
```

- **Hangup**
```
{
  service: hacs_unifi_talk.hangup
  data:
    number: "+18008675309"
}
```

- **Send DTMF**
```
{
  service: hacs_unifi_talk.send_dtmf
  data:
    number: "**620"
    digits: "#5"
    method: in_band
}
```

- **Play audio file**
```
{
  service: hacs_unifi_talk.play_audio_file
  data:
    number: "+18008675309"
    audio_file: "/config/audio/welcome.mp3"
    wait_for_audio_to_finish: true
}
```

- **Answer incoming by internal id**
```
{
  service: hacs_unifi_talk.answer
  data:
    number: "{{ trigger.json.internal_id }}"
    menu:
      message: "Please enter your access code."
      choices_are_pin: true
      choices:
        "1234":
          message: "Welcome."
          post_action: hangup
        "default":
          message: "Wrong code."
          post_action: return
}
```

---

## Node-RED flows (importable)

Flows are located in the "nodered" folder. These flows use the Node-RED **Home Assistant add-on**.  
Import via **Node-RED → menu → Import**.

> The flows listen to the HA event **`hacs_unifi_talk_webhook`** (node type: *events: all* with `event_type` set).

### A) Incoming Router (route by event)
**File**: `flows_incoming_router.json`

### B) Outbound: dial with TTS, then hangup after delay
**File**: 'flows_outbound_tts_then_hangup.json'

### C) Send DTMF to active call
**File**: 'flows_send_dtmf.json'

---

## Troubleshooting
- **ha-sip not found**: Ensure the add-on is installed and started. The slug must be c7744bff_ha-sip.
- **No audio / TTS**: Verify your tts_engine_id, language/voice, and that /config/audio_cache exists (if caching).
- **No incoming events**: Confirm your webhook id in the integration matches the add-on config, and that the integration is loaded (check Logs).
- **Node-RED not reacting**: The events: all node must filter event_type = hacs_unifi_talk_webhook.

---

## Development & CI
This repo includes GitHub Actions for:
- **HACS validation** (`.github/workflows/hacs.yml`)
- **hassfest** (`.github/workflows/hassfest.yml`)
Run-time stack:
- **Integration domain**: `hacs_unifi_talk`
- **Add-on slug target**: `c7744bff_ha-sip`
- **Python dep**: `paramiko` (for optional SSH)

---

## Roadmap
- Initial public examples (blueprint + form package)
- Validation and guardrails for inputs
- Optional confirmation prompts before call invocation
- Documentation with screenshots and sample automations

---

## Status
Pre-release design. Implementation details and examples will be added with the first version tag.

---

## Contributing
- Open **Issues** for bugs/feature requests
- Use **Discussions** for design proposals
- PRs welcome!!

**Links:** [Issues](#) · [Discussions](#) · [Changelog](#)

---

## License
This software is released under the MIT License (© Mike Harrington).
