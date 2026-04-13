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
        if let stored = UserDefaults.standard.string(forKey: "projectPath"),
           !stored.isEmpty
        {
            return URL(fileURLWithPath: stored)
        }
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
