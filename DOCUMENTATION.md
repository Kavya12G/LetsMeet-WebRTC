# LetsMeet-WebRTC — Project Documentation

## Overview

A full-stack real-time video conferencing application built with FastAPI (Python) and WebRTC. Supports multi-user video/audio calls, chat, screen sharing, room access control, and more. Deployed on Railway with PostgreSQL.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL + SQLAlchemy ORM |
| Migrations | Alembic |
| Auth | JWT (access + refresh tokens) |
| Real-time | WebSocket (FastAPI) + WebRTC (peer-to-peer) |
| Frontend | Vanilla HTML/CSS/JS (single template) |
| Deployment | Railway (Docker) |
| Rate limiting | SlowAPI |

---

## Project Structure

```
├── app/
│   ├── api/
│   │   ├── auth.py          # Register, login, refresh token endpoints
│   │   ├── protected.py     # /me endpoint, /ice-config (TURN credentials)
│   │   └── ws.py            # WebSocket signaling server
│   ├── core/
│   │   ├── config.py        # Settings from .env (pydantic-settings)
│   │   ├── connection_manager.py  # WebSocket connection registry
│   │   ├── dependencies.py  # get_current_user dependency
│   │   ├── limiter.py       # SlowAPI rate limiter instance
│   │   ├── logging.py       # Logging setup
│   │   └── security.py      # Password hashing, JWT creation/decode
│   ├── db/
│   │   ├── base.py          # SQLAlchemy Base
│   │   └── session.py       # Engine, SessionLocal, get_db
│   ├── models/
│   │   └── user.py          # User DB model
│   ├── schemas/
│   │   ├── token_schema.py  # Token response schema
│   │   └── user_schema.py   # UserCreate, UserResponse schemas
│   ├── services/
│   │   └── auth_service.py  # create_user, authenticate_user
│   ├── templates/
│   │   └── index.html       # Entire frontend (single file)
│   ├── websocket/
│   │   └── signaling.py     # Legacy signaling router (kept for compatibility)
│   └── main.py              # FastAPI app entry point
├── alembic/                 # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/            # Migration files
├── alembic.ini
├── Dockerfile
├── docker-compose.yml       # Local dev (app + postgres)
├── railway.toml             # Railway deployment config
├── requirements.txt
├── start.sh                 # Container startup script
├── .env                     # Local environment variables (never commit)
├── .env.example             # Template for environment variables
├── .gitignore
└── .dockerignore
```

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT signing key (32+ random chars) | `a3f8...` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Refresh token lifetime | `10080` (7 days) |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `https://your-app.up.railway.app` |
| `TURN_URL` | TURN server URL | `turn:openrelay.metered.ca:80` |
| `TURN_USERNAME` | TURN server username | `openrelayproject` |
| `TURN_CREDENTIAL` | TURN server password | `openrelayproject` |

---

## API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register new user `{username, email, password}` |
| POST | `/auth/login` | Login `{username, email, password}` → returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh tokens `{refresh_token}` → returns new token pair |

### Protected
| Method | Path | Description |
|---|---|---|
| GET | `/protected/me` | Returns current user info |
| GET | `/protected/ice-config` | Returns TURN/STUN ICE config (auth required) |

### WebSocket
| Path | Description |
|---|---|
| `WS /ws?token=JWT&room=ROOM_ID` | Main signaling WebSocket |

### Other
| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves the frontend HTML |
| GET | `/docs` | Swagger UI |

---

## Features

### 1. JWT Authentication
- Register with `username`, `email`, `password` (min 8 chars)
- Login returns `access_token` (30 min) and `refresh_token` (7 days)
- `/auth/refresh` issues new token pair using refresh token
- Frontend auto-refreshes access token 2 minutes before expiry
- Rate limited: 10 requests/minute on register and login

