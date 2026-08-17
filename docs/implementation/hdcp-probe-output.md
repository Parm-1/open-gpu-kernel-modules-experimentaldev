# Experimental `HDCP_PROBE` output

The opt-in `nvidia_drm.hdcp_probe=1` diagnostic emits one structured kernel line per connected display detection:

```text
HDCP_PROBE display=0x00000100 transport=1 query_result=0 rm_status=0x00000000 flags=0x00010800 valid=1
```

Fields:

- `transport`: the NVKMS KAPI/ioctl transport completed.
- `query_result`: detailed DP bridge result; `0` success, `1` invalid argument, `2` unsupported route, `3` no DP device, `4` not plugged, `5` no main link, `6` RM failure.
- `rm_status`: exact status returned by the RM state query.
- `flags`: raw pinned-release `NV0073_CTRL_SPECIFIC_HDCP_STATE_*` word.
- `valid`: RM completed the query and the flags are authoritative.

Decode without making a Gate verdict:

```bash
journalctl -k -b | python3 scripts/decode-hdcp-probe.py
```

The decoder recognizes capability, authentication, encryption, and Type 1 bits defined in NVIDIA 610.57.04. A valid single line is not end-to-end proof. Gate 1 requires controlled topology, a disabled-probe negative control, repeated clean boots, and preservation of raw logs.
