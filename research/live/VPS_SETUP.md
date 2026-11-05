# Pilot server setup (one-time, ~15 minutes)

Why a server: Polymarket blocks the United States on its website *and* its API, and GitHub's own job
runners live in the US. The pilot therefore runs on a small server of ours in an allowed country,
registered with GitHub as a "self-hosted runner". Nothing else changes: the code, the schedule and the
secrets stay in GitHub; the server only executes the job.

## 1. Rent the server
- Hetzner Cloud (https://console.hetzner.cloud): project -> Add Server
  - Location: **Helsinki** (Finland is not on Polymarket's restricted list; Germany and the UK are)
  - Image: Ubuntu 24.04 · Type: the smallest shared vCPU (CX22, ~EUR 4/month) · add your SSH key
- Any other provider works if the location is allowed (not US, UK, DE, FR, IT, PL, SG, AU, CA, ...);
  check with `curl https://polymarket.com/api/geoblock` on the box: it must say `"blocked":false`.

## 2. Prepare it (as root, over SSH)
```bash
apt update && apt install -y git python3 python3-pip python3-venv curl
adduser --disabled-password --gecos "" runner
curl -sS https://polymarket.com/api/geoblock; echo     # must be "blocked":false
```

## 3. Register it as a GitHub runner
On GitHub: repo -> Settings -> Actions -> Runners -> **New self-hosted runner** -> Linux x64.
GitHub shows a block of commands with a one-time token. Run them **as the `runner` user**
(`su - runner`), and when `./config.sh` asks:
- runner group: Enter (default)
- name: `pilot-helsinki`
- **labels: `pilot`**  (this is what the job looks for)
- work folder: Enter (default)

Then install it as a service so it survives reboots (back as root):
```bash
cd /home/runner/actions-runner && ./svc.sh install runner && ./svc.sh start && ./svc.sh status
```

## 4. Done
The pilot job (`.github/workflows/pilot.yml`) picks the runner up by its `pilot` label on the next
schedule, or immediately with "Run workflow" on the Actions page. Mode is still controlled by
`research/live/PILOT_MODE` (dry / live / off) and the `STOP` file; secrets stay in GitHub.

Security note: a self-hosted runner on a public repo executes this repo's workflows only (forks need
approval by default). Keep two-factor authentication on the GitHub account; the server holds no keys
of its own.
