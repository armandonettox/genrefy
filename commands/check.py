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

from spotify_client import get_saved_tracks, get_artists_for_tracks


def run_check(sp, playlists) -> list[dict]:
    tracks = get_saved_tracks(sp)
    artist_data = get_artists_for_tracks(sp, tracks)

    all_genres = [g for p in playlists for g in p['genres']]

    missing = [
        a for a in artist_data
        if not any(g in all_genres for g in a['genres'])
    ]

    all_overrides = [name for p in playlists for name in p.get('aoverride', [])]
    if all_overrides:
        missing = [a for a in missing if a['name'] not in all_overrides]

    return [
        {
            'name': a['name'],
            'genres': a['genres'],
            'image': a['images'][0]['url'] if a.get('images') else '',
        }
        for a in missing
    ]
