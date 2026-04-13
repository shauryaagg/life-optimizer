import AppKit
import Foundation

/// Manages macOS permission checks and requests.
class PermissionManager: ObservableObject {
    @Published var accessibilityGranted: Bool = false
    @Published var screenRecordingGranted: Bool = false

    /// Check all required permissions.
    func checkAll() {
        accessibilityGranted = AXIsProcessTrusted()
        screenRecordingGranted = checkScreenRecording()
    }

    /// Request Accessibility permission (shows system prompt).
    func requestAccessibility() {
        let options = [kAXTrustedCheckOptionPrompt.takeRetainedValue(): true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
        // Re-check after a short delay to update UI
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
            self?.accessibilityGranted = AXIsProcessTrusted()
        }
    }

    /// Open Screen Recording settings in System Settings.
    func openScreenRecordingSettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
            NSWorkspace.shared.open(url)
        }
    }

    /// Open Accessibility settings in System Settings.
    func openAccessibilitySettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
            NSWorkspace.shared.open(url)
        }
    }

    /// Check screen recording permission by attempting a minimal capture.
    private func checkScreenRecording() -> Bool {
        let testPath = "/tmp/.lo_test_screenshot.jpg"
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
        task.arguments = ["-x", "-t", "jpg", testPath]

        do {
            try task.run()
            task.waitUntilExit()
        } catch {
            return false
        }

        let exists = FileManager.default.fileExists(atPath: testPath)
        try? FileManager.default.removeItem(atPath: testPath)
        return exists && task.terminationStatus == 0
    }
}
