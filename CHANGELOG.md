# Changelog

All notable changes to **HACS UniFi Talk (ha-sip)** will be documented here.

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
- Requires Home Assistant OS / Supervised (Supervisor API).
- Requires the **ha-sip** add-on (`c7744bff_ha-sip`) from https://github.com/arnonym/ha-plugins.
