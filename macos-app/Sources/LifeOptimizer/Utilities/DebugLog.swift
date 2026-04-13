import Foundation

/// File-based debug logging (print doesn't work in GUI apps).
func debugLog(_ msg: String) {
    let line = "\(Date()): \(msg)\n"
    let path = "/tmp/life_optimizer_debug.txt"
    if let data = line.data(using: .utf8) {
        if let fh = FileHandle(forWritingAtPath: path) {
            fh.seekToEndOfFile()
            fh.write(data)
            fh.closeFile()
        } else {
            FileManager.default.createFile(atPath: path, contents: data)
        }
    }
}
