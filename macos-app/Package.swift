// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "LifeOptimizer",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "LifeOptimizer",
            path: "Sources/LifeOptimizer",
            resources: [.copy("../../Resources")]
        )
    ]
)
