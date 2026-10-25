# Design — step-outcome-check

## D1. `expect:` names the purpose; all its parts must hold

```yaml
- click: { label: Glyph, role: Button, expect: { opens: Megnyitás } }
- open_file: { path: "${import_file}", dialog: Megnyitás,
               expect: { closes: Megnyitás, value: { label: "Import fájl", contains: "${import_file}" } } }
- click: { label: "Importálás indítása", expect: { shows: "sikeresen befejeződött", timeout: 60 } }
- click: { label: "Megnyitás", role: Button, expect: { filled: { role: List } } }     # the drop-down
```

`opens` / `closes` take a window title (a top-level window of the program, or a dialog inside its window);
`shows` a text anywhere in the program's windows; `value` an element whose value contains the text;
`filled` an element with at least one child item. `timeout` defaults to 10 s. A map entry's `expect:` is the
default for its element; the step's own `expect:` replaces it whole (no merge, so a reader sees one
outcome). Variables are substituted after the map is resolved, so a map default can use `${import_file}`.
Steps without `expect:` keep the `step-effect-check` behaviour (something must change).

## D2. Failure words, only on what is new

The failure check reads only windows that appeared after the action and tree lines that were not there
before it. A menu item "Hibajelentés" that was always on screen is not a failure; a new "Hiba" box is. The
list is case-insensitive and substring-based; a map extends it with `failure_words:`. A new window whose
UI Automation does not answer within its deadline is reported by its title alone.

## D3. Plain sentences

| what happened | the sentence |
|---|---|
| `opens` not reached | after <step>: the window 'X' did not open |
| `closes` not reached | after <step>: the window 'X' is still open |
| `shows` not reached | after <step>: 'text' did not appear in the program's windows |
| `value` not reached | after <step>: 'label' shows 'actual', not 'wanted' |
| `filled` not reached | after <step>: 'label' stayed empty |
| failure seen | after <step>: <program> said in 'title': 'text' |
| call hung | <step> could not be delivered: 'X' (exe) is in front and does not answer; it was already open before this step / it opened with this step |

## D4. One check for unplanned dialogs, after the step

The `replay-guards` check ran before the next step and only in `run`. It now also runs right after each
action, in `run` and `act`, and a window named by the step's `expect.opens` or by the tape's `dialogs:` (for
`act`, the tape given with `--append`) is planned. Its report lists the window's text and buttons, so the
agent can name it or press the right button.

## D5. Alerts

`run` sends one alert when it stops (the failed step's sentence). `act` sends one when the program itself
reported a failure (D2), and keeps the stuck/blocked alerts of `step-effect-check`.
