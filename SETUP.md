# Satoru EMR — setup

Two repos, side by side:

```
EMRCHT/
  cht-core/    the CHT platform, patched (5 files) for readable scale reports + Print/PDF
  satoruemr/   this repo: forms, settings, translations, Excel exports, deploy overlay
```

Neither works alone. The cht-core patch is **inert** unless this repo's
`report_display` config is uploaded — that config is what tells it which
fields to hide and how to turn `P` into `Pass`.

Patched cht-core: https://github.com/defaultname-ayan/cht-core-satoru-reports

---

## 1. Prerequisites

| Tool | Version | Note |
|---|---|---|
| Docker | any recent | user must be in the `docker` group |
| Node | **22.x** | cht-core needs >=22.15.0; Node 25 is untested |
| Python | 3.10+ | for the export scripts |
| cht-conf | ^6.x | `npm i -g cht-conf` (the `cht` command) |

```bash
sudo usermod -aG docker $USER && sudo systemctl enable --now docker   # then log out/in
python -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
```

## 2. Start CHT — **use 5.3.0 images, not 5.2.0**

```bash
V=5.3.0
D=~/.medic/cht-docker/satoruemr-dir
mkdir -p "$D/compose" "$D/couch"
BASE="https://staging.dev.medicmobile.org/_couch/builds_4/medic:medic:${V}"
curl -sS -o "$D/compose/cht-core.yml"    "$BASE/docker-compose/cht-core.yml"
curl -sS -o "$D/compose/cht-couchdb.yml" "$BASE/docker-compose/cht-couchdb.yml"

cat > ../cht-core/satoruemr.env <<EOF
NGINX_HTTP_PORT=10080
NGINX_HTTPS_PORT=10443
COUCHDB_USER=medic
COUCHDB_PASSWORD=password
COUCHDB_SECRET=$(openssl rand -hex 16)
COUCHDB_UUID=$(openssl rand -hex 16)
COUCHDB_DATA=$D/couch
CHT_COMPOSE_PATH=$D/compose
CHT_NETWORK=cht-net
SATORU_REPO=$(pwd)
SATORU_EXPORTS_NGINX_TEMPLATE=$(pwd)/deploy/nginx-server.conf.template
EOF
```

> `COUCHDB_PASSWORD=password` is the CHT docker-helper default and is fine
> for a local dev box only. Change it for anything reachable by anyone else.
> `satoruemr.env` is gitignored in cht-core — never commit it.

> **Why 5.3.0.** The patch is cut from upstream master after the 5.2.0
> release, and the webapp calls `POST /api/v1/report/summary`. The 5.2.0
> API does not have that route, so it 404s and the Reports view hangs on
> a spinner forever. 5.3.0 has it.

Start everything (CHT **and** the export UI) with one command:

```bash
C=~/.medic/cht-docker/satoruemr-dir/compose
alias satoru='docker compose --env-file ../cht-core/satoruemr.env \
  -f '"$C"'/cht-core.yml -f '"$C"'/cht-couchdb.yml -f '"$(pwd)"'/deploy/cht-exports.yml'
satoru up -d
```

Trust the TLS cert (optional, removes browser warnings):

```bash
curl -s -o /tmp/c https://local-ip.medicmobile.org/fullchain
curl -s -o /tmp/k https://local-ip.medicmobile.org/key
docker cp /tmp/c <nginx-container>:/etc/nginx/private/cert.pem
docker cp /tmp/k <nginx-container>:/etc/nginx/private/key.pem
docker exec <nginx-container> nginx -s reload
```

## 3. Upload this config

```bash
python scripts/gen_report_config.py        # regenerate report_display + labels
cht --url=https://medic:PASSWORD@<HOST>:10443 --accept-self-signed-certs --force \
    upload-app-settings upload-app-forms upload-contact-forms upload-custom-translations
```

`--force` matters: without it cht-conf prompts before overwriting and dies
in any non-interactive shell. Hard-refresh the browser afterwards —
translations are cached client-side.

Run `gen_report_config.py` after **any** change to `forms/app/*.xml`.

## 4. Rebuild the webapp (only if you change cht-core)

```bash
cd ../cht-core
npx sass webapp/src/css/enketo/enketo.scss api/build/static/webapp/enketo.less --no-source-map
cd webapp && npm ci && npm run build -- --configuration=production
cd ../api/build/static/webapp
for f in main.js runtime.js polyfills.js scripts.js styles.css index.html; do
  docker cp $f <api-container>:/service/api/build/static/webapp/$f; done
docker restart <api-container>
```

> **`--configuration=production` is mandatory.** `angular.json` sets
> `defaultConfiguration: None`, so a bare `ng build` inlines "critical CSS"
> into `index.html`. That inlined copy of `.bootstrap-layer{display:flex}`
> is unlayered and overrides `.bootstrapped .bootstrap-layer{display:none}`,
> leaving the app stuck behind a loading spinner with the real UI rendered
> underneath. Production sets `inlineCritical:false`. Sanity check:
> `index.html` should be **~850 bytes**, not ~56 KB.
>
> The enketo.less step is also required — `ng build` fails without it.

## 5. Excel exports

Browser: **https://\<host\>:10443/exports/** — same stack, same URL as CHT.
Command line and format details: [scripts/EXPORTS.md](scripts/EXPORTS.md).

## 6. Test data / self-checks

```bash
.venv/bin/python scripts/load_sample_data.py --url https://medic:PASSWORD@<HOST>:10443/medic
.venv/bin/python scripts/validate_exports.py        # 58 checks, no server needed
node scripts/validate_report_patch.js               # 50 checks, needs ../cht-core/node_modules/typescript
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Reports show `report.dst.g_child.assessment_date` | config/translations not uploaded | step 3, then hard-refresh |
| App stuck on spinner, Reports never load | built without `--configuration=production`, or running 5.2.0 images | step 4 / step 2 |
| `permission denied ... docker.sock` | user not in `docker` group | `sudo usermod -aG docker $USER`, re-login |
| cht-conf exits on "overwrite?" | no TTY | add `--force` |
| Export sheet missing a scale | nobody completed it in that camp | expected — empty scales are skipped |
