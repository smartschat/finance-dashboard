# Raspberry Pi Setup Guide

Detailed guide for deploying the finance dashboard on a Raspberry Pi with nginx reverse proxy and Pi-hole for custom DNS.

## Hardware Used

- Raspberry Pi (with Raspberry Pi OS 64-bit)
- Connected via WiFi

## Overview

The final setup:
```
Browser → http://finance.home
    ↓
Router DNS → Pi-hole (192.168.68.110)
    ↓
Pi-hole resolves finance.home → 192.168.68.110
    ↓
nginx (port 80) → Streamlit (port 8501)
    ↓
Finance Dashboard
```

## Step 1: Flash the SD Card

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select Raspberry Pi OS (64-bit)
3. Click the gear icon to pre-configure:
   - Set hostname (e.g., `sebastians-pi`)
   - Enable SSH
   - Set username and password
   - Configure WiFi credentials
4. Flash the SD card
5. Insert into Pi and power on

## Step 2: Assign Static IP

In your router's admin interface (for TP-Link Deco: More → DHCP Server → Address Reservation):
- Add the Pi's MAC address
- Assign a static IP (e.g., `192.168.68.110`)

## Step 3: SSH into the Pi

```bash
ssh pi@<pi-ip-address>
```

## Step 4: Install uv and Clone the Project

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# Create projects directory
mkdir -p ~/projects
cd ~/projects

# Generate SSH key for GitHub
ssh-keygen -t ed25519 -C "pi@raspberrypi"
cat ~/.ssh/id_ed25519.pub
# Add this key to GitHub: Settings → SSH and GPG keys → New SSH key

# Clone the repo
git clone git@github.com:smartschat/finance-dashboard.git
cd finance-dashboard

# Install dependencies
uv sync
```

## Step 5: Copy CSV Files

From your Mac:

```bash
scp ~/path/to/*.csv pi@192.168.68.110:~/projects/finance-dashboard/
```

## Step 6: Run as a Systemd Service

Create the service file:

```bash
sudo tee /etc/systemd/system/finance-dashboard.service << EOF
[Unit]
Description=Finance Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/projects/finance-dashboard
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

Verify it's running:

```bash
sudo systemctl status finance-dashboard
curl -I http://localhost:8501
```

At this point, the dashboard is accessible at `http://192.168.68.110:8501`.

## Step 7: Install Pi-hole for Custom DNS

Pi-hole allows using `http://finance.home` instead of the IP address.

```bash
curl -sSL https://install.pi-hole.net | bash
```

During installation:
- Select your network interface (wlan0)
- Choose any upstream DNS (Google or Cloudflare)
- Install the web admin interface
- Note the admin password at the end

### Configure Pi-hole Web Server Port

Pi-hole v6 uses port 80 by default, which conflicts with nginx. Change it:

```bash
sudo pihole-FTL --config webserver.port 8081
sudo systemctl restart pihole-FTL
```

Pi-hole admin is now at `http://192.168.68.110:8081/admin`.

### Add Custom DNS Entry

Pi-hole v6 serves entries from `/etc/hosts`:

```bash
echo "192.168.68.110 finance.home" | sudo tee -a /etc/hosts
sudo systemctl restart pihole-FTL
```

**Important:** Use `.home` instead of `.local` because macOS reserves `.local` for mDNS (Bonjour), which causes resolution conflicts.

### Configure Router to Use Pi-hole

In your router settings, set the Pi as the primary DNS server:
- For TP-Link Deco: More → Advanced → IPv4 → DNS
- Set Primary DNS to `192.168.68.110`

Devices will need to reconnect to WiFi (or wait for DHCP lease renewal) to pick up the new DNS server.

## Step 8: Install nginx Reverse Proxy

nginx allows accessing the dashboard on port 80 (no `:8501` needed).

```bash
sudo apt install nginx
```

Create the configuration:

```bash
sudo tee /etc/nginx/sites-available/finance << 'EOF'
server {
    listen 80;
    server_name finance.home;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF
```

**Note:** Use `127.0.0.1` instead of `localhost` to avoid IPv6 resolution issues.

Enable and start:

```bash
sudo ln -s /etc/nginx/sites-available/finance /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl start nginx
sudo systemctl enable nginx
```

## Step 9: Access the Dashboard

From any device on your network:

```
http://finance.home
```

**Browser tip:** Type `finance.home/` (with trailing slash) or `http://finance.home` to prevent the browser from treating it as a search query. Best to bookmark it.

## Troubleshooting

### Check if services are running

```bash
sudo systemctl status finance-dashboard
sudo systemctl status nginx
sudo systemctl status pihole-FTL
```

### Test each component

```bash
# Streamlit
curl -I http://127.0.0.1:8501

# nginx
curl -I http://127.0.0.1:80 -H "Host: finance.home"

# DNS (from another machine)
nslookup finance.home
```

### View logs

```bash
# Streamlit/dashboard
sudo journalctl -u finance-dashboard -f

# nginx
sudo tail -f /var/log/nginx/error.log

# Pi-hole
sudo tail -f /var/log/pihole/pihole.log
```

### Port 80 already in use

Check what's using it:

```bash
sudo lsof -i :80
```

If it's Pi-hole (pihole-FTL), change its port as described in Step 7.

### DNS not resolving

1. Verify the entry exists: `cat /etc/hosts`
2. Restart Pi-hole: `sudo systemctl restart pihole-FTL`
3. On macOS, flush DNS cache: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
4. Make sure you're using `.home` not `.local`

### nginx IPv6 connection refused

If logs show `connect() failed (111: Connection refused) ... upstream: "http://[::1]:8501/"`:

Change `proxy_pass http://localhost:8501;` to `proxy_pass http://127.0.0.1:8501;` in the nginx config.

## Updating the Dashboard

```bash
cd ~/projects/finance-dashboard
git pull
sudo systemctl restart finance-dashboard
```

## Adding More Web Apps

To add another app (e.g., on port 8502):

1. Add DNS entry to `/etc/hosts`:
   ```bash
   echo "192.168.68.110 otherapp.home" | sudo tee -a /etc/hosts
   sudo systemctl restart pihole-FTL
   ```

2. Create nginx config:
   ```bash
   sudo tee /etc/nginx/sites-available/otherapp << 'EOF'
   server {
       listen 80;
       server_name otherapp.home;

       location / {
           proxy_pass http://127.0.0.1:8502;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   EOF

   sudo ln -s /etc/nginx/sites-available/otherapp /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
