# Spotify Analyzer

Spotify Analyzer is a demo project consisting of a FastAPI backend and a React frontend. The backend communicates with the Spotify API and stores data in MongoDB.

## Environment Variables
Create a `.env` file in the `Backend` directory (or set the variables in your environment) with at least the following settings:

- `SPOTIPY_CLIENT_ID` – Spotify API client ID
- `SPOTIPY_CLIENT_SECRET` – Spotify API client secret
- `SPOTIPY_REDIRECT_URI` – redirect URI registered with Spotify
- `MONGO_URI` – connection string for MongoDB

Optional variables used by the backend:

- `MONGO_DB` – Mongo database name (default `spotify_analytics`)
- `FRONTEND_REDIRECT_URI` – URL to redirect after login (default `http://127.0.0.1:5173?login=success`)
- `HOST` – binding host for the API server (default `0.0.0.0`)
- `PORT` – binding port for the API server (default `8080`)
- `DEBUG_MODE` – set to `true` for auto reload

## Running the FastAPI Backend
```bash
cd Backend
pip install -r requirements.txt
python app.py
```
The server will start on `http://0.0.0.0:8080` unless overridden by the environment variables above.

## Running the React Frontend
```bash
cd Frontend/spotify-analyzer
npm install
npm run dev
```
This starts the Vite development server, typically reachable at `http://localhost:5173`.
The frontend expects an API endpoint specified in `Frontend/spotify-analyzer/.env`:

```
VITE_API_URL=http://127.0.0.1:8080
```

If your backend is running on a different host or port (for example when using a
remote container), update `VITE_API_URL` accordingly so that login redirects work
correctly.
