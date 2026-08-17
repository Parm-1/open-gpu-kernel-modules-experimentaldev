# EXP-0007: Media Foundation CDM first-failure trace

## Question

At which public Media Foundation discovery stage does the same explicit CDM factory/type query first fail or report unsupported on native Windows and Wine?

## Current status

The public-SDK source builds with MSVC warnings as errors, passes deterministic self-tests, and passes source/import safety checks. Neither the native-Windows discovery path nor the Wine path has been executed as experiment evidence.

## Safety boundary

The probe stops at `IMFContentDecryptionModuleFactory::IsTypeSupported`. It does not create CDM access, a CDM, a session, a challenge, a license request, protected media, or playback. No vendor key system is queried unless an operator supplies it explicitly.

## Required comparison

For each platform preserve:

- the identical executable SHA-256;
- exact command and explicit input;
- stdout JSON and stderr;
- exit code;
- minimal OS or Wine version without host identity;
- first failure stage and HRESULT, or first unsupported stage;
- statement that no later CDM, license, network, or media operation was attempted.

Use the same executable hash and exact input for the paired Windows/Wine comparison. A no-key-system infrastructure trace should be collected first; any explicit key-system query is a separate observation.
