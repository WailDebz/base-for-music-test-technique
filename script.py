import pandas as pd
import psycopg2
import re
import json

# 1. CONFIGURATION
DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'i8D22021&',
    'host': 'localhost',
    'port': '5432'
}

# Creation des tables
def setup_database_schema(conn):
    drop_tables_sql = "DROP TABLE IF EXISTS Performances, Sing, Songs, Artists CASCADE;"
    create_tables_sql = """
        CREATE TABLE Artists (
            Artist_ID BIGINT PRIMARY KEY,
            Name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE Songs (
            Song_ID INTEGER PRIMARY KEY,
            Title TEXT,
            Release_date DATE,
            Cover_URL TEXT
        );
        CREATE TABLE Sing (
            Artist_ID BIGINT REFERENCES Artists(Artist_ID) ON DELETE CASCADE,
            Song_ID INTEGER REFERENCES Songs(Song_ID) ON DELETE CASCADE,
            PRIMARY KEY (Artist_ID, Song_ID)
        );
        CREATE TABLE Performances (
            Song_ID INTEGER REFERENCES Songs(Song_ID) ON DELETE CASCADE,
            Date DATE,
            Streams BIGINT,
            Popularity INTEGER,
            PRIMARY KEY (Song_ID, Date)
        );
    """
    try:
        with conn.cursor() as cur:
            cur.execute(drop_tables_sql)
            cur.execute(create_tables_sql)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e

# 2. LECTURE ET NETTOYAGE
print("Lecture du fichier ")
try:
    df = pd.read_csv("100-songs-audience-report.csv", dtype=str).fillna('')
    nom_reel_de_la_colonne = df.columns[0]
    if nom_reel_de_la_colonne != 'song_id':
        df.rename(columns={nom_reel_de_la_colonne: 'song_id'}, inplace=True)
except Exception as e:
    print(f"Une erreur est survenue lors de la lecture ou du nettoyage : {e}")
    exit()

# 3. PRÉPARATION DES DONNÉES
print("\nPréparation des données pour l'insertion...")

artist_map = {}
artist_id_counter = 1
song_map = {}
song_id_counter = 1

artist_rows, song_rows, sing_rows, performance_rows = [], [], [], []

def process_artists(artist_str):
    if not isinstance(artist_str, str) or not artist_str.strip(): return []
    return [a.strip() for a in re.split(r'[&,]| feat\.?| and ', artist_str, flags=re.IGNORECASE)]

def next_artist_id():
    global artist_id_counter
    artist_id_counter += 1
    return artist_id_counter

def next_song_id():
    global song_id_counter
    song_id_counter += 1
    return song_id_counter

for index, row in df.iterrows():
    original_song_id = row['song_id'].strip()
    if not original_song_id: continue

    if original_song_id not in song_map:
        new_int_id = next_song_id()
        song_map[original_song_id] = new_int_id
        
        title = row['title'].strip()
        image_url = row['image_url'].strip()
        release_date = row['release_date'].split('T')[0] if 'T' in row['release_date'] else row['release_date']
        if release_date == '' or release_date.startswith('0000'):
            release_date = None
        
        song_rows.append((new_int_id, title, release_date, image_url))
    
    current_song_int_id = song_map[original_song_id]
    
    # Preparation de la donnée artist
    artists = process_artists(row['artist'])
    for artist in artists:
        if artist not in artist_map:
            artist_map[artist] = next_artist_id()
            artist_rows.append((artist_map[artist], artist))
        sing_rows.append((artist_map[artist], current_song_int_id))

    # La table performances 
    time_series_str = row['timeSeries'].strip()
    if time_series_str:
        try:
            time_series_data = json.loads(time_series_str)
            for item in time_series_data:
                date = item.get('date')
                if date:
                    streams = item.get('spotify-streams')
                    popularity = item.get('spotify-popularity')
                    streams_val = int(streams) if streams is not None else None
                    popularity_val = int(popularity) if popularity is not None else None
                    performance_rows.append((date.split('T')[0], streams_val, popularity_val, current_song_int_id))
        except (json.JSONDecodeError, ValueError):
            continue

# 4. CONNEXION ET INSERTION
conn = None
try:
    print("\nConnexion à la base de données PostgreSQL")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("Connexion réussie.")

    # Création automatique du schéma
    setup_database_schema(conn)

    print("Insertion des données")
    cur.executemany("INSERT INTO Artists (Artist_ID, Name) VALUES (%s, %s) ON CONFLICT (Artist_ID) DO NOTHING;", artist_rows)
    cur.executemany("INSERT INTO Songs (Song_ID, Title, Release_date, Cover_URL) VALUES (%s, %s, %s, %s) ON CONFLICT (Song_ID) DO NOTHING;", song_rows)
    cur.executemany("INSERT INTO Sing (Artist_ID, Song_ID) VALUES (%s, %s) ON CONFLICT (Artist_ID, Song_ID) DO NOTHING;", sing_rows)
    if performance_rows:
        cur.executemany("INSERT INTO Performances (Date, Streams, Popularity, Song_ID) VALUES (%s, %s, %s, %s) ON CONFLICT (Song_ID, Date) DO NOTHING;", performance_rows)
    
    conn.commit()
    print("\nOpération terminée avec succès.")

except Exception as e:
    print(f"\nErreur : {e}")
    if conn: conn.rollback()
finally:
    if conn:
        if cur: cur.close()
        conn.close()
        print("Connexion à la base de données fermée.")