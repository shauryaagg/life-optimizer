import SwiftUI
import AppKit

@main
struct LifeOptimizerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var daemonManager = DaemonManager()
    @StateObject private var setupManager = SetupManager()
    @State private var hasStartedDaemon = false
    @State private var hasOpenedSetup = false

    var body: some Scene {
        MenuBarExtra {
            if setupManager.isSetupComplete {
                MenuBarView(daemonManager: daemonManager, appDelegate: appDelegate)
                    .onAppear {
                        if !hasStartedDaemon {
                            hasStartedDaemon = true
                            daemonManager.startAll()
                        }
                    }
            } else {
                SetupMenuView(setupManager: setupManager)
                    .onAppear {
                        if !hasOpenedSetup {
                            hasOpenedSetup = true
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                                openSetupWindow(setupManager: setupManager)
                            }
                        }
                    }
            }
        } label: {
            Label {
                Text("Life Optimizer")
            } icon: {
                Image(systemName: daemonManager.statusIcon)
                    .symbolRenderingMode(.palette)
                    .foregroundStyle(daemonManager.isRunning ? .green : .red)
            }
        }

        Settings {
            SettingsView(daemonManager: daemonManager)
        }
    }

    init() {
        // Validate that previous setup is still valid on launch
        let manager = SetupManager()
        manager.validateSetup()
    }
}
