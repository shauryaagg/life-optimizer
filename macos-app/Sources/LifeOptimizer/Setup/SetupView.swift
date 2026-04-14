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
    @State private var lastCheckedMessage: String = ""
    @State private var pollingTimer: Timer?

    var body: some View {
        VStack(spacing: 16) {
            Text("Permissions")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top, 20)

            Text("Life Optimizer needs **Accessibility** permission. Screen Recording is optional (for screenshots).")
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
                        Text("Detect which app is active")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    if setupManager.accessibilityGranted {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                            .font(.title3)
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

                // Screen Recording — optional, informational only
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Screen Recording")
                            .font(.headline)
                        Text("Optional — enable later in Settings for screenshots")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.secondary.opacity(0.05))
                )
            }
            .padding(.horizontal, 24)

            if !setupManager.accessibilityGranted {
                VStack(spacing: 4) {
                    Text("After granting Accessibility, you may need to quit and reopen Life Optimizer for it to take effect.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    if !lastCheckedMessage.isEmpty {
                        Text(lastCheckedMessage)
                            .font(.caption)
                            .foregroundColor(.orange)
                    }
                }
                .padding(.horizontal, 24)
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)

                Spacer()

                Button("Check Again") {
                    setupManager.checkAccessibility()
                    lastCheckedMessage = setupManager.accessibilityGranted
                        ? "✓ Granted!"
                        : "Not detected yet. Try quitting and reopening the app."
                }
                .buttonStyle(.bordered)

                Button("Continue") { setupManager.nextStep() }
                    .buttonStyle(.borderedProminent)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .onAppear {
            setupManager.checkAccessibility()
            pollingTimer = Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak setupManager] _ in
                Task { @MainActor in
                    setupManager?.checkAccessibility()
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
    @StateObject private var ollamaManager = OllamaManager()
    @State private var ollamaBusy = false

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
                VStack(alignment: .leading, spacing: 6) {
                    if ollamaBusy {
                        HStack {
                            ProgressView().controlSize(.small)
                            Text(ollamaManager.message)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        if ollamaManager.progress > 0 {
                            ProgressView(value: ollamaManager.progress)
                        }
                    } else if ollamaManager.status == .ready {
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                            Text("Ollama is ready with llama3.1:8b")
                                .font(.caption)
                        }
                    } else if ollamaManager.isInstalled() {
                        Text("Ollama is installed. We'll start it and pull llama3.1:8b when you click Continue.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    } else {
                        Text("Ollama is not installed. We'll download and install it for you when you click Continue.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    if let err = ollamaManager.error {
                        Text("Error: \(err)")
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
                .padding(.horizontal, 24)
            } else {
                Text("Activity tracking works without AI. Enable it later in Settings.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)
                    .disabled(ollamaBusy)
                Spacer()
                Button(ollamaBusy ? "Installing..." : "Continue") {
                    if llmProvider == "claude" {
                        if !apiKey.isEmpty {
                            setupManager.saveAPIKey(apiKey)
                        }
                        setupManager.nextStep()
                    } else if llmProvider == "ollama" {
                        // Auto-install and/or start Ollama
                        ollamaBusy = true
                        Task {
                            await ollamaManager.ensureReady(installModel: true)
                            ollamaBusy = false
                            if ollamaManager.error == nil {
                                setupManager.nextStep()
                            }
                        }
                    } else {
                        setupManager.nextStep()
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(ollamaBusy)
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
