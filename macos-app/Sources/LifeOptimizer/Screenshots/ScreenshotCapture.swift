import AppKit
import CoreGraphics
import Foundation
import ScreenCaptureKit

/// Native screenshot capture from the Swift app (uses the app's own TCC permissions).
///
/// Uses ScreenCaptureKit on macOS 14+ which is the officially supported API.
/// CGWindowListCreateImage is deprecated on 14+ and returns desktop-only
/// (no windows) for ad-hoc signed apps without proper entitlements.
///
/// ScreenCaptureKit respects the same Screen Recording permission that's
/// already granted, but actually captures window contents.
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
        // Don't fire immediately on launch — gives the system a moment to
        // settle and avoids hitting SCK before it's ready, which can cause
        // spurious permission prompts on some systems.
        Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            self?.captureNow()
        }
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
        if appName.contains("LifeOptimizer") || appName.contains("Life Optimizer") {
            return
        }
        captureNow(appName: appName, trigger: "app_switch")
    }

    private func captureNow(appName: String? = nil, trigger: String = "interval") {
        NSLog("[LO.screenshot] captureNow called trigger=\(trigger)")
        if let until = backoffUntil, Date() < until {
            NSLog("[LO.screenshot] in backoff until \(until)")
            return
        }

        let resolvedAppName = appName ?? frontmostAppName() ?? "unknown"
        NSLog("[LO.screenshot] frontmost app: \(resolvedAppName)")

        if resolvedAppName.contains("LifeOptimizer") || resolvedAppName.contains("Life Optimizer") {
            NSLog("[LO.screenshot] skipping — our own app")
            return
        }

        // Do NOT guard on CGPreflightScreenCaptureAccess — it returns false
        // for ad-hoc signed binaries even when the System Settings toggle is
        // on, because TCC keys grants by code hash which changes per build.
        // Just try the SCK capture; it will throw if permission truly denied.
        NSLog("[LO.screenshot] starting SCK capture")

        Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                let image = try await self.captureScreenSCK()
                NSLog("[LO.screenshot] got image \(image.width)x\(image.height)")
                self.saveImage(image, appName: resolvedAppName, trigger: trigger)
                self.consecutiveFailures = 0
                self.backoffUntil = nil
                self.lastCaptureTime = Date()
                self.captureCount += 1
                NSLog("[LO.screenshot] saved, count=\(self.captureCount)")
            } catch {
                NSLog("[LO.screenshot] ERROR: \(error.localizedDescription)")
                self.handleFailure()
            }
        }
    }

    private func handleFailure() {
        consecutiveFailures += 1
        if consecutiveFailures >= Self.failureThreshold {
            backoffUntil = Date().addingTimeInterval(Self.backoffSeconds)
        }
    }

    /// Capture the primary display using ScreenCaptureKit.
    private func captureScreenSCK() async throws -> CGImage {
        // Get shareable content — this is the modern, non-deprecated API
        let content = try await SCShareableContent.excludingDesktopWindows(
            false,
            onScreenWindowsOnly: true
        )

        guard let display = content.displays.first else {
            throw NSError(
                domain: "ScreenshotCapture", code: 1,
                userInfo: [NSLocalizedDescriptionKey: "No display available"]
            )
        }

        // Exclude our own app's windows from the capture
        let ourBundleID = Bundle.main.bundleIdentifier ?? "com.lifeoptimizer.app"
        let excludedApps = content.applications.filter { $0.bundleIdentifier == ourBundleID }

        let filter = SCContentFilter(
            display: display,
            excludingApplications: excludedApps,
            exceptingWindows: []
        )

        let config = SCStreamConfiguration()
        config.width = Int(display.width)
        config.height = Int(display.height)
        config.minimumFrameInterval = CMTime(value: 1, timescale: 60)
        config.showsCursor = false
        config.scalesToFit = true

        // SCScreenshotManager is macOS 14+
        if #available(macOS 14.0, *) {
            return try await SCScreenshotManager.captureImage(
                contentFilter: filter,
                configuration: config
            )
        } else {
            throw NSError(
                domain: "ScreenshotCapture", code: 2,
                userInfo: [NSLocalizedDescriptionKey: "macOS 14+ required for ScreenCaptureKit"]
            )
        }
    }

    private func saveImage(_ image: CGImage, appName: String, trigger: String) {
        let now = Date()
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let dateStr = formatter.string(from: now)
        formatter.dateFormat = "HHmmss"
        let timeStr = formatter.string(from: now)
        let safeName = appName
            .lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .filter { $0.isLetter || $0.isNumber || $0 == "_" || $0 == "-" }

        let dayDir = baseDir.appendingPathComponent(dateStr)
        try? FileManager.default.createDirectory(at: dayDir, withIntermediateDirectories: true)
        let outPath = dayDir.appendingPathComponent("\(timeStr)_\(safeName).jpg")

        // Resize & encode as JPEG
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
              )
        else { return }

        context.interpolationQuality = .high
        context.draw(image, in: CGRect(x: 0, y: 0, width: newWidth, height: newHeight))
        guard let resized = context.makeImage() else { return }

        let rep = NSBitmapImageRep(cgImage: resized)
        let props: [NSBitmapImageRep.PropertyKey: Any] = [.compressionFactor: quality]
        guard let data = rep.representation(using: .jpeg, properties: props) else { return }
        try? data.write(to: outPath)
    }

    private func frontmostAppName() -> String? {
        NSWorkspace.shared.frontmostApplication?.localizedName
    }
}
