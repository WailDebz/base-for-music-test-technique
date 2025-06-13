# Test Technique - Base for Music (Data Engineering)

Ce dépôt contient ma réponse au test technique pour le poste de Développeur Backend / Data Engineer chez Base for Music. Le projet consiste à modéliser, enrichir et analyser un jeu de données fourni par Soundcharts.

## Approche et Méthodologie

Le travail a été structuré en deux étapes principales, conformément à l'énoncé du test, avec un accent particulier sur la robustesse du traitement des données et la pertinence des analyses.

### Étape 1 : Modélisation de la Donnée

L'objectif était de transformer une donnée brute (CSV avec JSON imbriqué) en une structure relationnelle propre et performante sous PostgreSQL.

1.  **Analyse de la source :** Une première analyse a révélé plusieurs défis : formatage des noms de colonnes, données composites (multiples artistes par chanson), et surtout, des problèmes de qualité de données (dates invalides, corruption de fichier, clés JSON manquantes).
2.  **Schéma de la base de données :** Un schéma relationnel normalisé (3FN) a été conçu avec quatre tables principales : `Artists`, `Songs`, `Performances` (données temporelles) et `Sing` (table de jonction).
    * **Points notables :**
        * Utilisation de clés primaires numériques (`INTEGER`/`BIGINT`) pour des performances optimales.
        * Choix du type `BIGINT` pour la colonne `Streams`  après avoir identifié que les données pouvaient dépasser la capacité du type `INTEGER`.
3.  **Pipeline d'ingestion (ETL) :** Un script Python robuste a été développé pour :
    * Nettoyer les données sources.
    * Parser les chaînes d'artistes pour gérer les featurings.
    * Générer des clés primaires numériques.
    * Extraire et aplatir les données JSON de la colonne `timeSeries`.
    * Gérer les cas de données manquantes (clés JSON absentes, dates invalides) en les transformant en `NULL`.
    * Insérer les données propres dans la base de données PostgreSQL de manière idempotente (le script gère la recréation du schéma).
 4. **Suppression de la redondance** : La colonne summaries a été délibérément écartée. Elle contenait des données agrégées (total des streams, etc.) qui sont entièrement calculables à partir des données détaillées de la colonne timeSeries. La supprimer garantit une source de vérité unique et évite les problèmes de désynchronisation des données.

### Étape 2 : Analyse

1. **Classement des Artistes et Chansons**

**Top Artistes** : Un classement par total de streams cumulés a été généré. Le top 5 est le suivant :

* Taylor Swift (1.74e+10 streams)
* Bad Bunny (1.70e+10 streams)
* Tyler (1.09e+10 streams)
* Melanie Martinez (1.06e+10 streams)
* Manuel Turizo (1.01e+10 streams)

**Top Chansons** : De même, les chansons les plus streamées ont été identifiées. Le top 5 est mené par :

 * I Ain't Worried (3.70e+09 streams, 71.3 popularité moyenne)
 * La Bachata (3.33e+09 streams, 60.9 popularité moyenne)
 * I Ain't Worried (1.98e+09 streams, 44.7 popularité moyenne - probablement une autre version ou un remix)
 * un x100to (1.30e+09 streams, 79.2 popularité moyenne)
 * Quiéreme Mientras Se Pueda (1.10e+09 streams, 52.9 popularité moyenne)



1.  **Analyse de Corrélation (Popularité vs. Streams) :**
    * **Métrique :** Le coefficient de corrélation de Pearson entre la popularité moyenne et la vélocité moyenne des streams par chanson a été calculé.
    * **Résultat :** Une corrélation positive faible à modérée (`r ≈ 0.39`) a été trouvée. 
    * **Validation :** Un test de significativité a retourné une **p-value extrêmement faible** (`~8.14e-280`), confirmant que cette corrélation est statistiquement significative et non due au hasard. 
    * **Conclusion :** Bien que les streams influencent la popularité, ils n'expliquent qu'une partie de sa variation (R² ≈ 15.4%), suggérant l'importance d'autres facteurs (playlists, viralité, etc.).

2.  **Analyse de la Distribution du Catalogue :**
    * Un histogramme de la distribution des streams totaux par chanson a été généré. 
    * **Conclusion :** La visualisation a mis en évidence une distribution de type **"longue traîne"**, typique de l'industrie musicale : une petite fraction de "méga-hits" concentre une part très importante des écoutes.

