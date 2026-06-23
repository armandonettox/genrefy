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

from spotify_client import get_saved_tracks, decorate_artist_genres


def _get_playlist_uris(sp, pid: str) -> list[str]:
    """Retorna URIs das faixas atuais de uma playlist em ordem."""
    uris = []
    results = sp.playlist_items(pid, fields='items(track(uri)),next', limit=100)
    while True:
        uris.extend(item['track']['uri'] for item in results['items'] if item.get('track'))
        if not results.get('next'):
            break
        results = sp.next(results)
    return uris


def _filter_tracks_for_playlist(playlist: dict, decorated_tracks: list[dict]) -> list[dict]:
    """Aplica as regras de filtragem de uma playlist sem alterar estado externo."""
    playlist_tracks = [{'track': t['track'], 'genres': list(t['genres'])} for t in decorated_tracks]

    if playlist.get('aoverride'):
        for track in playlist_tracks:
            artist_name = track['track']['artists'][0]['name']
            if artist_name in playlist['aoverride']:
                track['genres'].append(playlist['genres'][0])

    filtered = [
        t for t in playlist_tracks
        if any(g in playlist['genres'] for g in t['genres'])
    ]

    if playlist.get('ngenres'):
        filtered = [
            t for t in filtered
            if not any(g in playlist['ngenres'] for g in t['genres'])
        ]

    filtered.sort(key=lambda t: (
        t['track']['artists'][0]['name'],
        t['track']['album']['name']
    ))

    return filtered


def plan_reload(sp, playlists: list[dict], cached_tracks=None, artist_map=None) -> dict:
    """
    Calcula o diff de cada playlist sem modificar nada no Spotify.
    Retorna {nome: {'pid': str, 'add': [uri], 'remove': [uri], 'keep': int, 'current': [uri]}}.
    'current' contem as URIs atuais da playlist em ordem (usado para snapshot de undo).
    """
    tracks = cached_tracks if cached_tracks is not None else get_saved_tracks(sp)
    decorated = decorate_artist_genres(sp, tracks, artist_map=artist_map)

    result = {}
    for playlist in playlists:
        pid = playlist['id']
        current_uris_list = _get_playlist_uris(sp, pid)
        current_uris = set(current_uris_list)
        filtered = _filter_tracks_for_playlist(playlist, decorated)
        filtered_uris = [t['track']['uri'] for t in filtered]
        filtered_set = set(filtered_uris)

        result[playlist['name']] = {
            'pid': pid,
            'add': [u for u in filtered_uris if u not in current_uris],
            'remove': list(current_uris - filtered_set),
            'keep': len(current_uris & filtered_set),
            'current': current_uris_list,
        }

    return result


def run_reload(sp, playlists, progress_callback=None, cached_tracks=None, artist_map=None, plan=None) -> tuple[list[str], dict]:
    """
    Sincroniza playlists de forma incremental: remove apenas o que saiu, adiciona apenas o que entrou.
    Se plan for fornecido (de plan_reload), usa o diff pre-calculado sem chamadas extras a API.
    Retorna (logs, summary). summary e {nome_playlist: contagem_final_de_tracks}.
    """
    logs = []
    summary = {}

    def log(msg):
        logs.append(msg)
        if progress_callback:
            progress_callback(msg)

    tracks = cached_tracks if cached_tracks is not None else get_saved_tracks(sp)
    log(f'Successfully loaded {len(tracks)} songs')

    decorated = decorate_artist_genres(sp, tracks, progress_callback=log, artist_map=artist_map)

    no_genre = sum(1 for t in decorated if not t['genres'])
    log(f'{no_genre}/{len(decorated)} tracks sem genero (artistas sem dados no Spotify)')

    log(f'Populando {len(playlists)} playlist(s)')

    chunk_size = 100

    for playlist in playlists:
        name = playlist['name']
        pid = playlist['id']
        log(f"Populando '{name}'")

        if plan is not None and name in plan:
            p = plan[name]
            add_uris = p['add']
            remove_uris = p['remove']
            total = p['keep'] + len(add_uris)
        else:
            current_uris = set(_get_playlist_uris(sp, pid))
            filtered = _filter_tracks_for_playlist(playlist, decorated)
            filtered_uris = [t['track']['uri'] for t in filtered]
            filtered_set = set(filtered_uris)
            add_uris = [u for u in filtered_uris if u not in current_uris]
            remove_uris = list(current_uris - filtered_set)
            total = len(filtered_uris)

        summary[name] = total
        log(f'  +{len(add_uris)} adicionadas, -{len(remove_uris)} removidas, total: {total}')
        if not total:
            log(f'  AVISO: nenhuma track correspondeu aos generos desta playlist')

        for i in range(0, len(remove_uris), chunk_size):
            sp.playlist_remove_all_occurrences_of_items(pid, remove_uris[i:i + chunk_size])

        for i in range(0, len(add_uris), chunk_size):
            log(f'  Adicionando chunk {i}–{i + chunk_size}...')
            sp.playlist_add_items(pid, add_uris[i:i + chunk_size])

    log('Reload concluido.')
    return logs, summary
