import os

import requests
import uvicorn
import argparse


if __name__ == "__main__":
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Run the AIO Exporter application.")

    # Add an argument for the port number
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("APP_PORT", 56006)),
        help="Port number to run the application on. Defaults to APP_PORT environment variable or 31006 if not set."
    )
    # Add an argument for the number of workers
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("APP_WORKERS", 1)),
        help="Number of workers to run the application with. Defaults to APP_WORKERS environment variable or 3 if not set."
    )

    # Parse the arguments
    args = parser.parse_args()

    # Run the application with the specified port
    uvicorn.run(
        "aio_parser_server.app.main:app",
        host="0.0.0.0",
        port=args.port,
        workers=args.workers
    )

