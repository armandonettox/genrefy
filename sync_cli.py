import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from commands.reload import run_reload
from spotify_client import (
    create_spotify_client,
    load_aliases,
    load_artist_cache,
    load_overrides,
    load_playlist_config,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')


def _build_artist_map(user_id: str) -> dict | None:
    cached = load_artist_cache(user_id)
    if not cached:
        return None
    artist_map = {a['id']: a.get('genres', []) for a in cached}
    artist_map.update(load_overrides(user_id))
    return artist_map or None


def main() -> None:
    refresh_token = os.environ.get('SPOTIFY_REFRESH_TOKEN')
    if not refresh_token:
        sys.exit('SPOTIFY_REFRESH_TOKEN nao definido')

    client_id = os.environ.get('SPOTIFY_CLIENT_ID', '')
    client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
    redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:8080/callback')

    if not client_id or not client_secret:
        sys.exit('SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET sao obrigatorios')

    scope = (
        'user-read-email user-read-private '
        'playlist-read-collaborative playlist-modify-public '
        'playlist-read-private playlist-modify-private '
        'user-library-modify user-library-read user-top-read'
    )

    # Cria cache temporario pre-populado com o refresh_token.
    # expires_at=0 forca o spotipy a renovar o access_token automaticamente.
    token_data = {
        'access_token': '',
        'token_type': 'Bearer',
        'expires_in': 3600,
        'refresh_token': refresh_token,
        'scope': scope,
        'expires_at': 0,
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(token_data, f)
        cache_path = f.name

    try:
        auth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=cache_path,
            open_browser=False,
        )
        sp = create_spotify_client(auth)
        user_id = sp.current_user()['id']
        logging.info('Autenticado como: %s', user_id)

        playlists = load_playlist_config(user_id)
        if not playlists:
            sys.exit(
                f'Nenhuma config de playlist salva para {user_id}. '
                'Execute o sync pela UI pelo menos uma vez para salvar a configuracao.'
            )

        artist_map = _build_artist_map(user_id)
        aliases = load_aliases(user_id)
        multi_artist = os.environ.get('SYNC_MULTI_ARTIST', '').lower() in ('1', 'true', 'yes')

        logging.info('Sincronizando %d playlist(s)...', len(playlists))
        _, summary = run_reload(
            sp,
            playlists,
            progress_callback=logging.info,
            artist_map=artist_map,
            aliases=aliases,
            multi_artist=multi_artist,
        )

        for name, count in summary.items():
            logging.info('%s: %d faixas', name, count)

        logging.info('Sync concluido.')

    finally:
        Path(cache_path).unlink(missing_ok=True)


if __name__ == '__main__':
    main()
