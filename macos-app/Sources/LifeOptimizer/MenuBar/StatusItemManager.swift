import AppKit
import SwiftUI
import Combine

/// Manages the menubar status item using classic NSStatusItem.
/// This works reliably with Swift Package Manager builds, unlike MenuBarExtra
/// which has known rendering issues outside of Xcode-built apps.
@MainActor
class StatusItemManager: ObservableObject {
    private var statusItem: NSStatusItem?
    private var popover: NSPopover?
    private var cancellables = Set<AnyCancellable>()
    private weak var appDelegate: AppDelegate?

    func install(appDelegate: AppDelegate) {
        self.appDelegate = appDelegate

        // Create the status item
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem = item

        // Set initial icon
        updateIcon()

        // Configure button action
        if let button = item.button {
            button.action = #selector(togglePopover(_:))
            button.target = self
        }

        // Setup popover with menu content
        let popover = NSPopover()
        popover.contentSize = NSSize(width: 280, height: 320)
        popover.behavior = .transient
        popover.animates = true
        let contentView = MenuBarView(appDelegate: appDelegate)
        popover.contentViewController = NSHostingController(rootView: contentView)
        self.popover = popover

        // Observe daemon manager to update icon color
        appDelegate.daemonManager.$isRunning
            .sink { [weak self] _ in
                Task { @MainActor in self?.updateIcon() }
            }
            .store(in: &cancellables)

        appDelegate.daemonManager.$statusIcon
            .sink { [weak self] _ in
                Task { @MainActor in self?.updateIcon() }
            }
            .store(in: &cancellables)
    }

    func uninstall() {
        if let item = statusItem {
            NSStatusBar.system.removeStatusItem(item)
        }
        statusItem = nil
        cancellables.removeAll()
    }

    private func updateIcon() {
        guard let button = statusItem?.button else { return }
        let isRunning = appDelegate?.daemonManager.isRunning ?? false

        // Try multiple SF Symbol names that should exist on macOS 13+
        let symbolCandidates = ["target", "viewfinder", "circle.dashed", "circle", "record.circle"]
        var symbolImage: NSImage?
        let config = NSImage.SymbolConfiguration(pointSize: 15, weight: .medium)

        for name in symbolCandidates {
            if let img = NSImage(systemSymbolName: name, accessibilityDescription: "Life Optimizer") {
                symbolImage = img.withSymbolConfiguration(config)
                break
            }
        }

        if let image = symbolImage {
            image.isTemplate = true
            button.image = image
            button.title = ""
        } else {
            // Fallback to text - guaranteed to show something
            button.image = nil
            button.title = "◎"
            button.font = NSFont.systemFont(ofSize: 16, weight: .medium)
        }

        button.toolTip = isRunning
            ? "Life Optimizer — tracking"
            : "Life Optimizer — click to start"
    }

    @objc private func togglePopover(_ sender: AnyObject?) {
        guard let popover = popover, let button = statusItem?.button else { return }
        if popover.isShown {
            popover.performClose(sender)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            popover.contentViewController?.view.window?.becomeKey()
        }
    }
}
