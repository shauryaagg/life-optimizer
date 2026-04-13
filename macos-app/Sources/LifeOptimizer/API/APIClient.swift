import Foundation

/// HTTP client for communicating with the Life Optimizer Python backend.
class APIClient {

    let baseURL: String

    init(baseURL: String = "http://127.0.0.1:8765") {
        self.baseURL = baseURL
    }

    // MARK: - Chat

    func chat(
        question: String,
        sessionId: String?,
        history: [ChatMessageModel]?
    ) async throws -> ChatAPIResponse {
        let url = URL(string: "\(baseURL)/api/chat")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 60

        let historyDicts: [[String: String]]? = history?.map { msg in
            ["role": msg.role, "content": msg.content]
        }
        let body = ChatRequest(
            question: question,
            sessionId: sessionId,
            history: historyDicts
        )
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)
        return try JSONDecoder().decode(ChatAPIResponse.self, from: data)
    }

    // MARK: - Status

    func status() async throws -> StatusResponse {
        let url = URL(string: "\(baseURL)/api/status")!
        let (data, response) = try await URLSession.shared.data(from: url)
        try validateResponse(response)
        return try JSONDecoder().decode(StatusResponse.self, from: data)
    }

    // MARK: - Stats

    func stats(date: String? = nil) async throws -> StatsResponse {
        var components = URLComponents(string: "\(baseURL)/api/stats")!
        if let date = date {
            components.queryItems = [URLQueryItem(name: "date", value: date)]
        }
        let (data, response) = try await URLSession.shared.data(from: components.url!)
        try validateResponse(response)
        return try JSONDecoder().decode(StatsResponse.self, from: data)
    }

    // MARK: - Events

    func events(date: String? = nil, app: String? = nil, limit: Int = 100) async throws -> [[String: AnyCodable]] {
        var components = URLComponents(string: "\(baseURL)/api/events")!
        var queryItems: [URLQueryItem] = []
        if let date = date { queryItems.append(URLQueryItem(name: "date", value: date)) }
        if let app = app { queryItems.append(URLQueryItem(name: "app", value: app)) }
        queryItems.append(URLQueryItem(name: "limit", value: String(limit)))
        components.queryItems = queryItems

        let (data, response) = try await URLSession.shared.data(from: components.url!)
        try validateResponse(response)
        return try JSONDecoder().decode([[String: AnyCodable]].self, from: data)
    }

    // MARK: - Entities

    func entities(type: String? = nil, limit: Int = 100) async throws -> [[String: AnyCodable]] {
        var components = URLComponents(string: "\(baseURL)/api/entities")!
        var queryItems: [URLQueryItem] = []
        if let type = type { queryItems.append(URLQueryItem(name: "type", value: type)) }
        queryItems.append(URLQueryItem(name: "limit", value: String(limit)))
        components.queryItems = queryItems

        let (data, response) = try await URLSession.shared.data(from: components.url!)
        try validateResponse(response)
        return try JSONDecoder().decode([[String: AnyCodable]].self, from: data)
    }

    // MARK: - Validation

    private func validateResponse(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(statusCode: httpResponse.statusCode)
        }
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error \(code)"
        case .decodingError(let error):
            return "Decoding error: \(error.localizedDescription)"
        }
    }
}
