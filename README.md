# Bassiehof VPS Pipeline

Volledige automatische pipeline voor de VPS.

## Structuur

```
bassiehof-vps/
├── vps_pipeline.py        # Hoofd pipeline script
├── orchestrator.py       # Lokaal orchestratie script
├── subtitels.py         # Ondertitels genereren
├── thumbnail.py          # Thumbnail generatie
├── youtube_upload.py    # YouTube upload
├── verwerk.py          # Video verwerking
└── tools/
    └── bassiehof-logo-transparent.png
```

## Installatie VPS

```bash
# Clone
git clone https://github.com/jordybergman-dev/bassiehof-pipeline.git
cd bassiehof-pipeline

# Installeer dependencies
pip install google-api-python-client google-auth-oauthlib pillow requests

# Setup folders
mkdir -p Videos logos

# Environment variables
export TELEGRAM_BOT="jouw_token"
export TELEGRAM_CHAT="1523587806"
```

## Gebruik

### Check agenda
```bash
python3 vps_pipeline.py --schedule
```

### Download & verwerk van stream URL
```bash
python3 vps_pipeline.py --url "https://livestreaming.b67buv2.tweedekamer.nl/2026-03-13/plenairezaal/stream_05/prog_index.m3u8"
```

### Lokaal verwerken
```bash
python3 vps_pipeline.py --video "video.mp4"
```

### Dry-run
```bash
python3 vps_pipeline.py --video "video.mp4" --dry-run
```

## Cron Job (dagelijks)

```bash
crontab -e

# Elke dag om 18:00 agenda checken
0 18 * * * cd /root/bassiehof-pipeline && python3 vps_pipeline.py --schedule >> /var/log/bassiehof.log 2>&1
```

## DebatDirect API

- Agenda: `https://cdn.debatdirect.tweedekamer.nl/api/agenda/YYYY-MM-DD`
- Streams: `https://livestreaming.b67buv2.tweedekamer.nl/{datum}/{locatie}/stream_05/prog_index.m3u8`
