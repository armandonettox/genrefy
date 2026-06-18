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
