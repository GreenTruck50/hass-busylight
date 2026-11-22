<p align="center">
  <img src="https://raw.githubusercontent.com/JnyJny/busylight/main/packages/busylight/assets/BusyLightForHumans.png" alt="Busylight for Humans logo" width="500">
</p>

# Home Assistant – Busylight for Humans

Custom integration that turns a [Busylight for Humans](https://github.com/JnyJny/busylight) Web API server (`busyserve`) into proper Home Assistant devices and RGB light entities with effects.

## Features

- **Config flow** – add a Busylight host (IP/hostname + port, optional Basic Auth)
- **One device per `busyserve` host**, carrying a **Health** connectivity binary sensor (`status`, `lights_available`, `timestamp`)
- **One device per physical light** discovered on that host, each with an **RGB light entity** and brightness (`dim` 0.0–1.0)
- **Effects** exposed natively on the light entity — every animated effect is offered in three speeds:

  | Effect | Names in the effect picker | Behaviour |
  |--------|----------------------------|-----------|
  | `off` | `off` | Solid color — whatever RGB color is set on the entity |
  | `blink` | `blink slow` · `blink medium` · `blink fast` | Blinks in the selected color |
  | `rainbow` | `rainbow slow` · `rainbow medium` · `rainbow fast` | Cycles through the color spectrum |
  | `pulse` | `pulse slow` · `pulse medium` · `pulse fast` | Breathing / pulsing in the selected color |
  | `Police Flash (fli)` | `Police Flash (fli) slow` · `Police Flash (fli) medium` · `Police Flash (fli) fast` | FLI ("GetFlashyIndication") — alternates **red ↔ blue** |

- Uses the modern `/api/v1/` endpoints exclusively — even **Police Flash (fli)** goes through the v1 flash route, no deprecated compatibility endpoints
- Local polling coordinator – default every 10 s, configurable from 5 to 300 s in the integration options
- HACS-ready

## Requirements

1. A machine with USB [Busylight-compatible](https://jnyjny.github.io/busylight/devices/) lights attached.
2. [Busylight for Humans](https://github.com/JnyJny/busylight) installed with the Web API extra:

   ```bash
   pip install "busylight-for-humans[webapi]"
   busyserve --host 0.0.0.0 --port 8000
   ```

   On Linux you also need the udev rules ([see upstream docs](https://jnyjny.github.io/busylight/installation/#linux-udev-rules)).

   To protect the API with Basic Auth, start `busyserve` with the upstream environment variables set, otherwise leave the username/password fields empty:

   ```bash
   export BUSYLIGHT_API_USER="admin"
   export BUSYLIGHT_API_PASS="secret"
   busyserve --host 0.0.0.0 --port 8000
   ```

3. Home Assistant that can reach the `busyserve` host on the network.

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS (Integration).
2. Search for “Busylight for Humans” and install.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for **Busylight for Humans**.

### Manual

1. Copy the `custom_components/busylight` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via the UI.

## Configuration

| Field     | Required | Default | Description                          |
|-----------|----------|---------|--------------------------------------|
| Host      | yes      | –       | IP or hostname of the `busyserve` machine |
| Port      | no       | 8000    | Port the API is listening on         |
| Username  | no       | –       | Optional HTTP Basic Auth user        |
| Password  | no       | –       | Optional HTTP Basic Auth password    |

After adding the host, Home Assistant creates a `Busylight (<host>)` device with the **Health** sensor, plus one device with an RGB light entity for every light reported by `GET /api/v1/lights`.

## Usage

- Turn the light on/off and set an RGB color + brightness from the normal light card or via the `light.turn_on` / `light.turn_off` services.
- Pick an effect — including its speed — from the effect list on the light entity, or call the service directly:

  ```yaml
  action: light.turn_on
  target:
    entity_id: light.desk_0
  data:
    effect: "pulse fast"
    brightness: 200
  ```

- **Police Flash (fli)** always alternates **red ↔ blue**; the selected RGB color is ignored while it runs. The colored effects (`blink`, `pulse`) use the entity's RGB color.
- Changing brightness or color while an effect is running re-applies that effect (handy for dimming it). Select `off` in the effect list to return to a solid color.
- Effect matching is case-insensitive, names without a speed (`effect: "rainbow"`) default to `medium`, and the older spellings (`"fli"`, `"fli fast"`) keep working even though the picker shows **Police Flash (fli)**.
- The integration polls the API every 10 s by default; change it to anything from 5 to 300 seconds in the integration's **Configure** dialog.

## Supported API surface

Endpoints the integration calls:

- `GET /api/v1/system/health` – feeds the Health binary sensor
- `GET /api/v1/lights` – device discovery and state polling
- `POST /api/v1/lights/{id}/on` – solid color (`color` as hex, `dim` 0.0–1.0, `led`)
- `POST /api/v1/lights/{id}/off`
- `POST /api/v1/lights/{id}/blink` – `color`, `dim`, `speed`, `count`, `led`
- `POST /api/v1/effects/{id}/rainbow` – `dim`, `speed`, `led`
- `POST /api/v1/effects/{id}/pulse` – `color`, `dim`, `speed`, `count`, `led`
- `POST /api/v1/effects/{id}/flash` – used for **Police Flash (fli)**: `color_a: "red"`, `color_b: "blue"`, `dim`, `speed`, `count`, `led`

`speed` is always one of `slow`, `medium` or `fast` and comes from the effect name chosen in Home Assistant. The deprecated compatibility routes (`GET /light/{id}/fli`, `/light/{id}/on`, …) are never called. `GET /api/v1/lights/{id}/status` is implemented in the API client but is not used for polling — the coordinator refreshes every light with a single `GET /api/v1/lights` call.

## Brand assets

Since Home Assistant **2026.3**, a custom integration ships its own brand images: a `brand/` folder inside the integration. No upstream submission, no manifest key.

```
custom_components/busylight/brand/
├── icon.png        icon@2x.png          <- 256 px / 512 px, light themes
├── dark_icon.png   dark_icon@2x.png     <- 256 px / 512 px, dark themes
├── logo.png        logo@2x.png
└── dark_logo.png   dark_logo@2x.png
```

Only those eight file names are recognised. Local images automatically take priority over the `brands.home-assistant.io` CDN, and Home Assistant serves them through its own proxy (`/api/brands/integration/busylight/<image>`, cached on disk), so the icon appears in the integrations dashboard, config flow and devices even without internet.

The wordmark is supplied in two colourways on full transparency — white + green for dark themes, dark ink + **the same green** for light themes (the source art is white-on-black, so the background was keyed out rather than left opaque, and the green accent is never re-tinted).

HACS requires this as well: its **Check brands** validation wants a `brand` directory containing at least an `icon.png`, which is what lets the repository be accepted into the HACS / Marketplace defaults.

The root [`logo.png`](logo.png) is the 1024×1024 master artwork; it is used for the banner above and works well as the GitHub social-preview image, and it is not part of the installed integration.

> There is no `images/` convention in Home Assistant or HACS — that folder name is only a repo-local habit for README screenshots. Brand images belong in `brand/`. Submitting to [home-assistant/brands](https://github.com/home-assistant/brands) (`custom_integrations/busylight/icon.png` + `icon@2x.png`, sized 128–256 px and 256–512 px) is now optional: it only helps installs older than 2026.3, and your local files win regardless.

## Development / Contributing

PRs welcome. Please keep the integration compatible with current Home Assistant quality guidelines — every push, PR and nightly run is checked by [hassfest](.github/workflows/hassfest.yml).

## License

This project is licensed under the **GNU General Public License v3.0** (GPLv3).
See the [LICENSE](LICENSE) file for the full text.

## Credits

- Upstream project: [JnyJny/busylight](https://github.com/JnyJny/busylight)
- Web API docs: https://jnyjny.github.io/busylight/api/
