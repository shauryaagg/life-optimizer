import SwiftUI

/// Multi-step onboarding view for first-launch setup.
struct SetupView: View {
    @ObservedObject var setupManager: SetupManager
    var onComplete: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Progress bar
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
    @State private var hasRequestedAccessibility = false
    @State private var pollingTimer: Timer?

    var body: some View {
        VStack(spacing: 16) {
            Text("Permissions")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top, 20)

            Text("Life Optimizer needs macOS permissions to track your activity.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 30)

            VStack(spacing: 12) {
                // Accessibility
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Accessibility")
                            .font(.headline)
                        Text("Required to detect which app is active")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    if setupManager.accessibilityGranted {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                            .font(.title3)
                    } else if !hasRequestedAccessibility {
                        Button("Grant") {
                            hasRequestedAccessibility = true
                            setupManager.requestAccessibility()
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    } else {
                        Button("Open Settings") {
                            setupManager.openAccessibilitySettings()
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(setupManager.accessibilityGranted
                              ? Color.green.opacity(0.05)
                              : Color.secondary.opacity(0.05))
                )

                // Screen Recording — informational only
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Screen Recording")
                            .font(.headline)
                        Text("Optional — for smart screenshots")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Button("Open Settings") {
                        setupManager.openScreenRecordingSettings()
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.secondary.opacity(0.05))
                )
            }
            .padding(.horizontal, 24)

            if hasRequestedAccessibility && !setupManager.accessibilityGranted {
                Text("After granting in System Settings, click \"Check Again\" below.")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 24)
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)

                Spacer()

                if hasRequestedAccessibility && !setupManager.accessibilityGranted {
                    Button("Check Again") {
                        setupManager.checkAccessibility()
                    }
                    .buttonStyle(.bordered)
                }

                Button("Continue") { setupManager.nextStep() }
                    .buttonStyle(.borderedProminent)
                    .disabled(!setupManager.accessibilityGranted)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .onAppear {
            setupManager.checkAccessibility()
            // Light polling — just reads AXIsProcessTrusted(), no side effects
            pollingTimer = Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { _ in
                Task { @MainActor in
                    setupManager.checkAccessibility()
                }
            }
        }
        .onDisappear {
            pollingTimer?.invalidate()
            pollingTimer = nil
        }
    }
}

// MARK: - Step 3: Python Setup

struct PythonSetupStepView: View {
    @ObservedObject var setupManager: SetupManager
    @State private var isRunning = false
    @State private var detectedPython = ""
    @State private var pythonStatus = "Checking..."

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
                    Text("Found: \(detectedPython)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            } else {
                HStack {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                    Text(pythonStatus)
                        .font(.caption)
                        .foregroundColor(.red)
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
                    .lineLimit(4)
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
            let python = PythonDiscovery.findPython()
            if FileManager.default.isExecutableFile(atPath: python) {
                detectedPython = python
            } else {
                pythonStatus = "Python 3.12+ not found. Install from python.org or Homebrew."
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
                    Text("Stored in macOS Keychain. Only summaries sent to API, never raw data.")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 24)
            } else if llmProvider == "ollama" {
                Text("Make sure Ollama is running at localhost:11434.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                Text("Activity tracking works without AI. Enable it later in Settings.")
                    .font(.caption)
                    .foregroundColor(.secondary)
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
                Text("Press **Cmd + Shift + Space** anytime to ask questions.")
            }
            .font(.body)
            .foregroundColor(.secondary)
            .multilineTextAlignment(.center)
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
