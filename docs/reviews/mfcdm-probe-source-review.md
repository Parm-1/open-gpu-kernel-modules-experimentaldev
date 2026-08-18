# `mfcdm-probe` source review

Review status: `PASSED_WINDOWS_CI`

Reviewed source commit: `f1960bfb3583e9b09d56f9fe5cf87af91e3c40bf`

## Result

The first E-001 implementation is source-complete and build-passed. It uses the public Microsoft Windows SDK discovery interfaces and stops after `IMFContentDecryptionModuleFactory::IsTypeSupported`.

The Windows workflow completed successfully with:

- MSVC `/W4 /WX`, conforming mode, SDL checks, UTF-8 source handling, CFG, DEP, and ASLR;
- deterministic internal self-tests that perform no COM or CDM query;
- a usage-error negative control;
- source-policy checks rejecting CDM access, CDM creation, session creation, request/license operations, network calls, and hardcoded known vendor key-system identifiers;
- direct PE-import inspection rejecting WinHTTP, WinINet, Winsock, and URLMon;
- executable SHA-256 and import-report packaging;
- an explicit build-only verdict.

## Source findings

- No Windows system binary, proprietary CDM, certificate, key, license body, challenge, media sample, or private COM declaration is redistributed.
- No key-system identifier is queried unless supplied explicitly by the operator.
- The no-input path ends after the public `IMFMediaEngineClassFactory4` interface is obtained and marks key-system stages `not_requested`.
- HRESULT failure and semantic unsupported are separate outcomes.
- COM objects are released before `MFShutdown`; successful COM initialization is balanced before process exit.
- The stable JSON policy explicitly records that no access object, CDM, session, request, network operation, or playback is created.
- Nonzero evidence exits are intentional and are not converted into fake success.

## Remaining uncertainty

CI proves Windows SDK buildability and static safety boundaries only. The workflow deliberately runs only `--self-test`, so no COM, Media Foundation factory, key-system, or type-support runtime stage is established by CI.

Native Windows and Wine traces remain `NOT_RUN`. A runtime verdict requires the identical executable hash and exact explicit input on both platforms.
