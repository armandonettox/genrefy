def run_info(sp, artist_input: str) -> dict:
    # Se for URL do Spotify, extrai o ID do artista
    if artist_input.startswith('https://'):
        artist_id = artist_input.split('/')[4].split('?')[0]
    else:
        artist_id = artist_input

    data = sp.artist(artist_id)

    return {'name': data['name'], 'genres': data['genres']}
