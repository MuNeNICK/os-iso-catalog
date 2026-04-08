# OS ISO Catalog

Machine-readable catalog of OS ISO images with download URLs, checksums, and EOL dates.

Served as static JSON via GitHub Pages. Updated daily via GitHub Actions.

[![Daily Checks](https://github.com/MuNeNICK/os-iso-catalog/actions/workflows/daily-check.yml/badge.svg)](https://github.com/MuNeNICK/os-iso-catalog/actions/workflows/daily-check.yml)

## Web UI

Browse the catalog with filtering, search, and EOL status at a glance:

- **Dashboard**: https://munenick.github.io/os-iso-catalog/
- **API Docs (Swagger)**: https://munenick.github.io/os-iso-catalog/api.html

<img width="1267" height="993" alt="image" src="https://github.com/user-attachments/assets/8865f535-4fda-4df5-9c8e-982db8219dc8" />


## API Endpoints

Base URL: `https://MuNeNICK.github.io/os-iso-catalog`

| Endpoint | Description |
|----------|-------------|
| `/v1/all.json` | All OS images |
| `/v1/supported.json` | Currently supported only |
| `/v1/eol.json` | End-of-life archive |
| `/v1/linux.json` | Linux distributions |
| `/v1/windows.json` | Windows images |
| `/v1/bsd.json` | BSD family |
| `/v1/amd64.json` | amd64/x86_64 images |
| `/v1/arm64.json` | arm64/aarch64 images |

## Quick Start

```bash
# Get all supported Linux images
curl -s https://MuNeNICK.github.io/os-iso-catalog/v1/supported.json \
  | jq '.images[] | select(.category == "linux") | {name, url}'
```

## Coverage

- **Linux**: Ubuntu, Kubuntu, Xubuntu, Debian, Fedora, Rocky Linux, AlmaLinux, CentOS Stream, openSUSE (Leap/Tumbleweed), Linux Mint, Arch, Manjaro, Kali, Alpine, Gentoo, Oracle Linux, Raspberry Pi OS, MX Linux, Pop!_OS, CachyOS, EndeavourOS, NixOS, Slackware, Tails, Qubes OS, Zorin OS, Omarchy
- **Windows**: Windows 11, 10, Server 2025/2022/2019
- **BSD**: FreeBSD, OpenBSD, NetBSD

All currently supported versions are tracked.

## How It Works

1. `data/images.yaml` is the single source of truth
2. `scripts/generate.py` transforms YAML into filtered JSON endpoints under `docs/v1/`
3. GitHub Pages serves the `docs/` directory
4. **Daily at 06:00 UTC**, GitHub Actions:
   - Fetches EOL dates from [endoflife.date](https://endoflife.date/) API and auto-updates `status` field
   - Validates all download URLs are reachable
   - Detects new OS releases and creates GitHub Issues
   - Creates GitHub Issues for broken links

## Contributing

1. Edit `data/images.yaml`
2. Run `python scripts/generate.py` to verify
3. Submit a PR

### Adding a new image

```yaml
- id: distro-version-edition
  name: "Distro Name Version"
  category: linux          # linux | windows | bsd
  distro: distro-slug
  version: "1.0"
  arch: amd64
  release_type: stable     # stable | beta | rolling
  url: https://example.com/distro.iso
  checksum:
    algorithm: sha256
    value: "abc123..."
  eol:
    standard: "2030-01-01"
    extended: null
    is_rolling: false
  status: supported        # supported | eol | eol-extended | beta
```

## Acknowledgments

- [endoflife.date](https://endoflife.date/) — EOL date data and new release detection

## License

MIT
