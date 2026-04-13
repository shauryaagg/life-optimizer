import AppKit
import SwiftUI

/// Floating NSPanel that hosts the Spotlight-style chat interface.
class SpotlightPanel: NSPanel {

    private var chatViewModel: ChatViewModel

    init(chatViewModel: ChatViewModel) {
        self.chatViewModel = chatViewModel

        super.init(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 420),
            styleMask: [.nonactivatingPanel, .titled, .fullSizeContentView, .utilityWindow, .hudWindow],
            backing: .buffered,
            defer: false
        )

        isFloatingPanel = true
        level = .floating
        titlebarAppearsTransparent = true
        titleVisibility = .hidden
        isMovableByWindowBackground = true
        backgroundColor = .clear
        hasShadow = true
        isReleasedWhenClosed = false
        hidesOnDeactivate = false
        animationBehavior = .utilityWindow

        // Center horizontally, upper quarter of screen
        centerOnScreen()

        // Host the SwiftUI view
        let hostingView = NSHostingView(
            rootView: SpotlightPanelView(viewModel: chatViewModel, panel: self)
        )
        contentView = hostingView
    }

    override var canBecomeKey: Bool { true }

    override func cancelOperation(_ sender: Any?) {
        close()
    }

    func centerOnScreen() {
        guard let screen = NSScreen.main else { return }
        let screenFrame = screen.visibleFrame
        let x = screenFrame.midX - frame.width / 2
        let y = screenFrame.maxY - 500
        setFrameOrigin(NSPoint(x: x, y: y))
    }

    func toggle() {
        if isVisible {
            close()
        } else {
            centerOnScreen()
            makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
        }
    }
}
