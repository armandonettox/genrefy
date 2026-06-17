from spotify_client import get_saved_tracks, decorate_artist_genres


def _remove_all_playlist_tracks(sp, pid):
    """Remove todas as faixas de uma playlist em lotes de 100."""
    while True:
        results = sp.playlist_items(pid, limit=100, fields='items(track(uri)),next')
        uris = [item['track']['uri'] for item in results['items'] if item['track']]
        if not uris:
            break
        sp.playlist_remove_all_occurrences_of_items(pid, uris)
        if not results['next']:
            break


def run_reload(sp, playlists, progress_callback=None) -> tuple[list[str], dict]:
    """Retorna (logs, summary). summary e {nome_playlist: contagem_de_tracks}."""
    logs = []
    summary = {}

    def log(msg):
        logs.append(msg)
        if progress_callback:
            progress_callback(msg)

    # Busca todas as musicas curtidas e decora com generos dos artistas
    tracks = get_saved_tracks(sp)
    log(f'Successfully loaded {len(tracks)} songs')

    decorated_tracks = decorate_artist_genres(sp, tracks, progress_callback=log)

    no_genre = sum(1 for t in decorated_tracks if not t['genres'])
    log(f'{no_genre}/{len(decorated_tracks)} tracks sem genero (artistas sem dados no Spotify)')

    log(f'Populating {len(playlists)} playlist(s)')

    for playlist in playlists:
        log(f"Populating playlist '{playlist['name']}'")

        pid = playlist['id']

        # Verifica se ha faixas antes de tentar remover
        current = sp.playlist_items(pid, limit=1, fields='total')
        if current.get('total', 0) > 0:
            _remove_all_playlist_tracks(sp, pid)

        # Cria copia por playlist para evitar que aoverride de uma playlist
        # contamine as demais (genres sao mutados em-place na logica sem copia)
        playlist_tracks = [{'track': t['track'], 'genres': list(t['genres'])} for t in decorated_tracks]

        # Aplica aoverride: injeta o primeiro genero da playlist nas tracks dos artistas listados
        # Isso acontece ANTES da filtragem — nao e um bypass
        if playlist.get('aoverride'):
            for track in playlist_tracks:
                artist_name = track['track']['artists'][0]['name']
                if artist_name in playlist['aoverride']:
                    track['genres'].append(playlist['genres'][0])

        # Filtra: mantém apenas tracks que tenham pelo menos um genero da playlist
        filtered = [
            t for t in playlist_tracks
            if any(g in playlist['genres'] for g in t['genres'])
        ]

        # Remove tracks que tenham qualquer genero em ngenres (ngenres tem precedencia absoluta)
        if playlist.get('ngenres'):
            filtered = [
                t for t in filtered
                if not any(g in playlist['ngenres'] for g in t['genres'])
            ]

        summary[playlist['name']] = len(filtered)
        log(f"  {len(filtered)} tracks corresponderam aos filtros")
        if not filtered:
            log(f"  AVISO: nenhuma track correspondeu aos generos desta playlist")

        # Ordena por nome do artista, e dentro do mesmo artista por nome do album
        filtered.sort(key=lambda t: (
            t['track']['artists'][0]['name'],
            t['track']['album']['name']
        ))

        # Adiciona as faixas filtradas em chunks de 100
        chunk_size = 100
        for i in range(0, len(filtered), chunk_size):
            chunk = filtered[i:i + chunk_size]
            if not chunk:
                break
            log(f'  Adicionando chunk {i}–{i + chunk_size}...')
            sp.playlist_add_items(pid, [t['track']['uri'] for t in chunk])

    log('Reload concluído.')
    return logs, summary
