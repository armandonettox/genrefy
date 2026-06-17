import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

logger = logging.getLogger(__name__)


def create_auth_manager() -> SpotifyOAuth:
    config_path = Path(__file__).parent / 'config' / 'production.json'
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)

    spotify_cfg = config['spotify']

    return SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID', spotify_cfg.get('client_id', '')),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET', spotify_cfg.get('client_secret', '')),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI', spotify_cfg['redirect_uri']),
        scope=' '.join(spotify_cfg['scopes']),
        cache_path=os.getenv('SPOTIFY_TOKEN_CACHE', '.spotify_cache'),
        open_browser=False,
    )


def create_spotify_client(auth_manager: SpotifyOAuth) -> spotipy.Spotify:
    return spotipy.Spotify(auth_manager=auth_manager)


def is_authenticated(auth_manager: SpotifyOAuth) -> bool:
    try:
        token = auth_manager.get_cached_token()
        return token is not None and not auth_manager.is_token_expired(token)
    except Exception:
        return False


def get_saved_tracks(sp: spotipy.Spotify) -> list[dict]:
    tracks = []
    offset = 0
    while True:
        results = sp.current_user_saved_tracks(limit=50, offset=offset)
        tracks.extend(results['items'])
        if not results['next']:
            break
        offset += 50
        logger.info(f'Carregando tracks com offset: {offset}')
    return tracks


def get_artists_for_tracks(sp: spotipy.Spotify, tracks: list[dict]) -> list[dict]:
    seen = set()
    artist_ids = []
    for t in tracks:
        aid = t['track']['artists'][0]['id']
        if aid not in seen:
            seen.add(aid)
            artist_ids.append(aid)

    artists = []
    total = len(artist_ids)

    def fetch(aid):
        return sp.artist(aid)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch, aid): aid for aid in artist_ids}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                logger.info(f'Carregando artistas {done}/{total}...')
            try:
                artists.append(future.result())
            except Exception as e:
                logger.warning(f'Erro ao carregar artista {futures[future]}: {e}')

    return artists


def decorate_artist_genres(sp: spotipy.Spotify, tracks: list[dict]) -> list[dict]:
    logger.info('Carregando informacoes de genero dos artistas...')
    artist_data = get_artists_for_tracks(sp, tracks)
    artist_map = {a['id']: a['genres'] for a in artist_data}

    decorated = []
    for track in tracks:
        artist_id = track['track']['artists'][0]['id']
        decorated.append({
            **track,
            'genres': list(artist_map.get(artist_id, [])),
        })

    logger.info('Dados de artistas e generos carregados com sucesso')
    return decorated
