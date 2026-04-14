import AppKit
import CoreGraphics
import Foundation

/// Native screenshot capture from the Swift app (uses the app's own TCC permissions).
/// This replaces the Python daemon's screencapture calls which were being blocked by TCC.
@MainActor
class ScreenshotCapture: ObservableObject {
    @Published var isRunning = false
    @Published var lastCaptureTime: Date?
    @Published var captureCount: Int = 0

    private var timer: Timer?
    private let interval: TimeInterval
    private let quality: Float = 0.6
    private let scale: CGFloat = 0.5
    private let baseDir: URL

    /// Track consecutive failures to back off when permission is denied
    private var consecutiveFailures: Int = 0
    private var backoffUntil: Date?
    private static let failureThreshold = 3
    private static let backoffSeconds: TimeInterval = 300

    init(interval: TimeInterval = 30, baseDir: URL? = nil) {
        self.interval = interval
        let defaultDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Documents/GitHub/life-optimizer/data/screenshots")
        self.baseDir = baseDir ?? defaultDir
    }

    func start() {
        guard !isRunning else { return }
        isRunning = true
        // Fire once immediately, then on interval
        captureNow()
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { _ in
            Task { @MainActor [weak self] in
                self?.captureNow()
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        isRunning = false
    }

    func captureOnAppSwitch(appName: String) {
        captureNow(appName: appName, trigger: "app_switch")
    }

    private func captureNow(appName: String? = nil, trigger: String = "interval") {
        // Check backoff
        if let until = backoffUntil, Date() < until {
            return
        }

        let resolvedAppName = appName ?? frontmostAppName() ?? "unknown"

        guard let result = captureScreen() else {
            handleFailure()
            return
        }

        // Save to disk
        let now = Date()
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let dateStr = formatter.string(from: now)
        formatter.dateFormat = "HHmmss"
        let timeStr = formatter.string(from: now)
        let safeName = resolvedAppName
            .lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .filter { $0.isLetter || $0.isNumber || $0 == "_" || $0 == "-" }

        let dayDir = baseDir.appendingPathComponent(dateStr)
        try? FileManager.default.createDirectory(at: dayDir, withIntermediateDirectories: true)
        let outPath = dayDir.appendingPathComponent("\(timeStr)_\(safeName).jpg")

        if saveJPEG(result, to: outPath) {
            consecutiveFailures = 0
            backoffUntil = nil
            lastCaptureTime = now
            captureCount += 1
        } else {
            handleFailure()
        }
    }

    private func handleFailure() {
        consecutiveFailures += 1
        if consecutiveFailures >= Self.failureThreshold {
            backoffUntil = Date().addingTimeInterval(Self.backoffSeconds)
            NSLog("Screenshot capture failed \(consecutiveFailures) times, backing off for \(Self.backoffSeconds)s")
        }
    }

    /// Capture the entire screen using CGWindowListCreateImage (works with Screen Recording permission).
    private func captureScreen() -> CGImage? {
        // Use the main display; capture full screen, on-screen windows only
        let image = CGWindowListCreateImage(
            CGRect.null,
            .optionOnScreenOnly,
            kCGNullWindowID,
            [.boundsIgnoreFraming]
        )
        return image
    }

    private func saveJPEG(_ image: CGImage, to url: URL) -> Bool {
        // Resize
        let newWidth = Int(CGFloat(image.width) * scale)
        let newHeight = Int(CGFloat(image.height) * scale)

        guard let colorSpace = image.colorSpace,
              let context = CGContext(
                data: nil,
                width: newWidth,
                height: newHeight,
                bitsPerComponent: 8,
                bytesPerRow: 0,
                space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
              ) else {
            return false
        }

        context.interpolationQuality = .high
        context.draw(image, in: CGRect(x: 0, y: 0, width: newWidth, height: newHeight))

        guard let resized = context.makeImage() else { return false }

        // Encode as JPEG
        let rep = NSBitmapImageRep(cgImage: resized)
        let props: [NSBitmapImageRep.PropertyKey: Any] = [
            .compressionFactor: quality
        ]
        guard let data = rep.representation(using: .jpeg, properties: props) else {
            return false
        }

        do {
            try data.write(to: url)
            return true
        } catch {
            NSLog("Failed to write screenshot: \(error)")
            return false
        }
    }

    private func frontmostAppName() -> String? {
        return NSWorkspace.shared.frontmostApplication?.localizedName
    }
}
