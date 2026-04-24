# Changelog

All notable changes to **HACS UniFi Talk (ha-sip)** will be documented here.

## [Unreleased]
### Added
- `translations/en.json` so the config and options flows use proper Home Assistant translation files.
- Basic GitHub Actions workflows for HACS validation and static checks.
- `pyproject.toml` with Ruff configuration.
- Additional Home Assistant surfaces:
  - `event` entity for webhook-backed call events
  - `notify` entity for a configured default call target
  - richer call summary sensors
- High-level actions:
  - `hacs_unifi_talk.announce`
  - `hacs_unifi_talk.answer_and_speak`
- Redacted diagnostics export.
- Reconfigure flow support.

### Changed
- Refactored integration setup so services are registered once, config/options are merged consistently, and runtime state is tracked per config entry.
- Fixed webhook handling to update the sensor and republish payloads as the `hacs_unifi_talk_webhook` event.
- Reworked the blueprint to listen for Home Assistant events instead of trying to reuse the integration's webhook ID.
- Improved Supervisor API handling and add-on option generation.
- Updated documentation and service descriptions to reflect the actual supported flow.
- Replaced the single "last call" state model with active/recent call session tracking keyed by `internal_id`.

## [2025.9.0] - 2025-09-17
### Added
- Initial public release.
- Config Flow that:
  - Checks `ha-sip` add-on (`c7744bff_ha-sip`) is installed and reachable.
  - Optionally fetches UniFi Talk SIP password via SSH (`fs_cli user_data <ext>@talk.com param password`).
  - Writes add-on options (`sip_global`, `sip`, `tts`, `webhook`) and restarts the add-on.
- Wrapper services around `ha-sip` commands:
  - `hacs_unifi_talk.dial`, `hangup`, `send_dtmf`, `transfer`, `bridge_audio`,
    `play_message`, `play_audio_file`, `stop_playback`, `answer`.
- Webhook integration:
  - Registers the configured webhook id and forwards all incoming payloads to HA as events
    (`hacs_unifi_talk_webhook`) for easy automation and Node-RED routing.
- **Sensor**: `sensor.unifi_talk_last_call` tracking last event / caller / internal_id / last DTMF digit.
- **Automation blueprint**: “ha-sip Incoming Call Router” to branch logic by `event`
  (`incoming_call`, `call_established`, `dtmf_digit`, `entered_menu`, `playback_done`,
  `ring_timeout`, `timeout`, `call_disconnected`).
- Node-RED example flows (importable) for incoming routing, outbound dialing, DTMF, audio/tts, hangup.

### Changed
- Integration domain finalized to `hacs_unifi_talk` and repo path updated to
  `github.com/meharrington90/hacs_unifi_talk`.

### Notes
- REQUIRED: Home Assistant OS / Supervised (Supervisor API).
- REQUIRED: The **ha-sip** add-on (`c7744bff_ha-sip`) from https://github.com/arnonym/ha-plugins.
