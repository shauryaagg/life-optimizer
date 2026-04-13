import SwiftUI

/// Content of the MenuBarExtra dropdown.
struct MenuBarView: View {
    @ObservedObject var daemonManager: DaemonManager
    let appDelegate: AppDelegate

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Status section
            if daemonManager.isRunning {
                HStack {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 8, height: 8)
                    Text("Deep Work: \(daemonManager.deepWorkFormatted) today")
                        .font(.system(.body, design: .monospaced))
                }

                Text("\(daemonManager.eventCount) events tracked")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                HStack {
                    Circle()
                        .fill(Color.red)
                        .frame(width: 8, height: 8)
                    Text("Not tracking")
                        .foregroundColor(.secondary)
                }
            }

            Divider()

            // Actions
            Button("Open Dashboard") {
                DashboardWindowController.shared.openToPath("/")
            }
            .keyboardShortcut("d")

            Button("Ask a Question") {
                appDelegate.toggleSpotlightPanel()
            }
            .keyboardShortcut(" ", modifiers: [.command, .shift])

            Button("Today's Insights") {
                DashboardWindowController.shared.openToPath("/reports")
            }

            Divider()

            Button(daemonManager.isRunning ? "Pause Tracking" : "Resume Tracking") {
                if daemonManager.isRunning {
                    daemonManager.stopAll()
                } else {
                    daemonManager.startAll()
                }
            }

            Divider()

            if #available(macOS 14.0, *) {
                SettingsLink {
                    Text("Settings...")
                }
            } else {
                Button("Settings...") {
                    NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                }
                .keyboardShortcut(",")
            }

            Button("Quit Life Optimizer") {
                daemonManager.stopAll()
                NSApp.terminate(nil)
            }
            .keyboardShortcut("q")
        }
        .padding(8)
    }
}

/// Minimal menu for use during setup.
struct SetupMenuView: View {
    @ObservedObject var setupManager: SetupManager

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Setup Required")
                .font(.headline)

            Text("Step \(setupManager.step.rawValue + 1) of \(SetupManager.SetupStep.allCases.count)")
                .font(.caption)
                .foregroundColor(.secondary)

            Divider()

            Button("Open Setup Window") {
                openSetupWindow(setupManager: setupManager)
            }

            Divider()

            Button("Quit") {
                NSApp.terminate(nil)
            }
            .keyboardShortcut("q")
        }
        .padding(8)
    }
}

/// Opens a standalone setup window.
func openSetupWindow(setupManager: SetupManager) {
    let window = NSWindow(
        contentRect: NSRect(x: 0, y: 0, width: 500, height: 400),
        styleMask: [.titled, .closable],
        backing: .buffered,
        defer: false
    )
    window.title = "Life Optimizer Setup"
    window.center()
    window.contentView = NSHostingView(rootView: SetupView(setupManager: setupManager))
    window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
}
