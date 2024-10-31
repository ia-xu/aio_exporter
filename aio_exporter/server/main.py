import os
import uvicorn


if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", 31006))

    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