3.  **Analyse de la Saisonnalité :**
    * **Hypothèse testée :** "La saison de sortie d'une chanson a-t-elle un impact sur sa performance ?"
    * **Analyse 1 (Performance globale) :** Les chansons sorties au **Printemps et en Hiver** montrent une vélocité de streams moyenne légèrement supérieure sur l'ensemble de leur cycle de vie. 
    * **Analyse 2 (Impact au lancement) :** En analysant les streams accumulés 1 jour après la sortie, on observe que les lancements en **Été** ont un impact initial significativement plus fort. 
    * **Conclusion :** Cela suggère que l'été est une période propice pour un lancement "explosif", tandis que les chansons lancées à d'autres périodes peuvent avoir une performance plus durable.

4.  **Analyse de la Relation Catalogue/Popularité :**
    * **Hypothèse testée :** "Les artistes avec plus de chansons sont-ils en moyenne plus populaires ?"
    * **Conclusion :** L'analyse de corrélation n'a pas montré de relation statistiquement significative (`p > 0.05`), suggérant que la popularité d'un artiste n'est pas directement liée à la taille de son catalogue. 


 ### Étape 3 : Fonctions d'Enrichissement

Ces fonctions calculent des indicateurs de performance (KPIs) clés au niveau de la chanson ou de l'artiste.

* `all_songs_avrg_daily_streams()` : Calcule pour chaque chanson du catalogue sa vélocité moyenne de streams depuis sa sortie (`lifetime_average_daily_streams`) et sa popularité moyenne. 
* `song_avrg_daily_streams(song_id)` : Version paramétrée de la fonction précédente pour obtenir les KPIs d'une seule chanson. 
* `get_artist_stats(artist_name)` : Calcule des statistiques agrégées pour un artiste donné, incluant le total de ses streams (en additionnant les totaux de chacune de ses chansons), sa popularité moyenne et son nombre de titres. 
* `get_song_streams_evolution(song_id, start_date, end_date)` : Mesure la croissance d'une chanson sur une période définie, en retournant l'évolution absolue et en pourcentage du nombre de streams.
* `get_all_songs_kpis()` : Calcule pour chaque chanson du catalogue des statistiques de performance de base, notamment son total de streams cumulés (latest_total_streams) et sa popularité moyenne (average_popularity). C'est la fonction de base pour l'analyse descriptive.
* `get_streams_per_artist()` : Calcule le total des streams cumulés pour chaque artiste en agrégeant les totaux de toutes leurs chansons. Cette fonction est utilisée pour créer le classement des artistes.
  


### Conclusion Générale et Pistes d'Amélioration
Ce projet a permis de mettre en place un pipeline de données complet, de la modélisation à l'analyse avancée. Les résultats montrent qu'il est possible d'extraire des informations stratégiques (saisonnalité, profils de chansons) même à partir d'un jeu de données initialement brut et imparfait.

Le potentiel d'analyse pourrait être démultiplié en enrichissant ce jeu de données avec des informations externes. Les pistes d'amélioration futures incluent :

   * Données géographiques et linguistiques : L'ajout de la nationalité de l'artiste ou de la langue de la chanson permettrait de réaliser des analyses de marché très fines (par exemple, "Quelle est la performance des artistes français en dehors de la France ?").
   * Données multi-plateformes : Le jeu de données actuel est centré sur Spotify. L'intégration de données d'autres plateformes (Apple Music, Deezer, TikTok, YouTube) permettrait d'obtenir une vision de la performance d'un artiste et de comprendre les spécificités de chaque canal.
   * Données contextuelles : Le croisement des données de performance avec un calendrier d'événements (tournées, passages TV, campagnes marketing) permettrait de mesurer directement le rol de chaque action.
   * Données de la chanson : par example; la durée de la chanson, single ou fait partie d'un album.

Ces enrichissements transformeraient la base de données en un puissant outil d'aide à la décision stratégique pour Base for Music.

## Contenu de dépôt

Le dépôt contient plusieurs scripts et fonctions réutilisables, notamment :
* `script.py` : Script principal d'ETL qui crée le schéma et insère les données.
* `test.ipynb` : Un notebook contenant les fonctions realisées dans la partie technique (Analayse et enrichissement).
* `notebook_sous_forme_pdf.pdf` : Un fichier pdf qui contient les resultats de notebook test.ipynb .
* `ERD.png` et `RS.png` :  Deux images png qui contiennent le Entity Relationship Diagram et le Relational Schema.
* `representation_des_données.png` : Une image png qui présente la structure des données.
* `musique_db.backup` : la base de données crée sur pgAdmin4.
* `rendu_partie1.pdf` : Pdf qui contient un rapport de la partie 1 du teste.

Ce projet a été réalisé en **Python** avec les bibliothèques `pandas`, `numpy`, `psycopg2`, `scikit-learn`, `seaborn`, et `matplotlib`.
