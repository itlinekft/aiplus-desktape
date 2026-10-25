// desktape OCR helper for macOS (macos-target D4): Apple Vision on one PNG, the lines as JSON.
//
//   desktape-ocr <image.png>   ->   [{"text": "...", "x": 120, "y": 48, "conf": 1.0}, ...]
//
// x and y are the centre of each line in image pixels, origin top left. desktape compiles this once on the
// target (`swiftc -O`) and feeds it the driver's own screenshot of a window, so the helper itself needs no
// macOS permission: it only reads a file. Language correction is off: Vision has no Hungarian model, and
// without correction it still reads Hungarian accents exactly (measured 2026-10-25).
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write("usage: desktape-ocr <image.png>\n".data(using: .utf8)!)
    exit(2)
}
let url = URL(fileURLWithPath: args[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
    FileHandle.standardError.write("cannot read \(args[1])\n".data(using: .utf8)!)
    exit(1)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])

let w = Double(image.width), h = Double(image.height)
var lines: [[String: Any]] = []
for observation in request.results ?? [] {
    guard let best = observation.topCandidates(1).first else { continue }
    let box = observation.boundingBox            // normalised, origin bottom left
    lines.append(["text": best.string, "x": Int(box.midX * w), "y": Int((1 - box.midY) * h),
                  "conf": Double(best.confidence)])
}
let data = try JSONSerialization.data(withJSONObject: lines)
print(String(data: data, encoding: .utf8)!)
