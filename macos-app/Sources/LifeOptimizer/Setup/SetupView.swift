import SwiftUI

/// Multi-step onboarding view for first-launch setup.
struct SetupView: View {
    @ObservedObject var setupManager: SetupManager
    var onComplete: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Progress indicator
            HStack(spacing: 4) {
                ForEach(SetupManager.SetupStep.allCases, id: \.rawValue) { step in
                    RoundedRectangle(cornerRadius: 2)
                        .fill(step.rawValue <= setupManager.step.rawValue
                              ? Color.accentColor
                              : Color.secondary.opacity(0.3))
                        .frame(height: 3)
                }
            }
            .padding(.horizontal, 24)
            .padding(.top, 16)

            // Step content
            Group {
                switch setupManager.step {
                case .welcome:
                    WelcomeStepView(setupManager: setupManager)
                case .permissions:
                    PermissionsStepView(setupManager: setupManager)
                case .pythonSetup:
                    PythonSetupStepView(setupManager: setupManager)
                case .llmSetup:
                    LLMSetupStepView(setupManager: setupManager)
                case .complete:
                    CompleteStepView(setupManager: setupManager, onComplete: onComplete)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(width: 520, height: 440)
    }
}

// MARK: - Step 1: Welcome

struct WelcomeStepView: View {
    @ObservedObject var setupManager: SetupManager

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "brain.head.profile")
                .font(.system(size: 48))
                .foregroundColor(.accentColor)

            Text("Welcome to Life Optimizer")
                .font(.title)
                .fontWeight(.bold)

            Text("Track your Mac activity, get AI-powered insights, and optimize how you spend your time. Everything stays 100% private on your machine.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Spacer()

            Button("Get Started") {
                setupManager.nextStep()
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .padding(.bottom, 24)
        }
    }
}

// MARK: - Step 2: Permissions

struct PermissionsStepView: View {
    @ObservedObject var setupManager: SetupManager
    @State private var pollingTimer: Timer?

    var body: some View {
        VStack(spacing: 16) {
            Text("Permissions")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top, 20)

            Text("Life Optimizer needs these macOS permissions to work:")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            VStack(spacing: 12) {
                PermissionRow(
                    title: "Accessibility",
                    description: "Track which app is active and enable the Cmd+Shift+Space hotkey",
                    isGranted: setupManager.permissionManager.accessibilityGranted,
                    action: { setupManager.requestAccessibility() }
                )

                PermissionRow(
                    title: "Screen Recording",
                    description: "Capture smart screenshots for context",
                    isGranted: setupManager.permissionManager.screenRecordingGranted,
                    action: { setupManager.openScreenRecordingSettings() }
                )
            }
            .padding(.horizontal, 24)

            if setupManager.permissionManager.accessibilityGranted {
                Text("Accessibility granted!")
                    .font(.caption)
                    .foregroundColor(.green)
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)
                Spacer()
                Button("Continue") { setupManager.nextStep() }
                    .buttonStyle(.borderedProminent)
                    // Allow continuing even without Screen Recording — it's optional
                    .disabled(!setupManager.permissionManager.accessibilityGranted)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .onAppear {
            setupManager.checkPermissions()
            // Poll every 2 seconds to detect permission grants
            pollingTimer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { _ in
                setupManager.checkPermissions()
            }
        }
        .onDisappear {
            pollingTimer?.invalidate()
        }
    }
}

struct PermissionRow: View {
    let title: String
    let description: String
    let isGranted: Bool
    let action: () -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            if isGranted {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                    .font(.title3)
            } else {
                Button("Grant") { action() }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isGranted ? Color.green.opacity(0.05) : Color.secondary.opacity(0.05))
        )
    }
}

// MARK: - Step 3: Python Setup

struct PythonSetupStepView: View {
    @ObservedObject var setupManager: SetupManager
    @State private var isRunning = false
    @State private var pythonStatus = "Checking..."
    @State private var detectedPython = ""

    var body: some View {
        VStack(spacing: 16) {
            Text("Python Environment")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top, 20)

            if !detectedPython.isEmpty {
                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                    Text("Python found: \(detectedPython)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            } else {
                HStack {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                    Text(pythonStatus)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Text("Life Optimizer will create an isolated Python environment and install all dependencies automatically.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            if isRunning {
                VStack(spacing: 8) {
                    ProgressView(value: setupManager.progress)
                        .padding(.horizontal, 40)
                    Text(setupManager.statusMessage)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            if let error = setupManager.error {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.horizontal, 24)
                    .lineLimit(3)
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)
                    .disabled(isRunning)
                Spacer()
                Button("Skip") { setupManager.nextStep() }
                    .buttonStyle(.bordered)
                    .disabled(isRunning)
                Button(isRunning ? "Installing..." : "Install") {
                    isRunning = true
                    Task {
                        await setupManager.setupPython()
                        isRunning = false
                        if setupManager.error == nil {
                            setupManager.nextStep()
                        }
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isRunning || detectedPython.isEmpty)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .onAppear {
            Task {
                let python = PythonDiscovery.findPython()
                if FileManager.default.isExecutableFile(atPath: python) {
                    detectedPython = python
                    pythonStatus = "Found"
                } else {
                    detectedPython = ""
                    pythonStatus = "Python 3.12+ not found. Install from python.org or Homebrew."
                }
            }
        }
    }
}

// MARK: - Step 4: LLM Setup

struct LLMSetupStepView: View {
    @ObservedObject var setupManager: SetupManager
    @AppStorage("llmProvider") var llmProvider: String = "claude"
    @State private var apiKey: String = ""

    var body: some View {
        VStack(spacing: 16) {
            Text("AI Provider")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top, 20)

            Text("Choose how Life Optimizer analyzes your activity.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Picker("Provider", selection: $llmProvider) {
                Text("Claude (Anthropic API)").tag("claude")
                Text("Ollama (100% Local)").tag("ollama")
                Text("None (Rule-based only)").tag("none")
            }
            .pickerStyle(.radioGroup)
            .padding(.horizontal, 24)

            if llmProvider == "claude" {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Anthropic API Key")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    SecureField("sk-ant-...", text: $apiKey)
                        .textFieldStyle(.roundedBorder)
                    Text("Stored securely in macOS Keychain. Only activity summaries are sent — never raw data.")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 24)
            } else if llmProvider == "ollama" {
                Text("Make sure Ollama is running at localhost:11434.")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 24)
            } else {
                Text("Activity tracking works without AI. You can enable it later in Settings.")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 24)
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)
                Spacer()
                Button("Continue") {
                    if llmProvider == "claude" && !apiKey.isEmpty {
                        setupManager.saveAPIKey(apiKey)
                    }
                    setupManager.nextStep()
                }
                .buttonStyle(.borderedProminent)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .onAppear {
            apiKey = KeychainHelper.load(key: "ANTHROPIC_API_KEY") ?? ""
        }
    }
}

// MARK: - Step 5: Complete

struct CompleteStepView: View {
    @ObservedObject var setupManager: SetupManager
    var onComplete: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 48))
                .foregroundColor(.green)

            Text("All Set!")
                .font(.title)
                .fontWeight(.bold)

            VStack(spacing: 8) {
                Text("Life Optimizer will appear in your menubar.")
                    .font(.body)
                    .foregroundColor(.secondary)

                Text("Press **Cmd + Shift + Space** anytime to ask questions about your day.")
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 40)

            Spacer()

            Button("Start Tracking") {
                setupManager.completeSetup()
                onComplete()
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .padding(.bottom, 24)
        }
    }
}
