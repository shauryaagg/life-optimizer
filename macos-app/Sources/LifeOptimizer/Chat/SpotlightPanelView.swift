import SwiftUI
import AppKit

/// The SwiftUI view hosted inside the SpotlightPanel.
struct SpotlightPanelView: View {
    @ObservedObject var viewModel: ChatViewModel
    weak var panel: SpotlightPanel?

    @FocusState private var isSearchFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                    .font(.title3)

                TextField("Ask about your activity...", text: $viewModel.query)
                    .textFieldStyle(.plain)
                    .font(.title3)
                    .focused($isSearchFocused)
                    .onSubmit {
                        Task { await viewModel.submit() }
                    }

                if viewModel.isLoading {
                    ProgressView()
                        .controlSize(.small)
                }

                if !viewModel.messages.isEmpty {
                    Button(action: { viewModel.clear() }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider()

            // Content area
            if viewModel.messages.isEmpty {
                // Default suggestions
                VStack(alignment: .leading, spacing: 12) {
                    Text("Suggestions")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 16)
                        .padding(.top, 12)

                    SuggestionsView(suggestions: viewModel.defaultSuggestions) { suggestion in
                        Task { await viewModel.submitFollowUp(suggestion) }
                    }

                    Spacer()
                }
            } else {
                // Conversation
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 4) {
                            ForEach(viewModel.messages) { message in
                                ChatBubbleView(message: message)
                                    .id(message.id)
                            }
                        }
                        .padding(.vertical, 8)
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        if let lastId = viewModel.messages.last?.id {
                            withAnimation(.easeOut(duration: 0.2)) {
                                proxy.scrollTo(lastId, anchor: .bottom)
                            }
                        }
                    }
                }

                // Follow-up suggestions
                if !viewModel.followUpSuggestions.isEmpty && !viewModel.isLoading {
                    Divider()
                    SuggestionsView(suggestions: viewModel.followUpSuggestions) { suggestion in
                        Task { await viewModel.submitFollowUp(suggestion) }
                    }
                    .padding(.vertical, 8)
                }
            }

            // Error message
            if let error = viewModel.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundColor(.orange)
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 8)
            }
        }
        .frame(width: 600, height: 420)
        .background(VisualEffectView(material: .hudWindow, blendingMode: .behindWindow))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .onAppear {
            isSearchFocused = true
        }
    }
}

/// NSVisualEffectView wrapper for vibrancy/blur background.
struct VisualEffectView: NSViewRepresentable {
    let material: NSVisualEffectView.Material
    let blendingMode: NSVisualEffectView.BlendingMode

    func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.material = material
        view.blendingMode = blendingMode
        view.state = .active
        return view
    }

    func updateNSView(_ nsView: NSVisualEffectView, context: Context) {
        nsView.material = material
        nsView.blendingMode = blendingMode
    }
}
