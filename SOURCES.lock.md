# Source lock

Changing a baseline requires a recorded architecture decision.

## NVIDIA open GPU kernel modules

| Role | Revision | Commit | Advertised fork ref |
|---|---|---|---|
| Pre-change control | `590.48.01` | `2ccbad25e1af6a6ee6f38cf569f89f8b65d658ab` | `source/nvidia-590.48.01` |
| First known non-stub source | `595.44.02` | `2c7bfb47060233bda7c37c8065c0ddcac0d3da05` | `source/nvidia-595.44.02` |
| Primary baseline | `610.57.04` | `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb` | `main` |

Repository: `https://github.com/NVIDIA/open-gpu-kernel-modules`

The two `source/nvidia-*` branches exist only to make otherwise unadvertised historical snapshot objects reproducibly fetchable in clean CI checkouts. They must remain pinned to the exact commits above and must not receive development commits.

## Chromium

- Repository: `https://github.com/chromium/chromium`
- Seed commit: `8086bb60f151aad53b2a76fbaeeebf6855ea2c4c`
- Purpose: Windows PlayReady/Media Foundation reference

## Wine

- Repository: `https://github.com/wine-mirror/wine`
- Seed commit: `e99fc2f7587db7bc186293e9949fe0d3695cd430`
- Purpose: PMP, Media Foundation, and D3D11 protected-video gap map

## Linux DRM/KMS and IGT

Exact kernel and IGT revisions remain `UNPINNED` until the native target is inventoried. Pin them before using them as pass/fail authorities.

## Verification

```bash
scripts/verify-source-transition.sh artifacts/source-transition
python3 scripts/check-research-metadata.py
```
