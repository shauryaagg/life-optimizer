import Foundation
import SwiftUI

/// Orchestrates the first-launch setup process.
@MainActor
class SetupManager: ObservableObject {
    @Published var step: SetupStep = .welcome
    @Published var progress: Double = 0
    @Published var statusMessage: String = ""
    @Published var error: String?
    @AppStorage("setupComplete") var isSetupComplete: Bool = false

    // Permissions — stored directly here so SwiftUI sees the changes
    @Published var accessibilityGranted: Bool = false
    @Published var screenRecordingGranted: Bool = false

    enum SetupStep: Int, CaseIterable {
        case welcome
        case permissions
        case pythonSetup
        case llmSetup
        case complete
    }

    func nextStep() {
        let allSteps = SetupStep.allCases
        if let currentIndex = allSteps.firstIndex(of: step),
           currentIndex + 1 < allSteps.count
        {
            step = allSteps[currentIndex + 1]
        }
    }

    func previousStep() {
        let allSteps = SetupStep.allCases
        if let currentIndex = allSteps.firstIndex(of: step),
           currentIndex > 0
        {
            step = allSteps[currentIndex - 1]
        }
    }

    /// Check permissions and update published properties directly.
    func checkPermissions() {
        accessibilityGranted = AXIsProcessTrusted()
        screenRecordingGranted = checkScreenRecording()
    }

    /// Prompt for Accessibility permission.
    func requestAccessibility() {
        let options = [kAXTrustedCheckOptionPrompt.takeRetainedValue(): true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
        // Re-check shortly after
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
            self?.checkPermissions()
        }
    }

    /// Open Screen Recording settings.
    func openScreenRecordingSettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
            NSWorkspace.shared.open(url)
        }
    }

    /// Run Python setup.
    func setupPython() async {
        error = nil
        let projectDir = PythonDiscovery.projectDirectory()

        do {
            try await PythonSetup.performFullSetup(projectPath: projectDir.path) { [weak self] message, prog in
                Task { @MainActor [weak self] in
                    self?.statusMessage = message
                    self?.progress = prog
                }
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Save API key to keychain.
    func saveAPIKey(_ key: String) {
        guard !key.isEmpty else { return }
        do {
            try KeychainHelper.save(key: "ANTHROPIC_API_KEY", value: key)
        } catch {
            self.error = "Failed to save API key: \(error.localizedDescription)"
        }
    }

    func completeSetup() {
        isSetupComplete = true
        step = .complete
    }

    func resetSetup() {
        isSetupComplete = false
        step = .welcome
        progress = 0
        statusMessage = ""
        error = nil
    }

    // MARK: - Private

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