### 2. WebRTC Video Conferencing
- Peer-to-peer video/audio using browser WebRTC APIs
- Works well up to 4-6 participants (beyond that needs SFU)
- ICE config fetched from server — TURN credentials never exposed in frontend
- STUN fallback if TURN fetch fails
- Uses `wss://` on HTTPS automatically

### 3. WebSocket Signaling
- Handles: `offer`, `answer`, `ice_candidate`, `existing_users`, `new_user`, `user_left`
- Existing users send offers to new joiners (not the other way)
- All user IDs normalized to strings to prevent int/string mismatch bugs
- `ontrack` uses `new MediaStream()` + `addTrack()` — avoids `e.streams[0]` unreliability

### 4. Room Management
- Rooms are identified by string ID (e.g. `room1`)
- In-memory state: `rooms`, `room_hosts`, `user_names`, `user_rooms`
- First user to join becomes host automatically

### 5. Reconnection Logic
- 8-second grace period on disconnect — user not removed immediately
- If user reconnects within 8s: peers get `peer_reconnected`, re-negotiate
- If not: `user_left` sent to all peers, cleanup runs
- Frontend: exponential backoff retry (1s → 2s → 4s → 8s → 16s max)
- Reconnect overlay shown during retries
- Only triggers after a successful first join (`_hasJoinedOnce` flag)

### 6. Room Access Control (Waiting Room)
- First user → instant host, no waiting
- Subsequent users → sent to waiting room, host sees admit/deny popup
- Host admits → user joins normally
- Host denies → user gets rejection message
- Auto-denied after 60 seconds if host doesn't respond
- If host leaves → next user in room becomes host

### 7. Chat
- WhatsApp-style bubbles: current user right (green), others left (dark)
- Sender name shown above each message
- Timestamp below each message
- Messages broadcast to all room participants via WebSocket

### 8. Pre-join Screen
- Camera preview before joining
- Mic/camera toggle before joining
- State (muted/cam off) carries over to meeting controls
- Room pre-filled from URL param `?room=ROOM_ID`

### 9. Video Grid Layout
- Google Meet-style grid that fills the viewport
- Auto-adjusts columns/rows based on participant count
- Each tile shows: video, avatar (initial letter when cam off), username label
- Speaking indicator (green outline) via Web Audio API

### 10. Mute/Camera State on Tiles
- 🔇 icon shown on tile when participant is muted
- Avatar shown when camera is off
- State broadcast via `media_state` WebSocket message
- Initial state broadcast on join

### 11. Participant List Panel
- Toggle with 👥 button in controls
- Shows all participants with avatar initial, name, mic/cam status icons
- Live updates when anyone joins, leaves, mutes, or toggles camera
- Shows participant count in header

### 12. Pin / Spotlight
- Click 📌 on any tile to pin it (fills entire grid)
- All other tiles hidden while pinned
- Click again to unpin and restore grid
- Auto-unpins if pinned participant leaves

### 13. Noise Suppression
- Enabled by default (`noiseSuppression`, `echoCancellation`, `autoGainControl`)
- 🔉 button toggles on/off (turns red when off)
- Re-acquires audio track with new constraints
- Hot-swaps track in all peer connections via `replaceTrack` — no call drop
- Mute state preserved across toggle

### 14. Invite Link
- 🔗 Invite button in topbar copies shareable URL
- URL format: `https://your-app.up.railway.app/?room=room1`
- Opening the link pre-fills the room field automatically
- Falls back to `prompt()` dialog if clipboard API unavailable

### 15. Screen Share
- 🖥 button requests screen capture
- Requests system audio alongside video (`audio: true` in `getDisplayMedia`)
- Replaces both video and audio tracks in all peer connections
- Local tile label changes to "Name (screen)"
- Automatically switches back to camera when screen share ends
- System audio requires user to check "Share system audio" in browser dialog

### 16. Raise Hand
- ✋ button toggles hand raised state
- Bouncing hand icon appears on your tile for all participants
- Button turns yellow when hand is raised
- Broadcast via `raise_hand` WebSocket message

