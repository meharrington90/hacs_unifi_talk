# HACS UniFi Talk

`hacs_unifi_talk` is a Home Assistant custom integration that configures the `ha-sip` add-on for a UniFi Talk third-party SIP extension, then exposes the call flow as Home Assistant services, entities, and events.

## Requirements

- Home Assistant OS or Home Assistant Supervised
- Home Assistant `2025.09.1` or newer
- The [`ha-sip` add-on](https://github.com/arnonym/ha-plugins) (`c7744bff_ha-sip`)
- A UniFi Talk third-party SIP extension

This integration depends on the Supervisor API. It will not work on Home Assistant Container or Core-only installs.
It does not bundle `ha-sip` and does not install it for you.

## Install

1. Install this repository through HACS as a custom integration, or copy `custom_components/hacs_unifi_talk` into your Home Assistant config.
2. Install the `ha-sip` add-on from `arnonym/ha-plugins`.
3. Restart Home Assistant.
4. Add `UniFi Talk (ha-sip)` from **Settings > Devices & Services**.

Only one config entry is supported.

## How It Works

- The config flow validates your inputs, writes `ha-sip` options through the Supervisor API, and restarts the add-on.
- The integration expects `ha-sip` to already be installed. If it is missing, setup stops with an `addon_missing` error.
- The integration registers a Home Assistant webhook for `ha-sip`.
- Incoming `ha-sip` webhook payloads are republished on the Home Assistant event bus as `hacs_unifi_talk_webhook`.
- Runtime call/session state is tracked by `internal_id` and stored across Home Assistant restarts.

## Configuration

Core setup is handled in the config flow and reconfigure flow. Notification defaults are handled in the integration options flow.

| Setting | Notes |
| --- | --- |
| SIP host / port / username / password / realm | UniFi Talk third-party SIP extension details. |
| `answer_mode` | Passed through to `ha-sip`. Allowed values: `listen` or `accept`. |
| `incoming_call_file` | Required when `answer_mode` is `accept`. |
| TTS engine / language / voice | Used by `play_message`, `announce`, and `answer_and_speak`. |
| `webhook_id` | Leave blank to auto-generate a Home Assistant webhook ID. |
| `cache_dir`, `name_server`, `global_options`, `sip_options` | Advanced `ha-sip` options. `--ice false` is always enforced in `sip_options`. |
| SSH password fetch | Optional. If enabled and the SIP password is blank, the integration will try to fetch it over SSH from the UniFi host. |
| Notify defaults | Default target, ring timeout, SIP account, and whether to hang up after speaking. |

If SSH password fetch is enabled, the integration runs:

```text
fs_cli -x 'user_data <extension>@talk.com param password'
```

against the configured SSH host.

## Entities

The integration creates one device and exposes these entities:

- `sensor` `Last Event`: latest webhook event plus summary attributes such as caller, menu, DTMF, message, and audio file
- `sensor` `Active Calls`: active call count with active and recent call snapshots
- `sensor` `Last Caller`: most recent caller plus last incoming call metadata
- `sensor` `Last DTMF Digit`: diagnostic sensor, disabled by default
- `binary_sensor` `Call In Progress`: on when at least one call is active
- `event` `Call Event`: emits supported call event types
- `notify` `Default Target`: available only when a default notification target is configured

## Events And Automation

The main automation surface is the Home Assistant event:

- `hacs_unifi_talk_webhook`

Supported event types:

- `incoming_call`
- `call_established`
- `entered_menu`
- `dtmf_digit`
- `playback_done`
- `ring_timeout`
- `timeout`
- `call_disconnected`

The fired Home Assistant event contains the original `ha-sip` payload plus normalized fields such as:

- `timestamp`
- `entry_id`
- `device_id`
- `internal_id`
- `caller`
- `parsed_caller`
- `digit`
- `menu_id`
- `sip_account`

Included examples:

- [Blueprint](blueprints/automation/hacs_unifi_talk/ha_sip_incoming_router.yaml)
- [Node-RED incoming router](nodered/flows_incoming_router.json)
- [Node-RED outbound TTS then hangup](nodered/flows_outbound_tts_then_hangup.json)
- [Node-RED send DTMF](nodered/flows_send_dtmf.json)

## Services

All services are exposed under the `hacs_unifi_talk` domain.

| Service | Purpose |
| --- | --- |
| `dial` | Place an outbound call through `ha-sip`. |
| `hangup` | Hang up an active call. |
| `send_dtmf` | Send DTMF digits to an active call. |
| `transfer` | Transfer a live call to another destination. |
| `bridge_audio` | Bridge audio between two live calls. |
| `play_message` | Speak a TTS message into an active call. |
| `play_audio_file` | Play an audio file into an active call. |
| `stop_playback` | Stop active TTS or audio playback. |
| `answer` | Answer an inbound call by `internal_id`. |
| `announce` | Dial, speak a TTS message, and optionally hang up after playback. |
| `answer_and_speak` | Answer an inbound call, speak a TTS message, and optionally hang up. |

Notes:

- `answer` and `answer_and_speak` expect the incoming call `internal_id` as `number`.
- Other call services accept an extension, phone number, `user@host`, or a full `sip:`, `sips:`, or `tel:` target.
- Simple targets are normalized against the configured SIP host before being sent to `ha-sip`.
- `announce` and `answer_and_speak` build the `ha-sip` menu payload for you.

## Notify Usage

Set a default target in the integration options, then call the notify entity with `notify.send_message`.

```yaml
action: notify.send_message
target:
  entity_id: notify.unifi_talk_default_target
data:
  title: Doorbell
  message: Someone is at the front door.
```

The actual notify entity ID may differ if you rename the integration or entity.

## Diagnostics

The integration includes redacted diagnostics for config, options, runtime summary, recent events, and tracked call sessions.

## Current Scope

This integration is still `ha-sip`-backed. It does not currently implement direct UniFi Talk API features such as:

- voicemail sync
- BLF or presence
- UniFi-native call logs
- recordings

## License

This project is licensed under the [MIT License](LICENSE).
