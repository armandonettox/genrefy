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

import csv
import os

from spotify_client import get_artists_for_tracks, get_saved_tracks


def run_genres(sp) -> str:
    tracks = get_saved_tracks(sp)
    artists = get_artists_for_tracks(sp, tracks)

    artists.sort(key=lambda a: a['name'])

    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output.csv')

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'genres'])
        for artist in artists:
            writer.writerow([artist['name'], ','.join(artist['genres'])])

    return os.path.abspath(output_path)
