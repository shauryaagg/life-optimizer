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

    // Permissions
    @Published var accessibilityGranted: Bool = false

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

    /// Check accessibility only — no side effects, no spawning processes.
    func checkAccessibility() {
        accessibilityGranted = AXIsProcessTrusted()
    }

    /// Prompt for Accessibility permission (one-shot, not in a loop).
    func requestAccessibility() {
        let options = [kAXTrustedCheckOptionPrompt.takeRetainedValue(): true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
    }

    /// Open Screen Recording settings.
    func openScreenRecordingSettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
            NSWorkspace.shared.open(url)
        }
    }

    /// Open Accessibility settings.
    func openAccessibilitySettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
            NSWorkspace.shared.open(url)
        }
    }

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
}
