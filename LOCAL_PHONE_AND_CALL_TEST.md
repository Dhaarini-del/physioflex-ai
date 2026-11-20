# PhysioFlex local phone + video-call testing

## Start the server

Open a terminal in the folder containing `main.py`, activate the same Python environment you use locally, then run:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Keep the terminal open. On the laptop, test `http://127.0.0.1:8000`.

## Open on Android/iPhone over the same Wi-Fi

1. Connect phone and laptop to the same non-guest Wi-Fi.
2. On Windows, run `ipconfig` and find the active Wi-Fi adapter's IPv4 address (example `192.168.1.20`).
3. On the phone, open `http://192.168.1.20:8000` using your actual IP. Do not use `localhost` or `127.0.0.1` on the phone.
4. If it times out, allow Python/port 8000 through Windows Defender Firewall on a private network. Some guest Wi-Fi networks block device-to-device access.

**Important:** local LAN HTTP is suitable for basic page testing, but camera/microphone APIs and PWA installation generally require HTTPS (localhost is a browser exception only on the same device). For full phone video-call testing, deploy to a temporary HTTPS host or use a local HTTPS tunnel.

## Test calls

1. Start server and sign in on two separate browsers/devices using a patient account and a doctor/physiotherapist account.
2. Keep both portal pages open; their WebSocket connections must remain connected.
3. From the patient portal, choose Video Call Doctor or Video Call Physio and accept the incoming prompt on the clinician portal. Both users should join the same Jitsi room ID.
4. Allow camera/microphone permissions. Both devices need internet access to reach `meet.jit.si`.
5. If the notification fails, inspect the terminal traceback. If Jitsi does not load, test `https://meet.jit.si/external_api.js` in that device's browser.

## YouTube exercise demonstrations

The demo modal embeds saved YouTube IDs when present and includes a YouTube search fallback based on the exercise name. A deleted, private, or embedding-disabled video cannot be repaired in code; replace its saved URL with a valid public video. Some networks/ad blockers may block embedded YouTube players.

## Privacy note

This is a prototype using the public Jitsi service. Do not use public rooms for real patient consultations without appropriate privacy/security review.
