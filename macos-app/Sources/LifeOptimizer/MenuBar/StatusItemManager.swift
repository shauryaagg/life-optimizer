import AppKit
import SwiftUI

/// Manages the menu bar status item icon color based on daemon state.
@MainActor
class StatusItemManager: ObservableObject {
    @Published var iconName: String = "circle.fill"
    @Published var iconColor: NSColor = .systemGray

    /// Update icon based on daemon status.
    func update(isRunning: Bool, trackingStatus: String) {
        if isRunning {
            if trackingStatus == "active" {
                iconName = "circle.fill"
                iconColor = .systemGreen
            } else {
                iconName = "pause.circle.fill"
                iconColor = .systemYellow
            }
        } else {
            iconName = "xmark.circle.fill"
            iconColor = .systemRed
        }
    }
}
