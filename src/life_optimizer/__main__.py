import asyncio

from life_optimizer.config import load_config
from life_optimizer.daemon.core import Daemon


def main():
    config = load_config()
    daemon = Daemon(config)
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
