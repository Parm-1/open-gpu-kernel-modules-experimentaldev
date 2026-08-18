# Architecture decision index

| Decision | Status | Summary |
|---|---|---|
| [DECISION-0001](docs/decisions/DECISION-0001-repository-layout.md) | Accepted | Keep NVIDIA source intact on `main`; isolate research and patches on branches |
| [DECISION-0002](docs/decisions/DECISION-0002-read-only-first.md) | Accepted | Prove an authoritative read-only state path before control or KMS properties |
| [DECISION-0003](docs/decisions/DECISION-0003-displayport-first.md) | Accepted | Start with direct DisplayPort SST; treat HDMI and MST separately |
| [DECISION-0004](docs/decisions/DECISION-0004-nova-secondary-track.md) | Accepted | Use the shipping stack for first proof; keep Nova as the upstream-native follow-on |
| [DECISION-0005](docs/decisions/DECISION-0005-gate1-blocked-pending-native-access.md) | Accepted | Gate 0/1 are externally blocked on native RTX 2060 access, not a technical verdict; redirect to non-hardware workstreams until the operator runs EXP-0006 or grants remote access |
