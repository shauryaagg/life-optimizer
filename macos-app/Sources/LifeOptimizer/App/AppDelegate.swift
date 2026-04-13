import AppKit
import SwiftUI

/// Application delegate for lifecycle management and global hotkey.
@MainActor
class AppDelegate: NSObject, NSApplicationDelegate, ObservableObject {

    private var hotkeyManager = HotkeyManager()
    private var spotlightPanel: SpotlightPanel?
    private let chatViewModel = ChatViewModel()

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Set as accessory app (menubar only, no dock icon)
        NSApp.setActivationPolicy(.accessory)

        // Register global hotkey (Cmd+Shift+Space)
        registerHotkey()

        // Create the spotlight panel
        spotlightPanel = SpotlightPanel(chatViewModel: chatViewModel)

        // Check accessibility permission and warn if not granted
        if !HotkeyManager.isAccessibilityGranted {
            showAccessibilityWarning()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        hotkeyManager.unregister()
    }

    // MARK: - Spotlight Panel

    func toggleSpotlightPanel() {
        spotlightPanel?.toggle()
    }

    // MARK: - Hotkey Registration

    private func registerHotkey() {
        hotkeyManager.register { [weak self] in
            self?.toggleSpotlightPanel()
        }
    }

    // MARK: - Accessibility Warning

    private func showAccessibilityWarning() {
        // The global hotkey requires Accessibility permission.
        // We prompt on first launch via PermissionManager, but also
        // check here in case the user hasn't granted it.
        let options = [kAXTrustedCheckOptionPrompt.takeRetainedValue(): true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
    }
}
