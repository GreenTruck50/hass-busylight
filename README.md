# Home Assistant – Busylight for Humans

Custom integration that turns a [Busylight for Humans](https://github.com/JnyJny/busylight) Web API server (`busyserve`) into proper Home Assistant devices and RGB light entities with effects.

## Features

- **Config flow** – add a Busylight host (IP/hostname + port, optional Basic Auth)
- **One HA device per physical light** discovered on the host
- **RGB light entity** per device with brightness
- **Effects** exposed natively via the light entity:
  - `off` (solid color)
  - `blink`
  - `rainbow`
  - `pulse`
  - `flash`
- Uses the modern `/api/v1/` endpoints
- Local polling coordinator
- HACS-ready

## Requirements

1. A machine with USB [Busylight-compatible](https://jnyjny.github.io/busylight/devices/) lights attached.
2. [Busylight for Humans](https://github.com/JnyJny/busylight) installed with the Web API extra:

   ```bash
   pip install "busylight-for-humans[webapi]"
   busyserve --host 0.0.0.0 --port 8000
   ```

   On Linux you also need the udev rules ([see upstream docs](https://jnyjny.github.io/busylight/installation/#linux-udev-rules)).

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

After adding the host, every light reported by `GET /api/v1/lights` appears as its own device with an RGB light entity.

## Usage

- Turn the light on/off and set RGB color + brightness from the normal light card or services.
- Choose an effect from the effect list on the light entity (or via `light.turn_on` with `effect:`).
- The integration polls the API (default every 10 s; changeable in the integration options).

## Supported API surface

The integration uses these endpoints:

- `GET /api/v1/system/health`
- `GET /api/v1/lights`
- `GET /api/v1/lights/{id}/status`
- `POST /api/v1/lights/{id}/on`
- `POST /api/v1/lights/{id}/off`
- `POST /api/v1/lights/{id}/blink`
- `POST /api/v1/effects/{id}/rainbow`
- `POST /api/v1/effects/{id}/pulse`
- `POST /api/v1/effects/{id}/flash`

## Development / Contributing

PRs welcome. Please keep the integration compatible with current Home Assistant quality guidelines.

## License

This project is licensed under the **GNU General Public License v3.0** (GPLv3).
See the [LICENSE](LICENSE) file for the full text.

## Credits

- Upstream project: [JnyJny/busylight](https://github.com/JnyJny/busylight)
- Web API docs: https://jnyjny.github.io/busylight/api/
