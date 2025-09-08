from __future__ import annotations

def generate_systemd_unit(app_path: str, start_command: str, port: int) -> str:
    return f"""
[Unit]
Description=Arvo Application Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory={app_path}
Environment=PORT={port}
ExecStart=/bin/bash -lc '{start_command}'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""".strip()
