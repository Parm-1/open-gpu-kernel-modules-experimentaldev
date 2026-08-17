# HDMI versus DisplayPort boundary

The current proof target is **direct DisplayPort SST only**.

## DisplayPort evidence

The public source contains an explicit DP library with HDCP state queries, authentication control, link validation, Type 0/Type 1 stream selection, MST logic, ECF/QSE handling, and retry timers.

## HDMI state

The presence of generic RM HDCP controls and HDMI display code does not prove that HDMI uses the same callable ownership path. No HDMI KMS HDCP bridge is identified in the current source map.

## Consequence

- Do not advertise HDMI support from a successful DP experiment.
- Do not use a DP-to-HDMI adapter in initial tests.
- Do not infer Type 1 from sink EDID or Windows behavior.
- Add HDMI only after a separate call graph identifies its authoritative state, request, link-loss, and repeater handling.
- Treat passive dongles, active converters, AV receivers, and MST PCON devices as distinct topologies.
