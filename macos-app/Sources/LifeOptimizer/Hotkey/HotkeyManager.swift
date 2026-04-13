import AppKit

/// Registers and manages global hotkeys using NSEvent monitors.
class HotkeyManager {
    private var globalMonitor: Any?
    private var localMonitor: Any?
    private var callback: (() -> Void)?

    /// Register Cmd+Shift+Space as the global hotkey.
    func register(callback: @escaping () -> Void) {
        self.callback = callback

        // Monitor events when app is not frontmost
        globalMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            self?.handleKeyEvent(event)
        }

        // Monitor events when app is frontmost
        localMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            let flags = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
            if flags == [.command, .shift] && event.keyCode == 49 {
                DispatchQueue.main.async { self?.callback?() }
                return nil // consume the event
            }
            return event
        }
    }

    /// Unregister all event monitors.
    func unregister() {
        if let monitor = globalMonitor {
            NSEvent.removeMonitor(monitor)
            globalMonitor = nil
        }
        if let monitor = localMonitor {
            NSEvent.removeMonitor(monitor)
            localMonitor = nil
        }
        callback = nil
    }

    private func handleKeyEvent(_ event: NSEvent) {
        let flags = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
        // keyCode 49 = Space
        if flags == [.command, .shift] && event.keyCode == 49 {
            DispatchQueue.main.async { [weak self] in
                self?.callback?()
            }
        }
    }

    /// Check whether Accessibility permissions are granted (required for global hotkey).
    static var isAccessibilityGranted: Bool {
        return AXIsProcessTrusted()
    }
}
