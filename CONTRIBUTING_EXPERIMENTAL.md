# Contributing to the experimental protected-media work

1. Read `CHARTER.md` and `AGENTS.md`.
2. Create or update an experiment record before implementation.
3. Pin every source revision and record exact commands.
4. Keep one concept per commit.
5. Treat errors and unsupported states as results; never return fake success.
6. Do not commit production credentials, DRM messages, keys, certificates, decrypted samples, EDIDs, hostnames, serial numbers, or account data.
7. Do not load experimental modules without the recovery checkpoint.
8. Driver patches need negative controls and lifecycle behavior, not only the happy path.
9. Pull requests must state the highest security-state class actually proven.
