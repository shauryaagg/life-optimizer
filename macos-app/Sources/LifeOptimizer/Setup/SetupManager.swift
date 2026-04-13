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

    let permissionManager = PermissionManager()

    /// On init, verify that a previous "complete" setup is still valid.
    /// If the project directory doesn't have config.yaml, reset setup.
    func validateSetup() {
        guard isSetupComplete else { return }
        let projectDir = PythonDiscovery.projectDirectory()
        let configExists = FileManager.default.fileExists(
            atPath: projectDir.appendingPathComponent("config.yaml").path
        )
        let pythonPath = PythonDiscovery.findPython()
        let pythonExists = FileManager.default.isExecutableFile(atPath: pythonPath)

        if !configExists || !pythonExists {
            // Previous setup is invalid — reset
            isSetupComplete = false
            step = .welcome
        }
    }

    enum SetupStep: Int, CaseIterable {
        case welcome
        case permissions
        case pythonSetup
        case llmSetup
        case complete
    }

    /// Move to the next step.
    func nextStep() {
        let allSteps = SetupStep.allCases
        if let currentIndex = allSteps.firstIndex(of: step),
           currentIndex + 1 < allSteps.count
        {
            step = allSteps[currentIndex + 1]
        }
    }

    /// Move to the previous step.
    func previousStep() {
        let allSteps = SetupStep.allCases
        if let currentIndex = allSteps.firstIndex(of: step),
           currentIndex > 0
        {
            step = allSteps[currentIndex - 1]
        }
    }

    /// Check current permission status.
    func checkPermissions() {
        permissionManager.checkAll()
    }

    /// Request accessibility permission.
    func requestAccessibility() {
        permissionManager.requestAccessibility()
    }

    /// Open screen recording settings.
    func openScreenRecordingSettings() {
        permissionManager.openScreenRecordingSettings()
    }

    /// Run Python setup.
    func setupPython() async {
        error = nil
        let projectPath = UserDefaults.standard.string(forKey: "projectPath")
            ?? PythonDiscovery.projectDirectory().path

        do {
            try await PythonSetup.performFullSetup(projectPath: projectPath) { [weak self] message, prog in
                DispatchQueue.main.async {
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

    /// Complete setup and mark as done.
    func completeSetup() {
        isSetupComplete = true
        step = .complete
    }

    /// Reset setup state (for re-running setup).
    func resetSetup() {
        isSetupComplete = false
        step = .welcome
        progress = 0
        statusMessage = ""
        error = nil
    }
}
