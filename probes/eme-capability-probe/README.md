# EME capability probe

Serve this directory over localhost or HTTPS:

```bash
python3 -m http.server 8000 --directory probes/eme-capability-probe
```

The page calls only `navigator.requestMediaKeySystemAccess()`. It does not create sessions, acquire licenses, inspect credentials, or play content. Accepted configurations are `CAPABILITY_ADVERTISED`, not proof of hardware protection, vendor attestation, or service authorization.
