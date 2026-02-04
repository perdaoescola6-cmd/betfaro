#!/usr/bin/env python3
"""
Entrypoint para Railway/produção.
Lê PORT do ambiente e inicia uvicorn programaticamente.
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"🚀 Starting BetFaro API on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
