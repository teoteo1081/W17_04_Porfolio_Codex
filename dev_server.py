#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Portfolio Visual Editor & Development Server (/api/save)
Chạy lệnh: python dev_server.py
Sau đó mở: http://localhost:8000  (hoặc http://127.0.0.1:8000)
"""

import os

from server import make_server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = make_server(port)
    print(f"W17_04_Porfolio_Codex Dev Server running at http://localhost:{port}")
    server.serve_forever()
