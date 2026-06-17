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
