// desktape input helper for macOS: a person's pointer and keyboard, through the system's own input path.
//
//   desktape-input glide <x> <y> [ms]    move the real pointer smoothly to (x, y) screen points (person-cursor D2)
//   desktape-input key <combo>           press one key or combination, e.g. cmd+shift+g, return, escape, cmd+a
//   desktape-input type <text>           type text as unicode characters, whatever the keyboard layout
//   desktape-input type -                the text from standard input (a secret never shows in the process list)
//   desktape-input front                 the ordinary windows front to back (top 6), as JSON lines
//                                        {"window_id", "pid", "app", "alpha"}; the caller skips overlays
//
// Keys go where a real keyboard's go: to the window in front. That is what reaches a macOS file dialog, which
// runs in a separate service process: the driver's keys go to the app's own process and never arrive there
// (mac-file-dialog D1, measured 2026-10-25). Key names follow US key positions; text is layout-independent.
import CoreGraphics
import Foundation

func fail(_ s: String) -> Never {
    FileHandle.standardError.write((s + "\n").data(using: .utf8)!)
    exit(2)
}

let codes: [String: CGKeyCode] = [
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13,
    "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "9": 25, "7": 26,
    "8": 28, "0": 29, "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45, "m": 46,
    "/": 44, ".": 47, ",": 43, "-": 27, "=": 24,
    "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51, "backspace": 51, "escape": 53, "esc": 53,
    "forwarddelete": 117, "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "left": 123, "right": 124, "down": 125, "up": 126,
]
let mods: [String: CGEventFlags] = [
    "cmd": .maskCommand, "command": .maskCommand, "shift": .maskShift, "alt": .maskAlternate,
    "option": .maskAlternate, "ctrl": .maskControl, "control": .maskControl,
]

func post(_ code: CGKeyCode, _ flags: CGEventFlags, text: String? = nil) {
    for down in [true, false] {
        guard let e = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: down) else { fail("no key event") }
        e.flags = flags
        if let t = text {
            let u = Array(t.utf16)
            e.keyboardSetUnicodeString(stringLength: u.count, unicodeString: u)
        }
        e.post(tap: .cghidEventTap)
        usleep(8_000)
    }
}

let a = Array(CommandLine.arguments.dropFirst())
guard let cmd = a.first else { fail("usage: desktape-input glide <x> <y> [ms] | key <combo> | type <text>") }
switch cmd {
case "glide":
    let n = a.dropFirst().compactMap { Double($0) }
    guard n.count >= 2 else { fail("glide needs x and y") }
    let ms = n.count > 2 ? max(0, min(n[2], 3000)) : 500
    let start = CGEvent(source: nil)?.location ?? CGPoint(x: n[0], y: n[1])
    let steps = max(1, Int(ms / 1000 * 60))
    for i in 1...steps {
        var k = Double(i) / Double(steps)
        k = k * k * (3 - 2 * k)
        let p = CGPoint(x: start.x + (n[0] - start.x) * k, y: start.y + (n[1] - start.y) * k)
        CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: .left)?
            .post(tap: .cghidEventTap)
        usleep(useconds_t(1_000_000 / 60))
    }
    let end = CGEvent(source: nil)?.location ?? CGPoint(x: n[0], y: n[1])
    print("\(Int(end.x)) \(Int(end.y))")
case "key":
    guard a.count == 2 else { fail("key needs one combination, e.g. cmd+shift+g") }
    var flags: CGEventFlags = []
    var key: CGKeyCode? = nil
    for part in a[1].lowercased().split(separator: "+").map(String.init) {
        if let m = mods[part] { flags.insert(m) } else if let c = codes[part] { key = c } else { fail("unknown key \(part)") }
    }
    guard let k = key else { fail("no key in \(a[1])") }
    post(k, flags)
    print("ok")
case "type":
    guard a.count == 2 else { fail("type needs one text argument, or - for standard input") }
    let text = a[1] == "-" ? String(data: FileHandle.standardInput.readDataToEndOfFile(), encoding: .utf8) ?? "" : a[1]
    for ch in text {
        post(0, [], text: String(ch))
        usleep(12_000)
    }
    print("ok")
case "front":
    // The system's window list runs front to back. Layer 0 holds ordinary windows; the first one that is not an
    // overlay (the driver's agent cursor is a layer-0 window too, measured) gets a keyboard's events. Ids and
    // owners need no permission (titles would need Screen Recording).
    let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID)
        as? [[String: Any]] ?? []
    for w in list.filter({ ($0[kCGWindowLayer as String] as? Int) == 0 }).prefix(6) {
        let id = w[kCGWindowNumber as String] as? Int ?? 0
        let pid = w[kCGWindowOwnerPID as String] as? Int ?? 0
        let alpha = w[kCGWindowAlpha as String] as? Double ?? 1
        let app = (w[kCGWindowOwnerName as String] as? String ?? "").replacingOccurrences(of: "\"", with: "'")
        print("{\"window_id\": \(id), \"pid\": \(pid), \"app\": \"\(app)\", \"alpha\": \(alpha)}")
    }
default:
    fail("unknown command \(cmd)")
}
