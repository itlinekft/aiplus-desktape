# Tasks — mac-file-dialog

## 1. Runner
- [x] 1.1 `desktape-input` with glide, key, type; the pointer glide moved onto it [REQ: a-macos-file-dialog-is-driven-like-a-keyboard-and-read-before-every-return]
- [x] 1.2 `open_file` on macOS: keys from the helper, OCR before each Return, Escape on a failed check [REQ: a-macos-file-dialog-is-driven-like-a-keyboard-and-read-before-every-return]
- [x] 1.3 `os: true` on `type` / `key` with `into:` on macOS [REQ: a-macos-file-dialog-is-driven-like-a-keyboard-and-read-before-every-return]

## 2. Tests and docs
- [x] 2.1 Selftest: the happy path, a path that did not arrive, a wrong folder [REQ: a-macos-file-dialog-is-driven-like-a-keyboard-and-read-before-every-return]
- [x] 2.2 Live on the Mac mini with a throwaway folder in Claude's "Add folder" (10:31: 7/7, Claude asked about exactly that folder, Cancel; a folder that does not exist failed with nothing typed and Escape) [REQ: a-macos-file-dialog-is-driven-like-a-keyboard-and-read-before-every-return]
- [x] 2.3 docs/tape-format.md [REQ: a-macos-file-dialog-is-driven-like-a-keyboard-and-read-before-every-return]
