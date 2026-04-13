import SwiftUI
import AppKit

@main
struct LifeOptimizerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        MenuBarExtra {
            MenuBarView(appDelegate: appDelegate)
        } label: {
            Label {
                Text("Life Optimizer")
            } icon: {
                Image(systemName: appDelegate.daemonManager.statusIcon)
                    .symbolRenderingMode(.palette)
                    .foregroundStyle(appDelegate.daemonManager.isRunning ? .green : .secondary)
            }
        }

        Settings {
            SettingsView(daemonManager: appDelegate.daemonManager)
        }
    }
}
