# genrefy — Distribui musicas curtidas do Spotify em playlists por genero
# Copyright (C) 2026 Armando Netto <armandosln7@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import json
import logging
import os
import time
from pathlib import Path

import spotipy
import spotipy.exceptions
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(os.getenv('ARTIST_CACHE_DIR', '/app/cache'))
_CACHE_TTL = 86400  # 24 horas

def _artist_cache_path(user_id: str) -> Path:
    return _CACHE_DIR / f'artists_{user_id}.json'


def load_artist_cache(user_id: str) -> list[dict] | None:
    path = _artist_cache_path(user_id)
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding='utf-8'))
        age = time.time() - data.get('timestamp', 0)
        if age > _CACHE_TTL:
            logger.info('Cache de artistas expirado')
            return None
        artists = data.get('artists', [])
        logger.info(f'Cache de artistas carregado: {len(artists)} artistas')
        return artists
    except Exception as e:
        logger.warning(f'Erro ao ler cache de artistas: {e}')
        return None


def save_artist_cache(user_id: str, artists: list[dict]) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _artist_cache_path(user_id)
        path.write_text(
            json.dumps({'timestamp': time.time(), 'artists': artists}, ensure_ascii=False),
            encoding='utf-8',
        )
        logger.info(f'Cache de artistas salvo: {len(artists)} artistas')
    except Exception as e:
        logger.warning(f'Erro ao salvar cache de artistas: {e}')


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
    return spotipy.Spotify(auth_manager=auth_manager, requests_timeout=15, retries=1)


def is_authenticated(auth_manager: SpotifyOAuth) -> bool:
    try:
        token = auth_manager.get_cached_token()
        return token is not None and not auth_manager.is_token_expired(token)
    except Exception:
        return False


def get_saved_tracks(sp: spotipy.Spotify, on_progress=None) -> list[dict]:
    tracks = []
    offset = 0
    total = None
    while True:
        results = sp.current_user_saved_tracks(limit=50, offset=offset)
        if total is None:
            total = results['total']
        tracks.extend(results['items'])
        if on_progress and total:
            on_progress(len(tracks), total)
        if not results['next']:
            break
        offset += 50
        logger.info(f'Carregando tracks com offset: {offset}')
    return tracks


def get_artists_for_tracks(sp: spotipy.Spotify, tracks: list[dict], progress_callback=None, on_progress=None) -> tuple[list[dict], list[str]]:
    """Retorna (artistas, erros). erros e uma lista de strings descrevendo falhas."""
    seen = set()
    artist_ids = []
    for t in tracks:
        aid = t['track']['artists'][0].get('id')
        if aid and aid not in seen:
            seen.add(aid)
            artist_ids.append(aid)

    total = len(artist_ids)
    artists = []
    errors = []
    batch_size = 50
    num_batches = (total + batch_size - 1) // batch_size
    use_individual = False

    for batch_num, i in enumerate(range(0, total, batch_size)):
        batch = artist_ids[i:i + batch_size]
        fetched = []

        if not use_individual:
            try:
                result = sp.artists(batch)
                fetched = [a for a in result.get('artists', []) if a]
                logger.info(f'Lote {batch_num + 1}/{num_batches}: {len(fetched)} artistas (batch)')
            except spotipy.exceptions.SpotifyException as e:
                msg = f'sp.artists() HTTP {e.http_status}: {e}'
                errors.append(msg)
                logger.warning(msg)
                if e.http_status in (400, 403):
                    logger.warning('Alternando para chamadas individuais')
                    use_individual = True
            except Exception as e:
                msg = f'sp.artists() {type(e).__name__}: {e}'
                errors.append(msg)
                logger.error(msg)
                use_individual = True

        if use_individual:
            for aid in batch:
                try:
                    a = sp.artist(aid)
                    fetched.append(a)
                except Exception as e:
                    msg = f'sp.artist({aid}) {type(e).__name__}: {e}'
                    errors.append(msg)
                    logger.error(msg)
            logger.info(f'Lote {batch_num + 1}/{num_batches}: {len(fetched)} artistas (individual)')

        artists.extend(fetched)

        if progress_callback:
            progress_callback(f'Carregando artistas: {min(i + batch_size, total)}/{total}...')
        elif on_progress:
            on_progress(min(i + batch_size, total), total)

    logger.info(f'Artistas carregados: {len(artists)}/{total}')
    return artists, errors


def get_user_playlists(sp: spotipy.Spotify) -> list[dict]:
    playlists = []
    results = sp.current_user_playlists(limit=50)
    while results:
        for item in results['items']:
            if item:
                playlists.append({'id': item['id'], 'name': item['name']})
        results = sp.next(results) if results.get('next') else None
    return playlists


def get_library_data(sp: spotipy.Spotify, on_progress=None) -> tuple[list[str], list[str], list[dict]]:
    """Retorna (genres, artists, tracks). on_progress(pct: float 0-1, msg: str) e chamado durante o carregamento."""

    def tracks_progress(done, total):
        if on_progress:
            on_progress(done / total, f'Musicas: {done}/{total}')

    tracks = get_saved_tracks(sp, on_progress=tracks_progress)

    if on_progress:
        on_progress(0.5, 'Carregando dados dos artistas...')

    artists, _ = get_artists_for_tracks(sp, tracks)
    all_genres = sorted({g for a in artists for g in a.get('genres', [])})
    all_artists = sorted({a['name'] for a in artists})
    return all_genres, all_artists, tracks


def get_library_genres_and_artists(sp: spotipy.Spotify) -> tuple[list[str], list[str]]:
    tracks = get_saved_tracks(sp)
    artists, _ = get_artists_for_tracks(sp, tracks)
    all_genres = sorted({g for a in artists for g in a.get('genres', [])})
    all_artists = sorted({a['name'] for a in artists})
    return all_genres, all_artists


def decorate_artist_genres(sp: spotipy.Spotify, tracks: list[dict], progress_callback=None) -> list[dict]:
    if progress_callback:
        progress_callback('Buscando generos dos artistas...')
    artist_data, _ = get_artists_for_tracks(sp, tracks, progress_callback=progress_callback)
    artist_map = {a['id']: a.get('genres', []) for a in artist_data}

    decorated = []
    for track in tracks:
        artist_id = track['track']['artists'][0]['id']
        decorated.append({
            **track,
            'genres': list(artist_map.get(artist_id, [])),
        })

    logger.info('Dados de artistas e generos carregados com sucesso')
    return decorated
