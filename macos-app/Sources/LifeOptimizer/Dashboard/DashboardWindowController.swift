import AppKit
import WebKit

/// Manages the dashboard window with an embedded WKWebView.
class DashboardWindowController: NSWindowController {

    static let shared = DashboardWindowController()

    private var webView: WKWebView!

    convenience init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1200, height: 800),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Life Optimizer"
        window.center()
        window.setFrameAutosaveName("LifeOptimizerDashboard")
        window.minSize = NSSize(width: 800, height: 500)

        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.load(URLRequest(url: URL(string: "http://127.0.0.1:8765")!))
        window.contentView = webView

        self.init(window: window)
        self.webView = webView
    }

    /// Open the dashboard to a specific path.
    func openToPath(_ path: String) {
        showWindow(nil)
        if let webView = window?.contentView as? WKWebView {
            let url = URL(string: "http://127.0.0.1:8765\(path)")!
            webView.load(URLRequest(url: url))
        }
        NSApp.activate(ignoringOtherApps: true)
    }

    /// Reload the current page.
    func reload() {
        webView?.reload()
    }
}
