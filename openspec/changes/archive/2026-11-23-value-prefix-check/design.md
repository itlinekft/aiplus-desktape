# Design — value-prefix-check

## Decisions

### D1. The top element, not "exactly one"

Every frame of a web page is its own Document in the tree, so "exactly one Document" would refuse ordinary pages
with frames, and a frame can carry any address. The page's own Document is the shallowest one; the step reads that,
and refuses when two tie at that depth, since then it cannot tell which is the page.

### D2. The driver's value, compared as written

The value comes from the driver's element (or, when the element list has none, the value in its tree line), never
from text shown on the page. It is compared with `startswith`, case and all: an address prefix through the path
(`https://host/path?`) leaves no room for another host. A page can change its own path with a script but not its
origin, so the prefix is as strong as the host it names.

### D3. A fixed sentence

The failure ends with "so the steps after it were not run" (`WRONG_VALUE_END`), so a caller that pins desktape by
hash can recognise the refusal, as it does "not reported as a password field, so nothing was sent". The value is
quoted only up to the prefix's length plus 24 characters, so a long query (a session token) is not written to the
run's files in full.

### D4. `focus` by the end of the title

A browser window's title is "<page title> - Google Chrome[ - <profile>]": the front varies with the page, the end
names the program and the profile. `suffix: true` matches the end, like `prefix: true` the start; both at once is
refused.

### D5. An optional `id`

Measured: Chrome's own controls can carry the role Document too (a value-less `Document "Keresés ikon"
[id=view_1011]` on the new tab page), while every page and frame is `id=RootWebArea`. `id:` narrows the step to
elements with that id, so a browser control can never be taken for the page.
