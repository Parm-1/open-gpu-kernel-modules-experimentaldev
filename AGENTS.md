# Project instructions

This fork is governed by `CHARTER.md`.

## Non-negotiable rules

- Preserve NVIDIA `main` as an upstream snapshot. Develop on narrow branches.
- Use the exact state names in `docs/security-state-model.md`.
- Do not attach KMS content-protection properties until the backend is truthful and fail-closed.
- Do not fabricate successful HDCP, PMP, D3D11, PlayReady, Widevine, or service states.
- Never collect production keys, certificates, license bodies, decrypted samples, or proprietary binaries.
- Keep DisplayPort SST, HDMI, MST, protected memory, protected decode, Wine, browser integration, and vendor authorization as separate evidence tracks.
- One concept per commit. Every experiment gets a manifest, commands, stdout, stderr, artifact hashes, and a verdict.
- Source work and builds are allowed. Loading experimental GPU modules, changing boot configuration, or rebooting requires explicit approval and a verified rollback path.
- Do not publish upstream issues, PRs, or vendor messages without approval for that publication target.

## First implementation rule

The first driver change must be a read-only HDCP state path. It must preserve raw error status and must not request authentication, select Type 1, or expose standard KMS properties.
