# HACS UniFi Talk

`hacs_unifi_talk` is a Home Assistant custom integration that bridges a UniFi Talk third-party SIP extension into Home Assistant by configuring and driving the `ha-sip` add-on.

It gives you:

- A config flow that writes `ha-sip` options for you
- Home Assistant services for dialing, DTMF, transfer, playback, and answer
- A sensor that exposes the latest call state
- A Home Assistant event stream for automations and Node-RED
- An event-router blueprint to branch call flows by event type

## Status

This repository is now at a reasonable starter baseline for a real Home Assistant integration, but it is still an early project. The integration currently assumes:

- Home Assistant OS or Supervised
- The Supervisor API is available
- The `ha-sip` add-on is installed from [arnonym/ha-plugins](https://github.com/arnonym/ha-plugins)
- You have a UniFi Talk third-party SIP extension with credentials

## Architecture

```text
UniFi Talk <-> ha-sip add-on <-> Home Assistant
                              |
                              +-> hacs_unifi_talk services
                              +-> hacs_unifi_talk_webhook event
                              +-> sensor.last_call state
```

The integration owns the inbound webhook used by `ha-sip`. It then republishes those payloads inside Home Assistant as the `hacs_unifi_talk_webhook` event. That event is the supported automation surface.

## Installation

1. Install the `ha-sip` add-on from [arnonym/ha-plugins](https://github.com/arnonym/ha-plugins).
2. Install this repository as a HACS custom integration.
3. Add the integration from Settings -> Devices & Services.
4. Fill in your UniFi Talk SIP extension details.

## Configuration Notes

- `sip_options` automatically keeps `--ice false` because UniFi Talk generally needs it.
- If `answer_mode` is `accept`, you must provide an incoming call file.
- If you leave the webhook ID blank, the integration generates one.
- Optional SSH password retrieval uses `fs_cli` on the UniFi host and requires the UniFi SSH password.

## Services

The integration exposes these services under `hacs_unifi_talk`:

- `dial`
- `hangup`
- `send_dtmf`
- `transfer`
- `bridge_audio`
- `play_message`
- `play_audio_file`
- `stop_playback`
- `answer`

Plain values like `8008675309`, `+18005551212`, or `**620` are normalized into SIP URIs automatically. Full `sip:` URIs are passed through unchanged.

## Events

Inbound call and playback events are fired on the Home Assistant bus as:

- `hacs_unifi_talk_webhook`

The event payload mirrors the JSON received from `ha-sip`. Typical keys include:

- `event`
- `caller`
- `parsed_caller`
- `sip_account`
- `internal_id`
- `digit`
- `message`
- `audio_file`

This is what automations and Node-RED should listen to. Do not bind your own automation to the same webhook ID that the integration uses internally.

## Sensor

The integration creates a sensor representing the latest call state. Its state is the latest event name, and attributes include caller details, internal call ID, last DTMF digit, playback metadata, and last update time.

## Blueprint

[`blueprints/automation/hacs_unifi_talk/ha_sip_incoming_router.yaml`](/Users/meharrington/Github/hacs_unifi_talk/blueprints/automation/hacs_unifi_talk/ha_sip_incoming_router.yaml) routes the `hacs_unifi_talk_webhook` event into separate automation branches for:

- `incoming_call`
- `call_established`
- `entered_menu`
- `dtmf_digit`
- `playback_done`
- `ring_timeout`
- `timeout`
- `call_disconnected`

## Node-RED

The example flows in [`nodered`](/Users/meharrington/Github/hacs_unifi_talk/nodered) should subscribe to the Home Assistant event `hacs_unifi_talk_webhook`, not to the raw webhook endpoint.

## Development

Current repository baseline improvements:

- Shared config normalization and add-on option building
- Proper service lifecycle registration
- Runtime state storage per config entry
- Webhook handling with Home Assistant event fan-out
- Real translation file support via `translations/en.json`
- Cleaner service documentation and blueprint behavior
- Basic CI scaffolding for static validation

## Recommended Next Steps

To move from a starter integration to something closer to Home Assistant best practice, the next high-value work is:

1. Add automated tests for config flow, webhook handling, and service payload generation.
2. Add diagnostics support so users can export redacted config/runtime state for bug reports.
3. Add repair flows or clear error surfaces for missing Supervisor, missing `ha-sip`, and failed add-on restarts.
4. Decide whether this should stay a thin `ha-sip` bridge or grow toward direct UniFi Talk API integration later.

## License

MIT
