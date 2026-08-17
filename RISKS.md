# Risk register

| ID | Risk | Likelihood | Impact | Mitigation / trigger |
|---|---|---:|---:|---|
| R-001 | RM/GSP rejects HDCP operations for the Linux GeForce client | Medium | High | Read-only query first; preserve raw status |
| R-002 | Public shared code is not wired into the shipping product path | Medium | High | Verify runtime state changes against sink/topology changes |
| R-003 | A diagnostic reports protection without encryption | Low | Critical | Never map unknown/error to enabled; use validity mask and raw status |
| R-004 | Custom display module causes loss of GUI or boot failure | Medium | High | Recovery checklist, SSH/TTY, known-good boot, matching userspace/GSP, approval |
| R-005 | DP and HDMI are incorrectly treated as one implementation | Medium | Medium | DP SST first; separate source and experiment records |
| R-006 | MST or clone topology weakens protection | High if enabled | High | Disable initially; add weakest-link tests later |
| R-007 | Vulkan support is inferred from Windows or GPU model | Medium | High | Query every runtime capability and codec profile |
| R-008 | A protected path is mislabeled vendor-attested | Medium | Critical | Exact state vocabulary; vendor/service states separate |
| R-009 | NVIDIA snapshot updates invalidate assumptions | Medium | Medium | Pinned source lock and decision before rebasing |
| R-010 | Research drifts into circumvention | Low | Critical | No keys, credentials, copied CDMs, spoofing, or forced manifests |
| R-011 | CI cannot see historical snapshot commits | Low | Medium | `fetch-depth: 0`; actionable failure |
| R-012 | Nova distracts from the actionable path | Medium | Medium | Nova is source-mapping only until first proof |
