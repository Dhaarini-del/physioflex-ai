# Deploy PhysioFlex to Render

## Important
Use Render as a single FastAPI web service first. The phone and laptop must open the same public `https://<your-service>.onrender.com` URL. Do not use `127.0.0.1` or `localhost` on the phone.

## GitHub
1. Extract this folder and create/push a GitHub repository.
2. Confirm `.env`, database files, and secrets are not staged.
3. Include `main.py`, `database.py`, `auth.py`, `chat_routes.py`, `requirements.txt`, `templates/`, `static/`, `render.yaml`, `Procfile`, and `.env.example`.

## Render
1. In Render choose **New + → Blueprint** and select the GitHub repository (or create a Web Service).
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add `MONGODB_URI` in Environment using your existing Atlas connection string. Keep Atlas database/user/network access configured; never put credentials in GitHub. `MONGODB_DB_NAME` defaults to `physioflex`.
5. Deploy, then test `https://YOUR-SERVICE.onrender.com/api/health`.
6. Open the same HTTPS URL on both phone and laptop. Free Render services can sleep when idle and the first request may be slow.

## Test checklist
- `/api/health` returns status `ok`.
- Login with a valid account.
- Approve patient accounts before testing clinical alerts.
- Send a patient alert, then check doctor/physiotherapist portal within 10–15 seconds.
- Use a valid exercise YouTube video URL; deleted/private videos cannot be restored by code.
- Test camera/microphone on HTTPS and accept browser permissions.

## Video call caveat
This application contains WebSocket signaling and a browser media UI. WebSocket notifications are process-local and may not work across multiple server instances. This patch improves persisted alert delivery, but it does not certify end-to-end WebRTC calling. For reliable calls, integrate a hosted room provider such as Jitsi with a unique room per consultation, or implement complete WebRTC signaling and STUN/TURN.


## Verify this deployment is the corrected version
After deployment, open `/api/health`. The response must include `"version":"1.1.1-alert-fix"`. If it does not, Render is deploying a different branch/root directory or the new commit has not been deployed.

Set `MONGODB_URI` to your existing Atlas connection string and `MONGODB_DB_NAME` to the exact existing database name that contains your PhysioFlex records. Do not create a new database or use a guessed name. Atlas Network Access must allow the Render service to connect.

The repository root must contain `main.py`, `database.py`, `requirements.txt`, and `render.yaml` directly. Do not commit the ZIP itself as the app root and do not leave these files only inside a nested `pf/` directory.
