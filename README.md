# LetsMeet — WebRTC Video Conferencing

A full-stack real-time video conferencing app built with FastAPI and WebRTC. Supports multi-user video/audio calls, chat, screen sharing, waiting room, and more.

---

## Features

- Multi-user video/audio conferencing (peer-to-peer WebRTC)
- Real-time chat with WhatsApp-style bubbles
- Waiting room — host admits/denies participants
- Screen share with system audio
- Raise hand ✋ and emoji reactions 🎉
- Participant list with live mic/cam status
- Pin/spotlight any participant
- Noise suppression toggle
- Invite link with room pre-fill
- Meeting timer
- Connection quality indicator per tile
- Reconnection logic with exponential backoff
- Mobile responsive UI
- JWT auth with auto token refresh
- Recording (saves locally as .webm)

---

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, Alembic
- **Auth:** JWT (access + refresh tokens), bcrypt, SlowAPI rate limiting
- **Real-time:** WebSocket signaling + WebRTC peer-to-peer
- **Frontend:** Vanilla HTML/CSS/JS
- **Deployment:** Docker, Railway

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# 5. Start PostgreSQL
docker compose up db -d

# 6. Run migrations
alembic upgrade head

# 7. Start the server
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`

---

## Testing Locally (Step-by-Step)

### Prerequisites
- Python 3.11+
- Docker Desktop (for PostgreSQL)
- A modern browser (Chrome recommended)

### 1. Start the app
Follow the Local Setup steps above. Once running, open `http://localhost:8000`.

### 2. Register a user
Go to `http://localhost:8000/docs` → find `POST /auth/register` → click **Try it out** → fill in:
```json
{
  "username": "your name",
  "email": "you mail@.com",
  "password": "password"
}
```
Click **Execute**.

### 3. Get a token
In the same Swagger page → find `POST /auth/login` → click **Try it out** → fill in:
```json
{
  "username": "your name",
  "email": "you mail@.com",
  "password": "password"
}
```
Click **Execute** → copy the `access_token` from the response.

### 4. Join a room
Go to `http://localhost:8000` → paste the token in the **Token** field → click **Join now**.

### 5. Test with multiple users
To simulate multiple participants, open the app in **two different browsers** (e.g. Chrome + Firefox) or use Chrome + an Incognito window. Register a second user, get their token, and join the same room.

> **Note:** Camera/mic access requires HTTPS in production. On localhost, browsers allow it without HTTPS.

### 6. Test the invite link
Click the **🔗 Invite** button in the topbar — it copies a URL like `http://localhost:8000/?room=room1`. Open that URL in another browser tab to join the same room with the room pre-filled.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
SECRET_KEY=your-32-char-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080
ALLOWED_ORIGINS=http://localhost:8000
TURN_URL=turn:openrelay.metered.ca:80
TURN_USERNAME=openrelayproject
TURN_CREDENTIAL=openrelayproject
```

---

## API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register `{username, email, password}` |
| POST | `/auth/login` | Login → access + refresh tokens |
| POST | `/auth/refresh` | Refresh tokens |
| GET | `/protected/ice-config` | TURN/STUN config (auth required) |
| WS | `/ws?token=JWT&room=ROOM` | WebSocket signaling |

Full API docs at `/docs` (Swagger UI).

---

## Deployment

Deployed on Railway with Docker. On every push to `main`:
1. Docker image is built
2. `alembic upgrade head` runs migrations
3. `uvicorn` starts the server

See [DOCUMENTATION.md](DOCUMENTATION.md) for full deployment guide and architecture details.

---

## Project Structure

```
app/
├── api/          # auth, protected, websocket endpoints
├── core/         # config, security, logging, rate limiter
├── db/           # database session and base
├── models/       # SQLAlchemy models
├── schemas/      # Pydantic schemas
├── services/     # business logic
├── templates/    # frontend (index.html)
└── websocket/    # legacy signaling router
alembic/          # database migrations
```

---

## License

MIT
