# Tasks — target-pairing

## 1. Controller half
- [x] 1.1 `pair NAME`: key, fingerprint, the restricted line with `from=`, the profile [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]
- [ ] 1.2 `pair NAME --check` (built; measured with the rehearsal, 3.2) [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]
- [x] 1.3 `unpair NAME`: the target's line first (macOS/Linux: awk on the last field, measured on a scratch file; Windows: a placeholder until task 2.2), then the local key, profile, known_hosts [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]

## 2. Target half (the Windows session)
- [ ] 2.1 `pair --accept "<line>"` on the target: fingerprint shown, the right file (admin or not) [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]
- [ ] 2.2 Removal by comment on Windows [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]

## 3. Tests, docs, rehearsal
- [x] 3.1 Selftest: the line, the address filter, the profile, unpair order [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]
- [ ] 3.2 Rehearse pair → check → look → unpair, Mac → Windows box, with the owner's yes [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]
- [x] 3.3 Docs [REQ: a-controller-can-be-paired-with-a-target-and-unpaired-again]
