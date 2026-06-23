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

import re

from spotify_client import get_genres_from_musicbrainz

_SPOTIFY_ID_RE = re.compile(r'^[A-Za-z0-9]{22}$')
_SPOTIFY_URL_RE = re.compile(r'open\.spotify\.com/artist/([A-Za-z0-9]{22})')
_SPOTIFY_URI_RE = re.compile(r'^spotify:artist:([A-Za-z0-9]{22})$')


def _extract_artist_id(artist_input: str) -> str:
    m = _SPOTIFY_URL_RE.search(artist_input)
    if m:
        return m.group(1)
    m = _SPOTIFY_URI_RE.match(artist_input)
    if m:
        return m.group(1)
    if _SPOTIFY_ID_RE.match(artist_input):
        return artist_input
    raise ValueError(
        "Entrada inválida. Informe um ID de artista (22 caracteres), "
        "URL (https://open.spotify.com/artist/...) ou URI (spotify:artist:...)."
    )


def run_info(sp, artist_input: str) -> dict:
    artist_id = _extract_artist_id(artist_input)

    data = sp.artist(artist_id)
    genres = data.get('genres', [])

    if not genres:
        genres = get_genres_from_musicbrainz(data['name'])

    return {'id': artist_id, 'name': data['name'], 'genres': genres, '_raw_keys': list(data.keys())}
