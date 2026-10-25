// desktape pointer helper for macOS (person-cursor D2): glide the real pointer to a point, like a person.
//
//   desktape-pointer <x> <y> [ms]   ->   prints the pointer's position afterwards, "x y"
//
// x and y are screen points, origin top left (the driver's element frames use the same space). The pointer
// moves along an ease-in-out curve at 60 steps a second; the driver's own pointer call jumps once per call,
// which looks choppy in a video (measured 2026-10-25). desktape compiles this once on the target.
import CoreGraphics
import Foundation

let args = CommandLine.arguments.dropFirst().compactMap { Double($0) }
guard args.count >= 2 else {
    FileHandle.standardError.write("usage: desktape-pointer <x> <y> [ms]\n".data(using: .utf8)!)
    exit(2)
}
let (x1, y1) = (args[0], args[1])
let ms = args.count > 2 ? max(0, min(args[2], 3000)) : 500
let start = CGEvent(source: nil)?.location ?? CGPoint(x: x1, y: y1)
let steps = max(1, Int(ms / 1000 * 60))
for i in 1...steps {
    var k = Double(i) / Double(steps)
    k = k * k * (3 - 2 * k)
    let p = CGPoint(x: start.x + (x1 - start.x) * k, y: start.y + (y1 - start.y) * k)
    CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: .left)?
        .post(tap: .cghidEventTap)
    usleep(useconds_t(1_000_000 / 60))
}
let end = CGEvent(source: nil)?.location ?? CGPoint(x: x1, y: y1)
print("\(Int(end.x)) \(Int(end.y))")
