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

def run_info(sp, artist_input: str) -> dict:
    # Se for URL do Spotify, extrai o ID do artista
    if artist_input.startswith('https://'):
        artist_id = artist_input.split('/')[4].split('?')[0]
    else:
        artist_id = artist_input

    data = sp.artist(artist_id)

    return {'name': data['name'], 'genres': data.get('genres', []), '_raw_keys': list(data.keys())}
