import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "server.pid"), "w") as f:
        f.write(str(os.getpid()))

    uvicorn.run(app, host="127.0.0.1", port=8000)
