import AppKit
import SwiftUI
import CoreGraphics

/// Application delegate — owns ALL startup logic.
/// MenuBarExtra.onAppear only fires on click, so we drive everything from here.
@MainActor
class AppDelegate: NSObject, NSApplicationDelegate, ObservableObject {

    let daemonManager = DaemonManager()
    let setupManager = SetupManager()
    let screenshotCapture = ScreenshotCapture(interval: 30)
    let statusItemManager = StatusItemManager()

    private var hotkeyManager = HotkeyManager()
    private var spotlightPanel: SpotlightPanel?
    private let chatViewModel = ChatViewModel()
    private var setupWindowController: NSWindowController?
    private var workspaceObserver: NSObjectProtocol?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Clean up stale TCC grants on launch.
        //
        // Ad-hoc signed binaries change their code hash on every rebuild.
        // macOS TCC keys grants by hash, so after rebuild the grant for the
        // OLD hash is still in System Settings (showing "Life Optimizer" as
        // allowed) but the new hash has no grant — and the user can't re-grant
        // because Settings shows it's already on.
        //
        // `tccutil reset` removes the stale entry. After reset, next capture
        // attempt triggers a fresh, clean permission prompt.
        //
        // We only do this if the CURRENT binary doesn't have a grant
        // (CGPreflightScreenCaptureAccess == false). If the current binary
        // has a valid grant, we don't touch anything.
        resetStaleTCCIfNeeded()

        // Set activation policy FIRST — must be done before any UI or the
        // status bar subsystem may not render properly
        if setupManager.isSetupComplete {
            NSApp.setActivationPolicy(.accessory)
        } else {
            NSApp.setActivationPolicy(.regular)
        }

        // Install menubar status item (after activation policy is set)
        statusItemManager.install(appDelegate: self)

        // Create spotlight panel (hidden initially)
        spotlightPanel = SpotlightPanel(chatViewModel: chatViewModel)

        // Register global hotkey
        hotkeyManager.register { [weak self] in
            self?.toggleSpotlightPanel()
        }

        // Start appropriate flow
        if setupManager.isSetupComplete {
            startTracking()
        } else {
            showSetupWindow()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        hotkeyManager.unregister()
        screenshotCapture.stop()
        if let observer = workspaceObserver {
            NSWorkspace.shared.notificationCenter.removeObserver(observer)
        }
        daemonManager.stopAll()
    }

    // MARK: - Tracking lifecycle

    /// Start both the Python daemon (for activity tracking) AND the Swift-side
    /// screenshot capture (which uses the Swift app's TCC permissions).
    private func startTracking() {
        daemonManager.startAll()
        screenshotCapture.start()

        // Listen for app switches to trigger immediate screenshots
        workspaceObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            if let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication,
               let name = app.localizedName {
                Task { @MainActor [weak self] in
                    self?.screenshotCapture.captureOnAppSwitch(appName: name)
                }
            }
        }
    }

    // MARK: - Setup Window

    func showSetupWindow() {
        // If already showing, just bring to front
        if let wc = setupWindowController, let w = wc.window, w.isVisible {
            w.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 520, height: 440),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.title = "Life Optimizer Setup"
        window.center()
        window.isReleasedWhenClosed = false

        let setupView = SetupView(setupManager: setupManager) { [weak self] in
            // Called when setup is complete — switch to menubar-only mode
            self?.setupWindowController?.close()
            self?.setupWindowController = nil
            NSApp.setActivationPolicy(.accessory)
            self?.startTracking()
        }
        window.contentView = NSHostingView(rootView: setupView)

        let controller = NSWindowController(window: window)
        controller.showWindow(nil)
        setupWindowController = controller

        NSApp.activate(ignoringOtherApps: true)
    }

    // MARK: - Spotlight Panel

    func toggleSpotlightPanel() {
        spotlightPanel?.toggle()
    }

    // MARK: - TCC Cleanup

    /// If the current binary has no Screen Recording grant, reset stale TCC
    /// entries so System Settings doesn't show "already granted" incorrectly.
    private func resetStaleTCCIfNeeded() {
        let bundleID = Bundle.main.bundleIdentifier ?? "com.lifeoptimizer.app"

        // If preflight returns true, we DO have a grant — don't touch anything
        if CGPreflightScreenCaptureAccess() {
            NSLog("[TCC] Screen Recording grant is valid, no cleanup needed")
            return
        }

        NSLog("[TCC] No valid Screen Recording grant — clearing stale TCC entries")

        // tccutil reset <service> <bundle-id> removes the stale entry so the
        // next permission prompt shows fresh and System Settings reflects
        // actual state.
        for service in ["ScreenCapture", "Accessibility"] {
            let task = Process()
            task.executableURL = URL(fileURLWithPath: "/usr/bin/tccutil")
            task.arguments = ["reset", service, bundleID]
            task.standardOutput = Pipe()
            task.standardError = Pipe()
            do {
                try task.run()
                task.waitUntilExit()
                NSLog("[TCC] Reset \(service) for \(bundleID): exit \(task.terminationStatus)")
            } catch {
                NSLog("[TCC] Failed to reset \(service): \(error)")
            }
        }
    }
}
