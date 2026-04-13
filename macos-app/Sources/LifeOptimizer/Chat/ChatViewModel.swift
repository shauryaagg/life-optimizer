import Foundation
import Combine

/// ViewModel for the Spotlight chat interface.
@MainActor
class ChatViewModel: ObservableObject {
    @Published var query: String = ""
    @Published var messages: [ChatMessageModel] = []
    @Published var isLoading: Bool = false
    @Published var followUpSuggestions: [String] = []
    @Published var errorMessage: String?

    private let apiClient = APIClient()
    private var sessionId: String?

    let defaultSuggestions = [
        "How much deep work today?",
        "What was I doing at 3pm?",
        "Compare this week to last week",
        "Who did I message most today?",
        "What apps did I use most?",
        "Show me my productivity stats",
    ]

    /// Submit the current query.
    func submit() async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        let question = trimmed
        query = ""
        errorMessage = nil

        // Add user message
        messages.append(ChatMessageModel(role: "user", content: question))
        isLoading = true

        do {
            let response = try await apiClient.chat(
                question: question,
                sessionId: sessionId,
                history: messages.isEmpty ? nil : messages
            )
            sessionId = response.sessionId
            messages.append(ChatMessageModel(role: "assistant", content: response.answer))
            followUpSuggestions = response.followUpSuggestions
        } catch {
            errorMessage = "Could not reach the backend. Is the daemon running?"
            messages.append(ChatMessageModel(
                role: "assistant",
                content: "Sorry, I couldn't connect to the backend. Please make sure the Life Optimizer daemon is running."
            ))
        }

        isLoading = false
    }

    /// Submit a follow-up suggestion.
    func submitFollowUp(_ text: String) async {
        query = text
        await submit()
    }

    /// Clear conversation and start fresh.
    func clear() {
        messages.removeAll()
        sessionId = nil
        followUpSuggestions = []
        errorMessage = nil
        query = ""
    }
}
