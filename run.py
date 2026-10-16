"""Start FindBack locally and display links to open in a browser."""

import argparse
from pathlib import Path

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run the local FindBack prototype")
    parser.add_argument(
        "--port", type=int, default=8000, choices=range(1, 65536),
        metavar="PORT", help="local port (default: 8000)",
    )
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    print(
        f"\nFindBack - copy a link into your browser after the server starts:\n"
        f"  Website:  {url}\n"
        f"  API docs: {url}/docs\n"
        f"Stop the server with Ctrl+C.\n",
        flush=True,
    )
    uvicorn.run(
        "main:app", host="127.0.0.1", port=args.port,
        app_dir=str(Path(__file__).resolve().parent),
    )


if __name__ == "__main__":
    main()
