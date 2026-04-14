import AppKit
import SwiftUI

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
        // Install the menubar status item FIRST (always visible)
        statusItemManager.install(appDelegate: self)

        // Create spotlight panel (hidden initially)
        spotlightPanel = SpotlightPanel(chatViewModel: chatViewModel)

        // Register global hotkey
        hotkeyManager.register { [weak self] in
            self?.toggleSpotlightPanel()
        }

        // Decide: show onboarding or start daemon
        if setupManager.isSetupComplete {
            NSApp.setActivationPolicy(.accessory)
            startTracking()
        } else {
            NSApp.setActivationPolicy(.regular)
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
}
