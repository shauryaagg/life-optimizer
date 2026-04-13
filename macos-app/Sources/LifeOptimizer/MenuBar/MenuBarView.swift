import SwiftUI

/// Content of the MenuBarExtra dropdown — always shown.
struct MenuBarView: View {
    let appDelegate: AppDelegate

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Status section
            if appDelegate.daemonManager.isRunning {
                HStack {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 8, height: 8)
                    Text("Deep Work: \(appDelegate.daemonManager.deepWorkFormatted) today")
                        .font(.system(.body, design: .monospaced))
                }

                Text("\(appDelegate.daemonManager.eventCount) events tracked")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else if appDelegate.setupManager.isSetupComplete {
                HStack {
                    Circle()
                        .fill(Color.orange)
                        .frame(width: 8, height: 8)
                    Text("Starting...")
                        .foregroundColor(.secondary)
                }
            } else {
                HStack {
                    Circle()
                        .fill(Color.yellow)
                        .frame(width: 8, height: 8)
                    Text("Setup required")
                        .foregroundColor(.secondary)
                }
            }

            Divider()

            if appDelegate.setupManager.isSetupComplete {
                Button("Open Dashboard") {
                    DashboardWindowController.shared.openToPath("/")
                }
                .keyboardShortcut("d")

                Button("Ask a Question") {
                    appDelegate.toggleSpotlightPanel()
                }

                Button("Today's Insights") {
                    DashboardWindowController.shared.openToPath("/reports")
                }

                Divider()

                Button(appDelegate.daemonManager.isRunning ? "Pause Tracking" : "Resume Tracking") {
                    if appDelegate.daemonManager.isRunning {
                        appDelegate.daemonManager.stopAll()
                    } else {
                        appDelegate.daemonManager.startAll()
                    }
                }
            } else {
                Button("Run Setup...") {
                    appDelegate.showSetupWindow()
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
                appDelegate.daemonManager.stopAll()
                NSApp.terminate(nil)
            }
            .keyboardShortcut("q")
        }
        .padding(8)
    }
}
