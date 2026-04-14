import Foundation
import Combine

/// Manages the Python daemon and dashboard processes.
@MainActor
class DaemonManager: ObservableObject {
    @Published var isRunning = false
    @Published var statusIcon = "circle.fill"
    @Published var trackingStatus = "stopped"
    @Published var deepWorkMinutes: Int = 0
    @Published var eventCount: Int = 0

    private var daemonProcess: Process?
    private var dashboardProcess: Process?
    private var healthTimer: Timer?
    private var restartCount = 0
    private let maxRestarts = 3

    private let apiClient = APIClient()

    var deepWorkFormatted: String {
        let h = deepWorkMinutes / 60
        let m = deepWorkMinutes % 60
        return h > 0 ? "\(h)h \(m)m" : "\(m)m"
    }

    var statusColor: String {
        if isRunning {
            return trackingStatus == "active" ? "green" : "yellow"
        }
        return "red"
    }

    // MARK: - Lifecycle

    func startAll() {
        killOrphanedProcesses()
        startDaemon()
        startDashboard()
        startHealthMonitor()
    }

    /// Kill any orphaned life_optimizer Python processes from previous runs.
    /// This prevents multiple daemons from accumulating and hammering the system.
    private func killOrphanedProcesses() {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        task.arguments = ["-9", "-f", "life_optimizer (start|dashboard)"]
        do {
            try task.run()
            task.waitUntilExit()
            // pkill returns 1 if no matches, 0 if matched — both are fine
        } catch {
            // Best effort
        }
    }

    func stopAll() {
        healthTimer?.invalidate()
        healthTimer = nil

        if let process = daemonProcess, process.isRunning {
            process.terminate()
        }
        daemonProcess = nil

        if let process = dashboardProcess, process.isRunning {
            process.terminate()
        }
        dashboardProcess = nil

        isRunning = false
        trackingStatus = "stopped"
        updateStatusIcon()
    }

    // MARK: - Daemon

    private func startDaemon() {
        let python = PythonDiscovery.findPython()
        let projectDir = PythonDiscovery.projectDirectory()
        let logDir = PythonDiscovery.logDirectory()

        // Ensure log directory exists
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

        let process = Process()
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = ["-m", "life_optimizer", "start"]
        process.currentDirectoryURL = projectDir

        // Build environment
        var env = ProcessInfo.processInfo.environment
        if let apiKey = KeychainHelper.load(key: "ANTHROPIC_API_KEY") {
            env["ANTHROPIC_API_KEY"] = apiKey
        }
        process.environment = env

        // Redirect output to log files
        let stdoutFile = logDir.appendingPathComponent("daemon-stdout.log")
        let stderrFile = logDir.appendingPathComponent("daemon-stderr.log")
        FileManager.default.createFile(atPath: stdoutFile.path, contents: nil)
        FileManager.default.createFile(atPath: stderrFile.path, contents: nil)

        if let stdoutHandle = FileHandle(forWritingAtPath: stdoutFile.path),
           let stderrHandle = FileHandle(forWritingAtPath: stderrFile.path)
        {
            stdoutHandle.seekToEndOfFile()
            stderrHandle.seekToEndOfFile()
            process.standardOutput = stdoutHandle
            process.standardError = stderrHandle
        }

        process.terminationHandler = { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self = self else { return }
                // Brief delay to avoid rapid restart loops
                try? await Task.sleep(nanoseconds: 500_000_000)
                self.startDaemon()
            }
        }

        do {
            try process.run()
            daemonProcess = process
        } catch {
            print("Failed to start daemon: \(error)")
        }
    }

    // MARK: - Dashboard

    private func startDashboard() {
        let python = PythonDiscovery.findPython()
        let projectDir = PythonDiscovery.projectDirectory()
        let logDir = PythonDiscovery.logDirectory()

        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

        let process = Process()
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = ["-m", "life_optimizer", "dashboard"]
        process.currentDirectoryURL = projectDir

        var env = ProcessInfo.processInfo.environment
        if let apiKey = KeychainHelper.load(key: "ANTHROPIC_API_KEY") {
            env["ANTHROPIC_API_KEY"] = apiKey
        }
        process.environment = env

        let stdoutFile = logDir.appendingPathComponent("dashboard-stdout.log")
        let stderrFile = logDir.appendingPathComponent("dashboard-stderr.log")
        FileManager.default.createFile(atPath: stdoutFile.path, contents: nil)
        FileManager.default.createFile(atPath: stderrFile.path, contents: nil)

        if let stdoutHandle = FileHandle(forWritingAtPath: stdoutFile.path),
           let stderrHandle = FileHandle(forWritingAtPath: stderrFile.path)
        {
            stdoutHandle.seekToEndOfFile()
            stderrHandle.seekToEndOfFile()
            process.standardOutput = stdoutHandle
            process.standardError = stderrHandle
        }

        // Auto-respawn dashboard if killed (e.g. after config change)
        process.terminationHandler = { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self = self else { return }
                // Brief delay to avoid rapid restart loops
                try? await Task.sleep(nanoseconds: 500_000_000)
                self.startDashboard()
            }
        }

        do {
            try process.run()
            dashboardProcess = process
        } catch {
            print("Failed to start dashboard: \(error)")
        }
    }

    // MARK: - Health Monitor

    private func startHealthMonitor() {
        healthTimer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                await self?.checkHealth()
            }
        }
        // Run immediately
        Task { await checkHealth() }
    }

    private func checkHealth() async {
        do {
            let statusResp = try await apiClient.status()
            isRunning = statusResp.daemonRunning
            trackingStatus = statusResp.trackingStatus
            eventCount = statusResp.eventCount
            updateStatusIcon()

            // Fetch deep work stats
            let statsResp = try await apiClient.stats()
            deepWorkMinutes = statsResp.categoryBreakdown["Deep Work"] ?? 0
        } catch {
            // Backend might not be running yet
            isRunning = false
            updateStatusIcon()
        }
    }

    // MARK: - Status Icon

    private func updateStatusIcon() {
        if isRunning {
            statusIcon = trackingStatus == "active"
                ? "circle.fill"
                : "pause.circle.fill"
        } else {
            statusIcon = "xmark.circle.fill"
        }
    }
}
