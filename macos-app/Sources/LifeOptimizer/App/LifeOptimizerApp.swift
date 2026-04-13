import SwiftUI
import AppKit

@main
struct LifeOptimizerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var daemonManager = DaemonManager()
    @StateObject private var setupManager = SetupManager()

    var body: some Scene {
        MenuBarExtra {
            if setupManager.isSetupComplete {
                MenuBarView(daemonManager: daemonManager, appDelegate: appDelegate)
                    .onAppear {
                        daemonManager.startAll()
                    }
            } else {
                SetupMenuView(setupManager: setupManager)
                    .onAppear {
                        // Auto-open setup window on first launch
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                            openSetupWindow(setupManager: setupManager)
                        }
                    }
            }
        } label: {
            Image(systemName: daemonManager.statusIcon)
        }

        Settings {
            SettingsView(daemonManager: daemonManager)
        }
    }
}
