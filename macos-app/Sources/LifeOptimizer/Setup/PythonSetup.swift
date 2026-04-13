import Foundation

/// Handles Python environment setup: finding Python, creating venv, installing package.
struct PythonSetup {

    enum SetupError: LocalizedError {
        case pythonNotFound
        case venvCreationFailed(String)
        case pipInstallFailed(String)

        var errorDescription: String? {
            switch self {
            case .pythonNotFound:
                return "Python 3 not found. Please install Python 3.12+ via Homebrew or python.org."
            case .venvCreationFailed(let msg):
                return "Failed to create virtual environment: \(msg)"
            case .pipInstallFailed(let msg):
                return "Failed to install dependencies: \(msg)"
            }
        }
    }

    /// Find Python and verify version >= 3.12.
    static func findAndVerifyPython() async throws -> String {
        let python = PythonDiscovery.findPython()

        let result = try await ProcessHelper.run(
            python,
            arguments: ["--version"]
        )

        guard result.exitCode == 0 else {
            throw SetupError.pythonNotFound
        }

        // Verify version is >= 3.12
        let versionString = result.stdout.trimmingCharacters(in: .whitespacesAndNewlines)
        // Format: "Python 3.12.x"
        if let range = versionString.range(of: #"(\d+)\.(\d+)"#, options: .regularExpression),
           let major = Int(versionString[range].split(separator: ".")[0]),
           let minor = Int(versionString[range].split(separator: ".")[1])
        {
            guard major >= 3 && minor >= 12 else {
                throw SetupError.pythonNotFound
            }
        }

        return python
    }

    /// Create a virtual environment in the app support directory.
    static func createVirtualEnvironment(pythonPath: String) async throws -> String {
        let appSupport = PythonDiscovery.appSupportDir()
        try FileManager.default.createDirectory(at: appSupport, withIntermediateDirectories: true)

        let venvPath = appSupport.appendingPathComponent("venv")

        let result = try await ProcessHelper.run(
            pythonPath,
            arguments: ["-m", "venv", venvPath.path]
        )

        guard result.exitCode == 0 else {
            throw SetupError.venvCreationFailed(result.stderr)
        }

        let venvPython = venvPath.appendingPathComponent("bin/python3").path
        guard FileManager.default.isExecutableFile(atPath: venvPython) else {
            throw SetupError.venvCreationFailed("venv python not found at \(venvPython)")
        }

        return venvPython
    }

    /// Install the life_optimizer package into the venv.
    static func installPackage(venvPython: String, projectPath: String) async throws {
        let result = try await ProcessHelper.run(
            venvPython,
            arguments: ["-m", "pip", "install", "-e", projectPath],
            workingDirectory: URL(fileURLWithPath: projectPath)
        )

        guard result.exitCode == 0 else {
            throw SetupError.pipInstallFailed(result.stderr)
        }
    }

    /// Full setup: find Python, create venv, install package.
    static func performFullSetup(
        projectPath: String,
        onProgress: @escaping (String, Double) -> Void
    ) async throws {
        onProgress("Finding Python...", 0.1)
        let python = try await findAndVerifyPython()

        onProgress("Creating virtual environment...", 0.3)
        let venvPython = try await createVirtualEnvironment(pythonPath: python)

        onProgress("Installing Life Optimizer...", 0.5)
        try await installPackage(venvPython: venvPython, projectPath: projectPath)

        onProgress("Verifying installation...", 0.9)
        let installed = await PythonDiscovery.isPackageInstalled(pythonPath: venvPython)
        guard installed else {
            throw SetupError.pipInstallFailed("Package verification failed")
        }

        onProgress("Setup complete!", 1.0)
    }
}