### 17. Emoji Reactions
- 😊 button opens emoji picker (👍 🎉 ❤️ 😂 👏 🔥)
- Clicking an emoji sends floating animation from your tile
- All participants see the reaction float up and fade out
- Broadcast via `reaction` WebSocket message

### 18. Connection Quality Indicator
- Colored dot on each remote tile (top-right corner)
- 🟢 Good: RTT < 150ms, packet loss < 2%
- 🟡 Fair: RTT < 400ms, packet loss < 8%
- 🔴 Poor: RTT > 400ms or packet loss > 8%
- Hover to see exact RTT in ms
- Updates every 3 seconds via `RTCPeerConnection.getStats()`

### 19. Meeting Timer
- Shows elapsed time in topbar (`MM:SS`, switches to `HH:MM:SS` after 1 hour)
- Starts when you successfully join a room
- Stops and resets when you leave

### 20. Recording
- ⏺ starts recording, ⏹ stops and downloads
- Records all streams (local + all remote participants)
- Saves as `recording.webm` to user's local machine

### 21. Mobile Responsive UI
- Viewport meta tag for proper mobile scaling
- Topbar compresses on small screens
- Chat panel hidden by default on mobile, slides up from bottom via 💬 button
- Controls bar spans full width at bottom on mobile
- Participant panel opens as top drawer on mobile
- Pre-join screen goes full screen on mobile

---

## Database Schema

### users table
| Column | Type | Description |
|---|---|---|
| id | Integer (PK) | Auto-increment |
| username | String | Unique, min 3 chars |
| email | String | Unique |
| hashed_password | String | bcrypt hash |

---

## Security

- Passwords hashed with bcrypt (passlib)
- JWT signed with `SECRET_KEY` — change from default in production
- Rate limiting on auth endpoints (10 req/min register/login, 20 req/min refresh)
- CORS locked to `ALLOWED_ORIGINS` env variable
- TURN credentials served server-side only — never in frontend code
- Token expiry check before WebSocket connection attempt
- Password minimum 8 characters, username minimum 3 characters

---

## Deployment (Railway)

### Initial Setup
1. Push code to GitHub (`.env` is gitignored)
2. Create Railway project → Deploy from GitHub repo
3. Add PostgreSQL plugin inside the same project
4. Set environment variables (copy from `.env.example`)
5. Railway auto-deploys on every push to `main`

### On Every Deploy
The Dockerfile runs:
```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --ws websockets --timeout-keep-alive 75
```
Migrations run first, then the server starts.

### Adding a Database Migration
When you change a model:
```bash
alembic revision --autogenerate -m "describe your change"
git add alembic/versions/
git commit -m "migration: describe your change"
git push
```

---

## Local Development

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start PostgreSQL (via Docker)
docker compose up db -d

# 4. Run migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`

---

## Known Limitations

- In-memory room state — lost on server restart (fix: Redis)
- Peer-to-peer WebRTC — degrades beyond 6 participants (fix: SFU like LiveKit)
- Single server instance — horizontal scaling requires Redis pub/sub for WebSocket routing
- Recording saves locally — no server-side storage
- Token refresh UI — silent failure if refresh token expires (user must re-login manually)

---

## Future Improvements

| Feature | Complexity | Notes |
|---|---|---|
| Redis for shared state | Medium | Survives restarts, enables multi-instance |
| SFU (LiveKit/mediasoup) | High | Required for 10+ participants |
| Room passwords | Low | Add password field to room creation |
| Server-side recording | Medium | Requires file storage (S3 or Railway volumes) |
| Token refresh failure UI | Low | Show re-login prompt when refresh fails |
| Breakout rooms | High | Sub-rooms within a main room |
| Virtual background/blur | High | Requires MediaPipe selfie segmentation |
| Push notifications | Medium | Notify when someone joins your room |
