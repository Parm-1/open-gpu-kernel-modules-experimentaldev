# Media Foundation CDM first-failure probe design

## Purpose

The Wine workstream needs a reproducible answer to a narrower question than “does protected playback work?”:

> How far can the public Media Foundation CDM discovery path progress before the first truthful failure on Windows and Wine?

`mfcdm-probe.exe` provides that trace without entering license, session, protected-memory, decode, presentation, HDCP, or service layers.

## Public call path

```text
CoInitializeEx
  → MFStartup
  → CoCreateInstance(CLSID_MFMediaEngineClassFactory)
  → QueryInterface(IMFMediaEngineClassFactory4)
  → [only when explicitly requested]
      CreateContentDecryptionModuleFactory(keySystem)
      → IMFContentDecryptionModuleFactory::IsTypeSupported(keySystem, contentType)
  → MFShutdown
```

The implementation uses the current Microsoft Windows SDK declarations rather than private interfaces, copied binaries, reverse-engineered GUIDs, or hand-authored COM definitions.

Official API references:

- `IMFMediaEngineClassFactory4::CreateContentDecryptionModuleFactory`
- `IMFContentDecryptionModuleFactory::IsTypeSupported`
- `mfcontentdecryptionmodule.h`

## Deliberate stop point

The source must not invoke or import code for:

- content-decryption-module access selection;
- CDM creation;
- session creation;
- server-certificate installation;
- request/challenge generation;
- license acquisition or update;
- media source, demux, decode, protected-memory, or presentation creation;
- network access.

The first version stops after `IsTypeSupported`. Later expansion requires a separate design, a new evidence question, and explicit review of what data the additional step can generate.

## Inputs

No proprietary key system is hardcoded. The two optional inputs are:

- `--key-system <identifier>`;
- `--content-type <RFC-2045 content type>`, valid only with a key system.

Omitting both produces an infrastructure-only trace and proves no vendor key system was queried.

## Output model

The JSON document has a stable ordered stage list. HRESULT stages preserve hexadecimal value and a conservative symbolic name. `IsTypeSupported` is represented as a boolean semantic result rather than an HRESULT. Skipped stages distinguish `not_requested`, `blocked_by_prior_failure`, and `not_started`.

Classifications:

- `INFRASTRUCTURE_AVAILABLE_NO_KEY_SYSTEM_REQUESTED`;
- `REQUESTED_TYPE_SUPPORTED`;
- `REQUESTED_TYPE_UNSUPPORTED`;
- `API_FAILURE`;
- `INTERNAL_ERROR`.

The trace separately records the first API failure and first unsupported semantic stage.

## Evidence interpretation

A successful factory/type-support result proves only that the public discovery interface accepted the query and returned true. It does not prove that access configuration can be selected, a CDM can be created, a session can be opened, a license can be obtained, samples are protected, robustness is hardware-backed, output protection is active, or a service will authorize a representation.

The decisive Windows/Wine comparison is the earliest stage, HRESULT, and semantic support result under the same explicit input. Runtime evidence remains `NOT_RUN` until collected on those platforms.
