import os

import requests
import uvicorn

# copy from tangruyi

if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", 31006))
    uvicorn.run("aio_exporter.cli.app.main:app", host="0.0.0.0", port=port)
