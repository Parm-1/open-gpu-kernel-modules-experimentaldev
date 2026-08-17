# DECISION-0002: read-only first

Status: Accepted — 2026-08-17

## Decision

The first driver experiment queries authoritative HDCP state only. It does not initiate authentication, select a stream type, or expose standard KMS content-protection properties.

## Reason

Source presence does not prove that the Linux GeForce RM/GSP path authorizes or instantiates the operation. A read-only result distinguishes a community-accessible path from a narrow NVIDIA hook or a vendor-blocked backend with minimal risk.
