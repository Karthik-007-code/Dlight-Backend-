# ✈️ Dlight Aviation API

A secure, high-performance FastAPI backend proxy for the [AviationStack API](https://aviationstack.com/). It provides real-time flight tracking information with built-in JWT authentication, request caching, and dual-layered rate limiting.

---

## 🗺️ System Architecture & Request Flow

```text
                 👤 CLIENT
                    │
                    │ HTTPS + Bearer JWT
                    ↓
          ┌──────────────────────┐
          │      FASTAPI         │
          │                      │
          │      CORS            │
          │        ↓             │
          │   IP RATE LIMIT      │
          │     30/min           │
          └──────────┬───────────┘
                     │
                     ↓
              🔐 AUTHENTICATION
                     │
                  JWT valid?
                     │
                     ↓
               Daily Quota
                 200/day
                     │
                     ↓
             ✈️ FLIGHT ROUTER
                     │
                     ↓
              🔎 CHECK CACHE
                     │
             ┌───────┴───────┐
             │               │
          HIT ✅           MISS ❌
             │               │
             ↓               ↓
       CACHE DATA       SERVICE LAYER
             │               │
             │               ↓
             │          httpx Async
             │               │
             │               ↓
             │        ✈️ AviationStack
             │               │
             │               ↓
             │          Flight Data
             │               │
             │               ↓
             │          Save to Cache
             │               │
             └───────┬───────┘
                     ↓
               📤 RESPONSE
                     │
                     ↓
                  👤 CLIENT
```

---

## 🚀 Key Features

*   **FastAPI Framework**: Leveraging asynchronous handling for fast and non-blocking I/O operations.
*   **Secure Authentication**: Standard OAuth2 Password Bearer flow using JWT access tokens (short-lived) and cryptographically secure refresh tokens (stored in DB).
*   **Dual-Layer Rate Limiting**:
    *   **IP-level limit**: Restricted to 30 requests per minute per IP via `slowapi` to prevent DDoS and spam.
    *   **User-level limit**: Stateful quota of 200 requests per day per authenticated user (tracked and stored in SQLite, resetting daily at midnight UTC).
*   **In-Memory TTL Caching**: Custom cache layer utilizing `cachetools` with a 60-second TTL. Reduces duplicate external API latency to sub-milliseconds and preserves API quota.
*   **Audit Logging**: Every incoming proxy request and API outcome is tracked in a local `UsageLog` database table for analytics and usage transparency.
*   **Resource Pooling**: Employs a shared `httpx.AsyncClient` lifespan session to maintain stable connection pools.

---

## 📁 Project Structure

```text
Dlight/
├── main.py                     # Entry point (FastAPI initialization, middleware, routes)
├── database.py                 # SQLAlchemy connection, Engine and DB session dependency
├── models.py                   # SQLAlchemy database schemas (User, RefreshToken, UsageLog)
├── schemas.py                  # Pydantic models for request & response validation
├── auth/                       
│   ├── jwt.py                  # Token signing, encoding, and decoding utilities
│   └── dependencies.py         # Authentication guards (get_current_user)
├── middleware/                 
│   └── rate_limit.py           # Custom per-user daily rate limiter dependency
├── routers/                    
│   ├── auth.py                 # User onboarding & auth controller (/auth/signup, /auth/login)
│   └── flights.py              # Flights search proxy controller (/v1/flights)
└── services/                   
    ├── aviation.py             # Integration layer with external AviationStack API (httpx)
    └── cache.py                # In-memory memory caching engine (cachetools)
```

---

## 🛠️ Getting Started

### 1. Prerequisites
*   Python 3.10 or higher
*   An active [AviationStack API Key](https://aviationstack.com/)

### 2. Installation & Setup
1. Clone this repository to your local machine.
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Environment Configuration
Create a `.env` file in the root directory and add the following settings:
```ini
DATABASE_URL=sqlite:///./dlight.db
JWT_SECRET_KEY=your_super_secret_jwt_key_here
AVIATION_API_KEY=your_aviation_stack_api_key_here
USER_DAILY_LIMIT=200
IP_RATE_LIMIT=30/minute
```

### 4. Running the Application
Start the development server with hot-reload enabled:
```bash
uvicorn main:app --reload
```
Once started, you can access the interactive API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## 🔒 API Specifications & Workflow

### 🔑 Authentication Flow
1. **Sign Up**: Register a new user at `POST /auth/signup`.
2. **Log In**: Authenticate credentials at `POST /auth/login` to receive an `access_token` and a `refresh_token`.
3. **Protected Access**: Include the access token in all requests to `/v1/flights` as a Bearer token:
   `Authorization: Bearer <your_access_token>`
4. **Token Refresh**: When the access token expires, use `POST /auth/refresh` with your refresh token to get a new access token.

### ✈️ Flights Query Flow (`GET /v1/flights`)
1. User provides flight search queries (such as `flight_iata`, `airline_name`, `dep_iata`, etc.).
2. The request is vetted against IP limits and user limits.
3. The cache is evaluated against the query parameters:
   * **Cache Hit**: Data is returned immediately (response time < 5ms).
   * **Cache Miss**: An async request fetches fresh data from AviationStack, caches it, and serves the user.
4. The backend registers the query context, user, timestamp, and status code into `UsageLog`.
