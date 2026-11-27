## ADDED Requirements

### Requirement: A real click on macOS is aimed at one window

On a macOS target an `os: true` click step SHALL post a real click through desktape's input helper, and SHALL click
only when the system's window list puts the step's window topmost at the point. A point on another window SHALL fail
the step without a click, naming that window's owner.

#### Scenario: the point is covered

- **WHEN** an `os: true` click on a Mac aims at Claude Desktop and another app's window covers the point
- **THEN** nothing is clicked and the failure names the covering app

### Requirement: The target profile decides real input

A target profile SHALL accept `use: test | personal`; without it a profile with `tidy: minimize` SHALL be
`personal` and any other `test`. A real click SHALL need the target's lock, and on a `personal` target also an
active booking of the session's own label. The driver's own refusal SHALL NOT decide an `os: true` click on macOS.

#### Scenario: a personal machine with a booking

- **WHEN** a real click step runs on a `personal` target and the session has no active booking there
- **THEN** nothing is clicked and the failure says to book the machine first

### Requirement: A click on a system prompt needs a devauth authorization

Until a devauth grant binding is decided, a real click whose point lands on a system prompt (a window not on the
ordinary layer) SHALL fail without a click, saying it needs a person (panel click). Once decided, such a click SHALL
be sent only with a one-time authorization on standard
input, signed by devauth's key and verified with OpenSSH signature verification against the configured signers
file, naming that target, the prompt's owner, a text the prompt shows and the button. An expired, reused, unsigned
or mismatching authorization SHALL fail the step without a click. A person's click from the panel SHALL need none.

#### Scenario: an agent clicks Allow without an authorization

- **WHEN** an agent's `act` step clicks "Allow" on a macOS consent prompt with no authorization
- **THEN** nothing is clicked and the failure says the prompt needs a person (panel click)

#### Scenario: devauth authorizes the click

- **WHEN** devauth runs the step with a signed authorization for this target, this prompt and "Allow"
- **THEN** the click is sent, the audit names the authorization's nonce, and the same authorization is refused the next time
