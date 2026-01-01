# Finance Dashboard

Personal finance dashboard for analyzing DKB (Deutsche Kreditbank) bank exports. Built with Streamlit.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.52+-red)

## Features

- **CSV Import**: Load Girokonto and Visa credit card exports from DKB
- **Auto-Categorization**: Transactions automatically categorized (Groceries, Transport, Subscriptions, etc.)
- **Multiple Views**:
  - Overview with key metrics and charts
  - Spending trends over time
  - Year-over-year comparison
  - Typical month budget analysis
- **Filtering**: By year, date range, account, and category
- **Search**: Find specific transactions

## Quick Start (Local)

```bash
# Clone the repo
git clone git@github.com:smartschat/finance-dashboard.git
cd finance-dashboard

# Install dependencies
uv sync

# Add your DKB CSV exports to the project folder
# Files should match: *Girokonto*.csv and *Visa*.csv

# Run the dashboard
uv run streamlit run app.py
```

Open http://localhost:8501

## Raspberry Pi Deployment

Host the dashboard on a Raspberry Pi for 24/7 access from any device on your network.

### Prerequisites

- Raspberry Pi 4 or 5 (2GB+ RAM recommended)
- Raspberry Pi OS (64-bit)
- SSH access to the Pi

### 1. Install uv and clone the repo

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# Clone and install
git clone git@github.com:smartschat/finance-dashboard.git
cd finance-dashboard
uv sync
```

### 2. Copy your CSV files

From your Mac/PC:

```bash
scp *.csv pi@<pi-ip>:~/finance-dashboard/
```

### 3. Run the dashboard

```bash
uv run streamlit run app.py --server.address 0.0.0.0
```

Access at `http://<pi-ip>:8501`

### 4. Run as a service (auto-start on boot)

Create a systemd service:

```bash
sudo tee /etc/systemd/system/finance-dashboard.service << EOF
[Unit]
Description=Finance Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/finance-dashboard
ExecStart=$HOME/.local/bin/uv run streamlit run app.py --server.address 0.0.0.0 --server.port 8501
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable finance-dashboard
sudo systemctl start finance-dashboard
```

Check status:

```bash
sudo systemctl status finance-dashboard
```

### 5. Nice hostname with Pi-hole (optional)

Instead of accessing via IP, use `http://finance.home`.

> **Note:** Use `.home` instead of `.local` because macOS reserves `.local` for mDNS (Bonjour), which causes DNS resolution conflicts.

**Install Pi-hole:**

```bash
curl -sSL https://install.pi-hole.net | bash
```

**Change Pi-hole web port** (to free port 80 for nginx):

```bash
sudo pihole-FTL --config webserver.port 8081
sudo systemctl restart pihole-FTL
```

**Add custom DNS entry** (Pi-hole v6 uses `/etc/hosts`):

```bash
echo "192.168.68.110 finance.home" | sudo tee -a /etc/hosts
sudo systemctl restart pihole-FTL
```

**Configure your router** to use the Pi as DNS server (Primary DNS = Pi's IP).

### 6. Remove port with nginx (optional)

Access via `http://finance.home` instead of `http://finance.home:8501`.

**Install nginx:**

```bash
sudo apt install nginx
```

**Add the config:**

```bash
sudo cp nginx.conf /etc/nginx/sites-available/finance
sudo ln -s /etc/nginx/sites-available/finance /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Now access at `http://finance.home` (no port needed).

## Project Structure

```
finance-dashboard/
├── app.py              # Main Streamlit dashboard
├── finance_dashboard/  # Core library modules
├── nginx.conf          # nginx reverse proxy config
├── pyproject.toml      # Project dependencies
└── *.csv               # Your DKB export files (gitignored)
```

## Exporting from DKB

1. Log into DKB online banking
2. Go to your account → Umsätze (transactions)
3. Set date range and click "Exportieren" → CSV
4. Repeat for each account (Girokonto, Visa)
5. Place CSV files in the project folder

## License

MIT
