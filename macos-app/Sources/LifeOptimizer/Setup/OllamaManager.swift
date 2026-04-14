import Foundation
import AppKit

/// Detects, installs, and starts Ollama on macOS.
///
/// Flow:
/// 1. Check if Ollama app is installed (in /Applications/Ollama.app)
/// 2. If not, install it by downloading the official .zip from ollama.com
/// 3. Check if it's running (HTTP /api/version on localhost:11434)
/// 4. If not running, launch it via `open -a Ollama`
/// 5. Optionally pull a default model (llama3.1:8b)
@MainActor
class OllamaManager: ObservableObject {
    @Published var status: Status = .idle
    @Published var progress: Double = 0
    @Published var message: String = ""
    @Published var error: String?
    @Published var availableModels: [String] = []

    enum Status {
        case idle
        case detecting
        case downloading
        case installing
        case starting
        case pullingModel
        case ready
        case failed
    }

    private let ollamaAppPath = "/Applications/Ollama.app"
    private let defaultModel = "qwen3.5:4b"
    private let downloadURL = URL(string: "https://ollama.com/download/Ollama-darwin.zip")!
    private let apiBase = "http://localhost:11434"

    /// Main entry point: make Ollama ready (install/start as needed).
    /// If any models are already installed, does NOT pull a new one — uses
    /// what the user already has. Only pulls the default if NO models exist.
    func ensureReady(installModel: Bool = true) async {
        error = nil
        do {
            status = .detecting
            message = "Checking for Ollama..."

            if !isInstalled() {
                try await install()
            }

            let running = await isRunning()
            if !running {
                try await start()
            }

            // Refresh model list
            await refreshModels()

            // Only pull the default model if the user has NO models installed.
            // Respects user's existing models (e.g. qwen).
            if installModel && availableModels.isEmpty {
                try await pullModel(defaultModel)
                await refreshModels()
            }

            // Pick the best model: prefer the hardcoded default (qwen3.5:4b)
            // if present, otherwise fall back to the first available.
            let chosen = pickBestModel()
            if let model = chosen {
                updatePythonConfig(provider: "ollama", model: model)
                message = "Using model: \(model)"
            }

            status = .ready
            progress = 1.0
        } catch {
            self.error = error.localizedDescription
            status = .failed
        }
    }

    // MARK: - Detection

    func isInstalled() -> Bool {
        FileManager.default.fileExists(atPath: ollamaAppPath)
            || FileManager.default.isExecutableFile(atPath: "/usr/local/bin/ollama")
            || FileManager.default.isExecutableFile(atPath: "/opt/homebrew/bin/ollama")
    }

    func isRunning() async -> Bool {
        guard let url = URL(string: "\(apiBase)/api/version") else { return false }
        var req = URLRequest(url: url, timeoutInterval: 2)
        req.httpMethod = "GET"
        do {
            let (_, response) = try await URLSession.shared.data(for: req)
            if let http = response as? HTTPURLResponse {
                return http.statusCode == 200
            }
        } catch {
            return false
        }
        return false
    }

