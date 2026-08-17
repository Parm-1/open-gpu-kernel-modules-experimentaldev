# `mfcdm-probe` source review

Review status: `PENDING_WINDOWS_CI`

## Intended properties

- Builds only against public Microsoft Windows SDK interfaces.
- Uses no redistributed Windows system binary or proprietary CDM.
- Has no built-in vendor or service key-system identifier.
- Performs no network operation.
- Stops at `IMFContentDecryptionModuleFactory::IsTypeSupported`.
- Emits deterministic JSON fields and preserves HRESULT values.
- Releases COM objects before `MFShutdown` and balances successful COM initialization.
- Treats unsupported and failed as distinct outcomes.
- Returns nonzero evidence codes rather than fabricating success.

## CI review requirements

The Windows workflow must:

1. compile with MSVC warnings as errors;
2. run the internal non-COM self-test;
3. reject prohibited CDM/session/license/network calls in source;
4. inspect direct PE imports and reject WinHTTP, WinINet, URLMon, and Winsock;
5. archive the executable hash and import report;
6. avoid treating the CI host as a Windows protected-media runtime result.

## Claim boundary

A green build proves `SOURCE_PRESENT` and buildability only. No Windows or Wine runtime stage is proven by this review.
