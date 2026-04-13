import SwiftUI

/// Multi-step onboarding view for first-launch setup.
struct SetupView: View {
    @ObservedObject var setupManager: SetupManager

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
                    CompleteStepView(setupManager: setupManager)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(width: 500, height: 400)
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

            Text("Track your digital activity, gain insights, and optimize your productivity. This setup wizard will help you get started.")
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

    var body: some View {
        VStack(spacing: 16) {
            Text("Permissions")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top, 20)

            Text("Life Optimizer needs these permissions to track your activity:")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            VStack(spacing: 12) {
                PermissionRow(
                    title: "Accessibility",
                    description: "Required for tracking active windows and global hotkey",
                    isGranted: setupManager.permissionManager.accessibilityGranted,
                    action: { setupManager.requestAccessibility() }
                )

                PermissionRow(
                    title: "Screen Recording",
                    description: "Required for capturing screenshots for analysis",
                    isGranted: setupManager.permissionManager.screenRecordingGranted,
                    action: { setupManager.openScreenRecordingSettings() }
                )
            }
            .padding(.horizontal, 24)

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)
                Spacer()
                Button("Refresh") { setupManager.checkPermissions() }
                    .buttonStyle(.bordered)
                Button("Continue") { setupManager.nextStep() }
                    .buttonStyle(.borderedProminent)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .onAppear { setupManager.checkPermissions() }
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
                .fill(Color.secondary.opacity(0.05))
        )
    }
}

// MARK: - Step 3: Python Setup

struct PythonSetupStepView: View {
    @ObservedObject var setupManager: SetupManager
    @State private var projectPath: String = ""
    @State private var isRunning = false

    var body: some View {
        VStack(spacing: 16) {
            Text("Python Environment")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top, 20)

            Text("Life Optimizer needs Python 3.12+ to run the backend.")
                .font(.body)
                .foregroundColor(.secondary)

            VStack(alignment: .leading, spacing: 8) {
                Text("Project Path")
                    .font(.caption)
                    .foregroundColor(.secondary)
                HStack {
                    TextField("Path to life-optimizer project", text: $projectPath)
                        .textFieldStyle(.roundedBorder)
                    Button("Browse") {
                        let panel = NSOpenPanel()
                        panel.canChooseDirectories = true
                        panel.canChooseFiles = false
                        panel.allowsMultipleSelection = false
                        if panel.runModal() == .OK, let url = panel.url {
                            projectPath = url.path
                            UserDefaults.standard.set(projectPath, forKey: "projectPath")
                        }
                    }
                }
            }
            .padding(.horizontal, 24)

            if isRunning {
                VStack(spacing: 8) {
                    ProgressView(value: setupManager.progress)
                        .padding(.horizontal, 24)
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
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)
                Spacer()
                Button("Skip") { setupManager.nextStep() }
                    .buttonStyle(.bordered)
                Button("Install") {
                    isRunning = true
                    if !projectPath.isEmpty {
                        UserDefaults.standard.set(projectPath, forKey: "projectPath")
                    }
                    Task {
                        await setupManager.setupPython()
                        isRunning = false
                        if setupManager.error == nil {
                            setupManager.nextStep()
                        }
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isRunning)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .onAppear {
            projectPath = UserDefaults.standard.string(forKey: "projectPath") ?? ""
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

            Text("Choose your AI provider for activity analysis and chat.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Picker("Provider", selection: $llmProvider) {
                Text("Claude (Anthropic)").tag("claude")
                Text("Ollama (Local)").tag("ollama")
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
                    Text("Your key is stored securely in the macOS Keychain.")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 24)
            } else {
                Text("Make sure Ollama is running locally on port 11434.")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 24)
            }

            if let error = setupManager.error {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.horizontal, 24)
            }

            Spacer()

            HStack {
                Button("Back") { setupManager.previousStep() }
                    .buttonStyle(.bordered)
                Spacer()
                Button("Skip") { setupManager.nextStep() }
                    .buttonStyle(.bordered)
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

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 48))
                .foregroundColor(.green)

            Text("All Set!")
                .font(.title)
                .fontWeight(.bold)

            Text("Life Optimizer is ready. The daemon will start tracking your activity and you can ask questions anytime with Cmd+Shift+Space.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Spacer()

            Button("Start Life Optimizer") {
                setupManager.completeSetup()
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .padding(.bottom, 24)
        }
    }
}
