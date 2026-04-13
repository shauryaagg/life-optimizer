import SwiftUI

/// Preferences window with tabs for General, AI Provider, and About.
struct SettingsView: View {
    @ObservedObject var daemonManager: DaemonManager

    var body: some View {
        TabView {
            GeneralSettingsView()
                .tabItem { Label("General", systemImage: "gear") }

            LLMSettingsView()
                .tabItem { Label("AI Provider", systemImage: "brain") }

            AboutSettingsView()
                .tabItem { Label("About", systemImage: "info.circle") }
        }
        .frame(width: 450, height: 300)
    }
}

// MARK: - General Settings

struct GeneralSettingsView: View {
    @AppStorage("pythonPath") var pythonPath: String = ""
    @AppStorage("projectPath") var projectPath: String = ""
    @AppStorage("screenshotInterval") var screenshotInterval: Double = 30.0
    @AppStorage("launchAtLogin") var launchAtLogin: Bool = false

    var body: some View {
        Form {
            Section {
                HStack {
                    TextField("Python Path", text: $pythonPath)
                        .textFieldStyle(.roundedBorder)
                    Button("Detect") {
                        pythonPath = PythonDiscovery.findPython()
                    }
                }
                HStack {
                    TextField("Project Path", text: $projectPath)
                        .textFieldStyle(.roundedBorder)
                    Button("Browse") {
                        let panel = NSOpenPanel()
                        panel.canChooseDirectories = true
                        panel.canChooseFiles = false
                        if panel.runModal() == .OK, let url = panel.url {
                            projectPath = url.path
                        }
                    }
                }
            } header: {
                Text("Paths")
            }

            Section {
                Slider(value: $screenshotInterval, in: 10...120, step: 5) {
                    Text("Screenshot Interval: \(Int(screenshotInterval))s")
                }
                Toggle("Launch at Login", isOn: $launchAtLogin)
            } header: {
                Text("Tracking")
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - LLM Settings

struct LLMSettingsView: View {
    @AppStorage("llmProvider") var llmProvider: String = "claude"
    @State private var apiKey: String = ""
    @State private var saveStatus: String?

    var body: some View {
        Form {
            Section {
                Picker("Provider", selection: $llmProvider) {
                    Text("Claude (Anthropic)").tag("claude")
                    Text("Ollama (Local)").tag("ollama")
                }
            } header: {
                Text("AI Provider")
            }

            if llmProvider == "claude" {
                Section {
                    SecureField("API Key", text: $apiKey)
                        .textFieldStyle(.roundedBorder)
                    HStack {
                        Button("Save to Keychain") {
                            do {
                                try KeychainHelper.save(key: "ANTHROPIC_API_KEY", value: apiKey)
                                saveStatus = "Saved"
                            } catch {
                                saveStatus = "Error: \(error.localizedDescription)"
                            }
                        }
                        if let status = saveStatus {
                            Text(status)
                                .font(.caption)
                                .foregroundColor(status == "Saved" ? .green : .red)
                        }
                    }
                } header: {
                    Text("Anthropic API Key")
                }
            }

            if llmProvider == "ollama" {
                Section {
                    Text("Make sure Ollama is running on http://localhost:11434")
                        .font(.caption)
                        .foregroundColor(.secondary)
                } header: {
                    Text("Ollama")
                }
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear {
            apiKey = KeychainHelper.load(key: "ANTHROPIC_API_KEY") ?? ""
        }
    }
}

// MARK: - About

struct AboutSettingsView: View {
    var body: some View {
        VStack(spacing: 16) {
            Spacer()

            Image(systemName: "brain.head.profile")
                .font(.system(size: 36))
                .foregroundColor(.accentColor)

            Text("Life Optimizer")
                .font(.title2)
                .fontWeight(.bold)

            Text("Version 0.1.0")
                .font(.caption)
                .foregroundColor(.secondary)

            Text("Track your digital activity, gain AI-powered insights, and optimize your productivity.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Spacer()
        }
    }
}
