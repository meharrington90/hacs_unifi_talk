# Unifi Talk VoIP Call Features for Home Assistant
Declarative call profiles and an ad-hoc form to trigger TTS phone calls via `hassio.addon_stdin`.

---

## Overview
This project provides a lightweight pattern for defining reusable “call profiles” and an optional dashboard form in Home Assistant. Profiles and the form assemble a message from static text plus live entity state (e.g., alarm mode, open sensors) and invoke a VoIP add-on over Supervisor stdin.

**Key intent:** make outbound TTS calls first-class automation targets without bespoke YAML per use case.

---

## Goals
- **Reusability:** Create named call profiles (script instances) with clear inputs.
- **Composability:** Reference live HA entities/attributes in messages.
- **Operator UX:** Provide an optional dashboard form for one-off calls.
- **Minimal coupling:** Treat the VoIP stack as an external add-on invoked via stdin.

**Non-goals:** shipping a SIP stack, emergency calling, call routing logic.

---

## Features
- **Profiled Calls:** Script blueprint with inputs such as:
  - Destination (`E.164`), SIP host/port, add-on slug
  - `intro_phrase`, `call_reason`, `callback_number`, `extra_context`
  - Optional full `message_template` override
  - Context sources: alarm entity, include/exclude sensor lists, area scoping, device_class filters, `open_only`
- **Ad-Hoc Form:** Dashboard helpers + script to submit one-off calls with the same message assembly logic.
- **Context Expansion:** Precomputed variables (e.g., `arm_mode`, `open_sensors`, `callback_number_spoken`) for use in messages.
- **HA-Native:** Works with Scripts, Dashboards, and Automations. No custom component required.

---

## How It Works (high level)
```
[Dashboard Button / Automation / Script]
           │
           ▼
   Profile / Form collects inputs
           │
           ▼
  Message assembly (Jinja + entity state)
           │
           ▼
hassio.addon_stdin → VoIP Add-on (TTS → call)
```

- **Invocation:** `hassio.addon_stdin` with `input: { call_sip_uri, message_tts }`.
- **Message:** Built from profile/form inputs and optional entity-derived context.
- **Context:** Filtered binary_sensors by `device_class`, `area`, and state; optional alarm entity.

---

## Typical Use Cases
- Operator-triggered welfare check or notification call
- Automation-driven outbound call based on alarm/door states
- Quick one-off calls from a dashboard form during incidents

---

## Architecture Notes
- **Execution:** HA Script / Script Blueprint; optional Lovelace entities for the form.
- **Boundary:** VoIP/TTS is delegated to an existing Supervisor add-on (e.g., custom DSS VoIP).
- **Compatibility:** Requires **Home Assistant OS/Supervised** (Supervisor API access).
- **Idempotence:** Scripts are stateless; message content is derived at runtime.

---

## Configuration Model (conceptual)
- **Profiles (Blueprint instances):**
  - *Connectivity:* `addon_slug`, `phone_number`, `sip_host`, `sip_port`
  - *Message inputs:* `intro_phrase`, `call_reason`, `callback_number`, `extra_context`
  - *Context inputs:* `alarm_entity`, `include_entities`, `exclude_entities`, `area_scope`,
    `include_device_classes[]`, `open_only`
  - *Override:* `message_template` (optional full template)
- **Form (Dashboard):**
  - Mirrors the above as `input_text` / `input_number` / `input_boolean` helpers plus a single “Send” script.

> Exact YAML and UI examples will be added when the first tagged release is published.

---

## Security & Privacy
- Treat phone numbers and messages as sensitive config.
- Be aware of local regulations regarding automated calls and recorded messages.
- This project is **not** an emergency service.

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
- PRs welcome once the initial structure lands

**Links (TBD):** [Issues](#) · [Discussions](#) · [Changelog](#)

---

## License
To be defined at first release.
