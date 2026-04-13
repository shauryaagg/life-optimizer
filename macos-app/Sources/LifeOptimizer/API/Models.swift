import Foundation

// MARK: - AnyCodable wrapper for mixed-type JSON values

/// A type-erased Codable wrapper for handling JSON values with mixed types.
struct AnyCodable: Codable, Equatable, Hashable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            value = NSNull()
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case is NSNull:
            try container.encodeNil()
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dict as [String: Any]:
            try container.encode(dict.mapValues { AnyCodable($0) })
        default:
            try container.encodeNil()
        }
    }

    static func == (lhs: AnyCodable, rhs: AnyCodable) -> Bool {
        String(describing: lhs.value) == String(describing: rhs.value)
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(String(describing: value))
    }

    var stringValue: String? { value as? String }
    var intValue: Int? { value as? Int }
    var doubleValue: Double? { value as? Double }
    var boolValue: Bool? { value as? Bool }
}

// MARK: - Chat API

struct ChatAPIResponse: Codable {
    let answer: String
    let queryType: String
    let sqlQuery: String?
    let followUpSuggestions: [String]
    let sessionId: String?

    enum CodingKeys: String, CodingKey {
        case answer
        case queryType = "query_type"
        case sqlQuery = "sql_query"
        case followUpSuggestions = "follow_up_suggestions"
        case sessionId = "session_id"
    }
}

struct ChatRequest: Codable {
    let question: String
    let sessionId: String?
    let history: [[String: String]]?

    enum CodingKeys: String, CodingKey {
        case question
        case sessionId = "session_id"
        case history
    }
}

// MARK: - Status API

struct StatusResponse: Codable {
    let daemonRunning: Bool
    let trackingStatus: String
    let eventCount: Int
    let lastEventTime: String?

    enum CodingKeys: String, CodingKey {
        case daemonRunning = "daemon_running"
        case trackingStatus = "tracking_status"
        case eventCount = "event_count"
        case lastEventTime = "last_event_time"
    }
}

// MARK: - Stats API

struct TopApp: Codable {
    let app: String
    let count: Int
}

struct StatsResponse: Codable {
    let date: String?
    let eventCount: Int
    let categoryBreakdown: [String: Int]
    let topApps: [TopApp]

    enum CodingKeys: String, CodingKey {
        case date
        case eventCount = "event_count"
        case categoryBreakdown = "category_breakdown"
        case topApps = "top_apps"
    }
}

// MARK: - Chat Message Model (internal)

struct ChatMessageModel: Identifiable, Equatable {
    let id: UUID
    let role: String
    let content: String
    let timestamp: Date

    init(role: String, content: String) {
        self.id = UUID()
        self.role = role
        self.content = content
        self.timestamp = Date()
    }
}
