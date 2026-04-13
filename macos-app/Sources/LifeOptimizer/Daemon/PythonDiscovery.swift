import Foundation

/// Discovers Python executable and project paths.
struct PythonDiscovery {

    /// Find the best available Python 3 executable.
    static func findPython() -> String {
        let candidates: [String?] = [
            UserDefaults.standard.string(forKey: "pythonPath"),
            appSupportDir().appendingPathComponent("venv/bin/python3").path,
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]

        for candidate in candidates.compactMap({ $0 }) {
            if FileManager.default.isExecutableFile(atPath: candidate) {
                return candidate
            }
        }
        return "/usr/bin/python3"
    }

    /// Get the Life Optimizer Python project directory.
    static func projectDirectory() -> URL {
        // 1. User-configured path
        if let stored = UserDefaults.standard.string(forKey: "projectPath"),
           !stored.isEmpty,
           FileManager.default.fileExists(atPath: stored + "/config.yaml")
        {
            return URL(fileURLWithPath: stored)
        }

        // 2. Check if we're inside the project repo (development mode)
        //    Walk up from the executable to find config.yaml
        if let execURL = Bundle.main.executableURL {
            var dir = execURL.deletingLastPathComponent()
            for _ in 0..<6 {
                let configPath = dir.appendingPathComponent("config.yaml").path
                if FileManager.default.fileExists(atPath: configPath) {
                    return dir
                }
                dir = dir.deletingLastPathComponent()
            }
        }

        // 3. Check common development location
        let home = FileManager.default.homeDirectoryForCurrentUser
        let devPath = home.appendingPathComponent("Documents/GitHub/life-optimizer")
        if FileManager.default.fileExists(atPath: devPath.appendingPathComponent("config.yaml").path) {
            return devPath
        }

        // 4. Fall back to Application Support
        return appSupportDir()
    }

    /// Get the Application Support directory for Life Optimizer.
    static func appSupportDir() -> URL {
        let appSupport = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        )[0]
        return appSupport.appendingPathComponent("LifeOptimizer")
    }

    /// Get the log directory.
    static func logDirectory() -> URL {
        let home = FileManager.default.homeDirectoryForCurrentUser
        return home
            .appendingPathComponent("Library")
            .appendingPathComponent("Logs")
            .appendingPathComponent("LifeOptimizer")
    }

    /// Check if Python has the life_optimizer package installed.
    static func isPackageInstalled(pythonPath: String) async -> Bool {
        do {
            let result = try await ProcessHelper.run(
                pythonPath,
                arguments: ["-c", "import life_optimizer; print('ok')"]
            )
            return result.exitCode == 0 && result.stdout.contains("ok")
        } catch {
            return false
        }
    }
}
