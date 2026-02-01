# PDF-to-HTML Deployment Notes (VPS)

Updated: 2026-02-01

## Production service settings

Use a direct Python entrypoint (not `python -m gradio`) to avoid startup loop issues:

```ini
[Service]
WorkingDirectory=/home/clawdbot/clawd/pdf-to-html
Environment="PATH=/usr/bin:/bin"
Environment=PUBLIC_ROOT_URL=https://pdf.zoid.bot
Environment=GRADIO_SERVER_NAME=0.0.0.0
ExecStart=/usr/bin/python3 /home/clawdbot/clawd/pdf-to-html/gradio_app.py
Restart=always
RestartSec=10
```

Systemd unit path:

- `/etc/systemd/system/pdf-to-html.service`

Reload/restart after edits:

```bash
sudo systemctl daemon-reload
sudo systemctl restart pdf-to-html
sudo systemctl status pdf-to-html
```

## Nginx upload limit (fixes 413)

Set this in both HTTP and HTTPS `server` blocks for `pdf.zoid.bot`:

```nginx
client_max_body_size 200M;
```

Nginx vhost path:

- `/etc/nginx/sites-available/pdf.zoid.bot`

Validate/reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Gradio root path note

Do not set `GRADIO_ROOT_PATH=/gradio_api` as app `root_path`.
That value is used by Gradio internal API routes and can trigger startup probe failures (`.../startup-events` 404) in newer versions.

