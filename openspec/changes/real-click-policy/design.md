# Design — real-click-policy

## D1. The mechanism: the helper's click, aimed at one window

On macOS a real click goes through `desktape-input` (the same CGEvent path that answered the consent prompt in
`panel-mac-click`). Before it clicks, the helper's `front` lists the on-screen windows front to back with their
bounds; desktape clicks only when the first window containing the point is the step's window (by window id, else
pid). This is the macOS form of "A real click aimed at one window" (`os_click` on Windows). `front` gains the
window bounds and a `front-at <x> <y>` form that answers the topmost window at a point, any layer, so a system
prompt (not layer 0) is seen.

## D2. Who decides: desktape's target profile

`use: test | personal` on a target profile. Default: `personal` when `tidy: minimize` (a person works there),
otherwise `test`. The difference for real input:

| | test | personal |
|---|---|---|
| real click on the step's own window | with the lock | with the lock, and inside a booking when one exists |
| real click on a system prompt (a grant) | devauth authorization | devauth authorization |

The driver's own refusal is no longer the decision: on macOS an `os: true` click does not ask the driver to click.

## D3. A grant: what it is and how it is authorized

A point whose topmost window belongs to a process the step does not name, and which is not an ordinary app window
(not layer 0, or owned by a system agent), is a prompt. A click on it is a grant. desktape requires an authorization
on standard input: a JSON statement `{target, prompt_owner, prompt_text, button, nonce, expires}` and an OpenSSH
signature over it (`ssh-keygen -Y sign -n desktape-grant`), verified with `ssh-keygen -Y verify` against the
signers file named in desktape's config (`grant_signers:`, the public key only). desktape checks: the signature, the
expiry (at most 120 s), the nonce not seen before (kept in the state dir), the target, the prompt's owner and its
OCR'd text containing `prompt_text`, and the button found by OCR inside the prompt. Any mismatch: no click, a named
failure. The private key is devauth's (its store, never readable by a session); desktape holds no secret.

## D4. The devauth side (owned by itline-ai-devauth)

A catalogue entry kind for a grant binding (machine, prompt owner, prompt text, button), owner-approved like any
other; a tool (or a `devauth_type` form) that, for an approved binding, signs the statement and runs desktape's
pinned script with it on stdin. The model names the binding; it never holds the key.

## D5. Measured before relied on

The owner of the 2026-11-27 consent prompt was not recorded. The panel's helper-click audit line gains the
`front-at` answer, so the next prompt names its owner; D3's "system-owned" rule is fixed from that measurement.

## Open

- Whether UAC on Windows (secure desktop) can be reached at all: out of scope, it stays the person's.
- The prompt owners differ per macOS release; the rule names layer and owner, measured per release in
  `knowledge/macos.md`.
