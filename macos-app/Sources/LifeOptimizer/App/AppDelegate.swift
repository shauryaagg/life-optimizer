import AppKit
import SwiftUI

/// Application delegate — owns ALL startup logic.
/// MenuBarExtra.onAppear only fires on click, so we drive everything from here.
@MainActor
class AppDelegate: NSObject, NSApplicationDelegate, ObservableObject {

    let daemonManager = DaemonManager()
    let setupManager = SetupManager()

    private var hotkeyManager = HotkeyManager()
    private var spotlightPanel: SpotlightPanel?
    private let chatViewModel = ChatViewModel()
    private var setupWindowController: NSWindowController?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Create spotlight panel (hidden initially)
        spotlightPanel = SpotlightPanel(chatViewModel: chatViewModel)

        // Register global hotkey
        hotkeyManager.register { [weak self] in
            self?.toggleSpotlightPanel()
        }

        // Decide: show onboarding or start daemon
        if setupManager.isSetupComplete {
            NSApp.setActivationPolicy(.accessory)
            daemonManager.startAll()
        } else {
            NSApp.setActivationPolicy(.regular)
            showSetupWindow()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        hotkeyManager.unregister()
        daemonManager.stopAll()
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
            self?.daemonManager.startAll()
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
