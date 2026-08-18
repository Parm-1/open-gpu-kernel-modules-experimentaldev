# `mfcdm-probe`

`mfcdm-probe.exe` locates the first unsupported public Windows Media Foundation CDM step without creating a CDM access object, CDM, session, challenge, license request, protected sample, or playback pipeline.

## Stages

The executable always emits the same ordered stage schema:

1. COM multithreaded-apartment initialization;
2. Media Foundation startup;
3. `IMFMediaEngineClassFactory` creation;
4. `IMFMediaEngineClassFactory4` query;
5. optional `IMFContentDecryptionModuleFactory` creation for an explicitly supplied key-system identifier;
6. optional `IMFContentDecryptionModuleFactory::IsTypeSupported` result;
7. Media Foundation shutdown.

With no key system, stages 5 and 6 are marked `not_requested`. The probe does not contain a default PlayReady, Widevine, Clear Key, or service identifier.

## Build

Use a current 64-bit Microsoft Windows SDK and MSVC:

```powershell
cmake -S probes/mfcdm -B build/mfcdm -A x64
cmake --build build/mfcdm --config Release --parallel
build/mfcdm/Release/mfcdm-probe.exe --self-test
```

The Windows SDK must expose `IMFMediaEngineClassFactory4` and `IMFContentDecryptionModuleFactory`.

## Run

Infrastructure-only observation:

```powershell
build/mfcdm/Release/mfcdm-probe.exe > mfcdm-infrastructure.json
$LASTEXITCODE
```

Explicit key-system/type observation:

```powershell
build/mfcdm/Release/mfcdm-probe.exe `
  --key-system '<explicit-identifier>' `
  --content-type 'video/mp4; codecs="avc1.640028"' `
  > mfcdm-type.json
$LASTEXITCODE
```

The same binary can be invoked under Wine using the same arguments and redirected JSON output. Do not infer CDM usability, robustness, hardware protection, license eligibility, or service authorization from factory/type support.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | The explicitly requested key-system/type was reported supported. |
| `2` | Command-line usage error. |
| `10` | Public COM/MF/factory infrastructure completed; no key system was requested. |
| `20` | The requested key-system/type was reported unsupported. |
| `30` | A public API stage failed, cleanup failed, or the probe encountered an internal error. |

A nonzero code is evidence, not a reason to return fake success. Preserve stdout, stderr, the executable hash, command line, platform identity, and exit code separately for Windows and Wine.

## Privacy and safety

The output contains only the explicit input strings, stage names, HRESULT values/names, support boolean, classification, and claim boundary. It intentionally avoids OS account names, host names, hardware identifiers, certificates, challenges, license bodies, keys, CDM memory, media samples, URLs, and network activity. Review explicit input strings before sharing.
