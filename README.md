Your whole architecture in one simple diagram
                 👤 CLIENT
                    │
                    │ HTTPS + JWT
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
                  