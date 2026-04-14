import SwiftUI
import AppKit

@main
struct LifeOptimizerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // Settings scene — accessible via Cmd+, and from menubar
        Settings {
            SettingsView(daemonManager: appDelegate.daemonManager)
        }
    }
}
