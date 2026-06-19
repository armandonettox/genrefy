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
    return spotipy.Spotify(auth_manager=auth_manager, requests_timeout=10)


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


def get_artists_for_tracks(sp: spotipy.Spotify, tracks: list[dict], progress_callback=None, on_progress=None) -> list[dict]:
    seen = set()
    artist_ids = []
    for t in tracks:
        aid = t['track']['artists'][0].get('id')
        if aid and aid not in seen:
            seen.add(aid)
            artist_ids.append(aid)

    total = len(artist_ids)
    artists = []

    for i, aid in enumerate(artist_ids):
        try:
            artists.append(sp.artist(aid))
        except Exception as e:
            logger.warning(f'Erro ao carregar artista {aid}: {e}')
        done = i + 1
        if progress_callback and done % 20 == 0:
            progress_callback(f'Carregando artistas: {done}/{total}...')
        elif done % 50 == 0:
            logger.info(f'Carregando artistas {done}/{total}...')

    logger.info(f'Artistas carregados: {len(artists)}/{total}')

    if not artists and total > 0:
        raise RuntimeError(
            f'Nenhum artista retornado pela API do Spotify ({total} IDs enviados, 0 recebidos).'
        )

    return artists


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
            on_progress(done / total, f'Músicas: {done}/{total}')

    tracks = get_saved_tracks(sp, on_progress=tracks_progress)

    if on_progress:
        on_progress(0.5, 'Carregando dados dos artistas...')

    artists = get_artists_for_tracks(sp, tracks)
    all_genres = sorted({g for a in artists for g in a['genres']})
    all_artists = sorted({a['name'] for a in artists})
    return all_genres, all_artists, tracks


def get_library_genres_and_artists(sp: spotipy.Spotify) -> tuple[list[str], list[str]]:
    tracks = get_saved_tracks(sp)
    artists = get_artists_for_tracks(sp, tracks)
    all_genres = sorted({g for a in artists for g in a['genres']})
    all_artists = sorted({a['name'] for a in artists})
    return all_genres, all_artists


def decorate_artist_genres(sp: spotipy.Spotify, tracks: list[dict], progress_callback=None) -> list[dict]:
    if progress_callback:
        progress_callback('Buscando gêneros dos artistas...')
    artist_data = get_artists_for_tracks(sp, tracks, progress_callback=progress_callback)
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
