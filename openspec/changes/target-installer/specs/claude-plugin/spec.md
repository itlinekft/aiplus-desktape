## MODIFIED Requirements

### Requirement: The plugin gives the agent a short command

The plugin SHALL NOT ship a top-level `bin/` folder. Its skills SHALL call desktape as
`uv run --quiet "${CLAUDE_PLUGIN_ROOT}/desktape.py" <command> …`, one form that runs in Bash, Git Bash, PowerShell and
cmd, and SHALL say where to find `uv` when it is not yet on the shell's PATH.

#### Scenario: a look from a project folder

- **WHEN** the plugin is enabled and an agent runs the skill's form of `look --grep Allow` in its project folder
- **THEN** desktape runs from the plugin's folder and the look's state is written under `./desktape-runs`

#### Scenario: an organization rollout

- **WHEN** the plugin is synced to many machines through claude.ai's organization settings
- **THEN** the sync accepts it, since it has no top-level `bin/` folder