    func hasModel(_ name: String) async -> Bool {
        guard let url = URL(string: "\(apiBase)/api/tags") else { return false }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let models = obj["models"] as? [[String: Any]]
            {
                return models.contains { ($0["name"] as? String)?.contains(name) == true }
            }
        } catch {
            return false
        }
        return false
    }

    /// Refresh the list of installed Ollama models.
    func refreshModels() async {
        guard let url = URL(string: "\(apiBase)/api/tags") else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let models = obj["models"] as? [[String: Any]]
            {
                let names = models.compactMap { $0["name"] as? String }
                availableModels = names.sorted()
            }
        } catch {
            // Silent — Ollama might not be running yet
        }
    }

    /// Pick the best model to use — prefer hardcoded default if installed,
    /// otherwise first available.
    func pickBestModel() -> String? {
        // Exact match for default
        if availableModels.contains(defaultModel) {
            return defaultModel
        }
        // Match any qwen3 variant
        if let qwen = availableModels.first(where: { $0.lowercased().contains("qwen") }) {
            return qwen
        }
        return availableModels.first
    }

    /// User manually picked a model.
    func selectModel(_ name: String) {
        UserDefaults.standard.set(name, forKey: "ollamaModel")
        updatePythonConfig(provider: "ollama", model: name)
        message = "Selected model: \(name)"
    }

    /// Update config.yaml: llm.provider and llm.ollama.model.
    /// Restarts the Python daemon + dashboard so changes take effect immediately.
    func updatePythonConfig(provider: String, model: String) {
        let home = FileManager.default.homeDirectoryForCurrentUser
        let configPath = home
            .appendingPathComponent("Documents/GitHub/life-optimizer/config.yaml")

        guard FileManager.default.fileExists(atPath: configPath.path),
              var content = try? String(contentsOf: configPath, encoding: .utf8)
        else {
            NSLog("[Ollama] config.yaml not found at \(configPath.path)")
            return
        }

        var lines = content.components(separatedBy: "\n")

        // Track current section: top-level = nil, llm, llm.ollama, etc.
        var inLLM = false
        var inOllama = false

        for i in 0..<lines.count {
            let line = lines[i]
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            let isTopLevel = !line.isEmpty && !line.hasPrefix(" ") && !line.hasPrefix("\t")

            // Reset context when we leave llm: section
            if isTopLevel {
                inLLM = trimmed.hasPrefix("llm:")
                inOllama = false
                continue
            }

            if inLLM {
                // Count leading spaces to figure out nesting
                let leading = line.prefix { $0 == " " }.count
                if leading == 2 && trimmed.hasPrefix("ollama:") {
                    inOllama = true
                    continue
                }
                if leading == 2 && !trimmed.hasPrefix("ollama:") {
                    inOllama = false
                }

                // Update llm.provider (at 2-space indent)
                if leading == 2 && trimmed.hasPrefix("provider:") {
                    lines[i] = "  provider: \(provider)"
                    continue
                }

                // Update llm.ollama.model (at 4-space indent under ollama:)
                if inOllama && leading == 4 && trimmed.hasPrefix("model:") {
                    lines[i] = "    model: \(model)"
                    continue
                }
            }
        }

        content = lines.joined(separator: "\n")
        do {
            try content.write(to: configPath, atomically: true, encoding: .utf8)
            NSLog("[Ollama] Updated config.yaml: provider=\(provider), model=\(model)")
        } catch {
            NSLog("[Ollama] Failed to update config.yaml: \(error)")
            return
        }

        // Restart Python processes so they load new config
        restartPythonBackend()
    }

    /// Kill Python daemon + dashboard. The Swift app's DaemonManager will
    /// respawn them via its termination handler / the user's next launch.
    private func restartPythonBackend() {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        task.arguments = ["-9", "-f", "life_optimizer (start|dashboard)"]
        try? task.run()
        task.waitUntilExit()
        NSLog("[Ollama] Killed Python daemon — Swift app will respawn")
    }

    // MARK: - Installation

    /// Download and install Ollama.app into /Applications.
    private func install() async throws {
        status = .downloading
        progress = 0
        message = "Downloading Ollama..."

        // Download to temp
        let tempDir = FileManager.default.temporaryDirectory
        let zipPath = tempDir.appendingPathComponent("Ollama-darwin.zip")
        try? FileManager.default.removeItem(at: zipPath)

        let (downloadURL, response) = try await URLSession.shared.download(from: self.downloadURL)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw NSError(
                domain: "OllamaManager", code: 1,
                userInfo: [NSLocalizedDescriptionKey: "Failed to download Ollama"]
            )
        }
        try FileManager.default.moveItem(at: downloadURL, to: zipPath)
        progress = 0.5

        status = .installing
        message = "Installing Ollama.app..."

        // Unzip into /Applications
        let unzipResult = try await runProcess(
            executable: "/usr/bin/ditto",
            arguments: ["-x", "-k", zipPath.path, "/Applications"]
        )
        guard unzipResult.exitCode == 0 else {
            throw NSError(
                domain: "OllamaManager", code: 2,
                userInfo: [NSLocalizedDescriptionKey: "Failed to install: \(unzipResult.stderr)"]
            )
        }

        try? FileManager.default.removeItem(at: zipPath)

        guard isInstalled() else {
            throw NSError(
                domain: "OllamaManager", code: 3,
                userInfo: [NSLocalizedDescriptionKey: "Installation completed but Ollama.app not found"]
            )
        }

        progress = 0.7
    }

    // MARK: - Starting

    /// Launch Ollama.app and wait for its server to come online.
    private func start() async throws {
        status = .starting
        message = "Starting Ollama..."

        // Launch Ollama.app (this starts the background server)
        let workspace = NSWorkspace.shared
        guard let appURL = URL(string: "file://\(ollamaAppPath)") else {
            throw NSError(domain: "OllamaManager", code: 4, userInfo: [NSLocalizedDescriptionKey: "Invalid Ollama path"])
        }

        let config = NSWorkspace.OpenConfiguration()
        config.activates = false
        config.hides = true

        _ = try await workspace.openApplication(at: appURL, configuration: config)

        // Poll up to 30 seconds for server to respond
        for i in 0..<30 {
            try await Task.sleep(nanoseconds: 1_000_000_000)
            if await isRunning() {
                progress = 0.85
                return
            }
            message = "Waiting for Ollama to start... (\(i+1)s)"
        }

        throw NSError(
            domain: "OllamaManager", code: 5,
            userInfo: [NSLocalizedDescriptionKey: "Ollama didn't start within 30 seconds"]
        )
    }

    // MARK: - Model pulling

    private func pullModel(_ name: String) async throws {
        status = .pullingModel
        message = "Downloading model \(name)..."

        // Use streaming pull API to show progress
        guard let url = URL(string: "\(apiBase)/api/pull") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: ["name": name])
        req.timeoutInterval = 3600 // 1 hour for large model download

        let (asyncBytes, response) = try await URLSession.shared.bytes(for: req)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw NSError(
                domain: "OllamaManager", code: 6,
                userInfo: [NSLocalizedDescriptionKey: "Failed to start model download"]
            )
        }

        for try await line in asyncBytes.lines {
            if let data = line.data(using: .utf8),
               let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            {
                if let statusStr = obj["status"] as? String {
                    message = "\(name): \(statusStr)"
                }
                if let total = obj["total"] as? Double, let completed = obj["completed"] as? Double,
                   total > 0
                {
                    progress = 0.85 + 0.15 * (completed / total)
                }
            }
        }
    }

    // MARK: - Helpers

    private struct ProcessResult {
        let exitCode: Int32
        let stdout: String
        let stderr: String
    }

    private func runProcess(executable: String, arguments: [String]) async throws -> ProcessResult {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = arguments
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        try process.run()
        process.waitUntilExit()

        let stdout = String(data: stdoutPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let stderr = String(data: stderrPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        return ProcessResult(exitCode: process.terminationStatus, stdout: stdout, stderr: stderr)
    }
}
