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
        debugLog("[StatusItem] install() called")

        // Create the status item with fixed length to ensure visibility
        let item = NSStatusBar.system.statusItem(withLength: 30)
        statusItem = item
        // autosaveName persists the position across launches and asks macOS
        // to prefer this placement — helps avoid being pushed into the notch
        // dead zone on MacBooks with many status items.
        item.autosaveName = "com.lifeoptimizer.app.statusitem"
        item.behavior = [.removalAllowed]
        debugLog("[StatusItem] created, button=\(item.button != nil)")

        // Configure button FIRST
        if let button = item.button {
            button.action = #selector(togglePopover(_:))
            button.target = self
            // Force a visible text label — guaranteed to render
            button.title = "LO"
            button.font = NSFont.systemFont(ofSize: 13, weight: .semibold)
            button.imagePosition = .imageLeft
            debugLog("[StatusItem] button configured, title='\(button.title)', frame=\(button.frame)")
        }

        // Set icon after button is configured
        updateIcon()

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
        guard let button = statusItem?.button else {
            debugLog("[StatusItem.updateIcon] NO BUTTON — bailing")
            return
        }
        let isRunning = appDelegate?.daemonManager.isRunning ?? false

        // Keep text-only for now — proven to render reliably
        button.title = "LO"
        button.image = nil

        button.toolTip = isRunning
            ? "Life Optimizer — tracking"
            : "Life Optimizer — click to start"

        debugLog("[StatusItem.updateIcon] title='\(button.title)', image=\(button.image != nil), frame=\(button.frame), isHidden=\(button.isHidden), alphaValue=\(button.alphaValue)")
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
