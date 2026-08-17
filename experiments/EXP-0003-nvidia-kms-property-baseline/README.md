# EXP-0003: Collect native NVIDIA KMS property baseline

## Question

Which physical connector is owned by `nvidia-drm`, and are `Content Protection` and `HDCP Content Type` exposed?

## Acceptance criterion

Connector ownership and property values are captured on native Linux with redacted provenance.

## Safety

Read-only native diagnostics; no module modification.
