# HACS UniFi Talk

`hacs_unifi_talk` turns a UniFi Talk third-party SIP extension into a more native Home Assistant automation surface by configuring and driving the `ha-sip` add-on.

## What it does

- Configures the `ha-sip` add-on from a Home Assistant config flow
- Exposes call-control actions for dial, answer, DTMF, transfer, bridging, playback, and hangup
- Adds higher-level actions for `announce` and `answer_and_speak`
- Tracks active and recent call sessions instead of only one last event
- Persists recent call history and summary state across Home Assistant restarts
- Publishes `hacs_unifi_talk_webhook` on the Home Assistant event bus
- Exposes sensors and a binary sensor for last event, active calls, call-in-progress state, last caller, and last DTMF digit
- Exposes an event entity for call events
- Exposes a notify entity for a configured default target
- Supports reconfigure and diagnostics

## Requirements

- Home Assistant OS or Supervised
- The `ha-sip` add-on from [arnonym/ha-plugins](https://github.com/arnonym/ha-plugins)
- A UniFi Talk third-party SIP extension

## Automation Surface

The integration owns the inbound `ha-sip` webhook and republishes those payloads as the Home Assistant event:

- `hacs_unifi_talk_webhook`

That event is the supported trigger surface for automations, blueprints, and Node-RED.

## Main Features Added

### Session tracking

Webhook events are now folded into a live in-memory call/session model keyed by `internal_id`. The integration tracks:

- direction
- state
- caller and parsed caller
- SIP account
- entered menu ID
- last DTMF digit
- last playback metadata
- timestamps for create, establish, disconnect, and update

### Home Assistant entities

The integration now provides:

- call summary sensors
- a binary sensor for call-in-progress automations
- a call event entity
- a notify entity for a default UniFi Talk target

### Higher-level actions

In addition to the raw `ha-sip` wrappers, the integration now includes:

- `hacs_unifi_talk.announce`
- `hacs_unifi_talk.answer_and_speak`

These are easier to use for common automation tasks like alert calls, door/intercom flows, and spoken notifications.

### Better configuration lifecycle

- Config flow writes validated add-on options
- Reconfigure flow updates setup data without removing the integration
- Options flow handles notification defaults
- Diagnostics export redacted runtime and config data
- Runtime call history survives restarts using Home Assistant storage

## Services

Core actions:

- `dial`
- `hangup`
- `send_dtmf`
- `transfer`
- `bridge_audio`
- `play_message`
- `play_audio_file`
- `stop_playback`
- `answer`

Higher-level actions:

- `announce`
- `answer_and_speak`

## Notify usage

Set a default target in the integration settings, then target the notify entity with `notify.send_message`. The integration will place the call, speak the message, and optionally hang up afterward.

## Blueprint

[`blueprints/automation/hacs_unifi_talk/ha_sip_incoming_router.yaml`](/Users/meharrington/Github/hacs_unifi_talk/blueprints/automation/hacs_unifi_talk/ha_sip_incoming_router.yaml) routes the `hacs_unifi_talk_webhook` event by event type.

## Current Scope

This is still primarily a `ha-sip`-backed integration. It does not yet implement direct UniFi Talk metadata features like voicemail sync, BLF presence, call logs, or recordings from UniFi itself.

## Next High-Value Work

1. Add automated tests.
2. Add repairs for missing Supervisor or missing `ha-sip`.
3. Add direct device triggers for common call events.
4. Explore direct UniFi Talk metadata integration for voicemail, logs, presence, and recordings.
