# Tasks: install-cold-read

## 1. doctor

- [x] 1.1 `doctor` with no target: the last line says this computer is ready to drive and no target was checked,
  with `doctor --target NAME` and `pair NAME --os windows`; "everything is in place" only when a target or `--local`
  was checked. [REQ: prerequisites-checked-and-named]
- [x] 1.2 Next steps on the dead ends: `--local` on Linux; a target that is not reachable.
  [REQ: prerequisites-checked-and-named]
- [x] 1.3 Selftest for 1.1 and 1.2. [REQ: prerequisites-checked-and-named]

## 2. Documents and skills

- [x] 2.1 README, Hungarian and English: "Before you start", one default route, uv as the one prerequisite, the
  measured new-target status, a many-machines note. [REQ: prerequisites-checked-and-named]
- [x] 2.2 One Cua Driver procedure on Windows: `docs/windows-setup.md` §2 and `docs/install.md` use the pinned
  release and its hash; `docs/pairing.md` §2 names both ways to accept the line; `docs/windows-setup.md` gets an
  uninstall section. [REQ: prerequisites-checked-and-named]
- [x] 2.3 Skills: `desktape` OS-neutral; `desktape-start` names the surfaces, the macOS driver steps and the
  controller-only result. [REQ: prerequisites-checked-and-named]
- [x] 2.4 The site's "Get started": the plugin route and the current status. [REQ: prerequisites-checked-and-named]
- [x] 2.5 CHANGELOG. [REQ: prerequisites-checked-and-named]

## 3. Check

- [ ] 3.1 `--selftest`, `openspec validate --all`, `claude plugin validate .`, the leak scan.
  [REQ: prerequisites-checked-and-named]
- [ ] 3.2 Run the install reviewer again on the new commit; record its verdict in `docs/MEASURED.md` as a paper
  review. [REQ: prerequisites-checked-and-named]
