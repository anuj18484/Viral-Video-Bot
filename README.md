# Free Video Bot

## Files
- `main.py` — single-file Telegram bot
- `requirements.txt` — dependency list

## Hosting environment variables
Set these in your hosting dashboard. Do not commit secrets to GitHub.

- `BOT_TOKEN`: new token from @BotFather
- `ADMIN_USERNAME`: Telegram username without `@`
- `JOIN_LINK`: public channel link or invite link

Admin ID is configured in `main.py`: `8678341659`.

## Run
```bash
pip install -r requirements.txt
python main.py
```

Use persistent storage for `videos.db`, otherwise user/video records may be lost on redeploy or restart. Run only one polling instance.
