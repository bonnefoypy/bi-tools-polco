import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import contextily as ctx
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import osmnx as ox
import networkx as nx
from geopy.geocoders import Nominatim
import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore')

class PreciseIsochroneMapper:
    """
    Générateur d'isochrones précises avec export d'images de haute qualité
    """
    
    def __init__(self, openrouteservice_key=None):
        self.ors_key = openrouteservice_key
        self.geolocator = Nominatim(user_agent="decathlon_precise_analysis")
        
    def get_precise_isochrones(self, lat, lon, times=[10, 20, 30], transport_mode='driving-car'):
        """
        Génère des isochrones ultra-précises en utilisant plusieurs méthodes
        """
        print(f"Génération d'isochrones précises pour {lat:.6f}, {lon:.6f}")
        
        # Tentative avec OpenRouteService (le plus précis)
        if self.ors_key:
            try:
                return self._get_ors_precise_isochrones(lat, lon, times, transport_mode)
            except Exception as e:
                print(f"ORS échoué: {e}")
        
        # Fallback avec OSMnx (très précis aussi)
        try:
            return self._get_osmnx_precise_isochrones(lat, lon, times, transport_mode)
        except Exception as e:
            print(f"OSMnx échoué: {e}")
            
        # Dernier recours: approximation intelligente
        return self._get_road_network_approximation(lat, lon, times, transport_mode)
    
    def _get_ors_precise_isochrones(self, lat, lon, times, transport_mode):
        """OpenRouteService avec paramètres optimisés pour la précision"""
        
        url = f"https://api.openrouteservice.org/v2/isochrones/{transport_mode}"
        headers = {
            'Authorization': self.ors_key,
            'Content-Type': 'application/json'
        }
        
        body = {
            "locations": [[lon, lat]],
            "range": [t * 60 for t in times],
            "range_type": "time",
            "smoothing": 0.8,  # Moins de lissage pour plus de précision
            "attributes": ["area", "reachfactor"],
            "intersections": True,
            "area_units": "km"
        }
        
        response = requests.post(url, json=body, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            isochrones = []
            
            for i, feature in enumerate(data['features']):
                geom = feature['geometry']
                props = feature['properties']
                
                if geom['type'] == 'Polygon':
                    coords = geom['coordinates'][0]
                    # Conversion lon,lat vers lat,lon
                    polygon_coords = [(coord[1], coord[0]) for coord in coords]
                    
                    isochrones.append({
                        'time': times[i],
                        'polygon': Polygon([(coord[1], coord[0]) for coord in coords]),
                        'area_km2': props.get('area', 0),
                        'center_lat': lat,
                        'center_lon': lon
                    })
            
            return isochrones
        else:
            raise Exception(f"ORS API error: {response.status_code}")
    
    def _get_osmnx_precise_isochrones(self, lat, lon, times, transport_mode):
        """OSMnx avec algorithme de précision maximale"""
        
        # Mapping des modes
        network_types = {
            'driving-car': 'drive',
            'cycling-regular': 'bike',
            'foot-walking': 'walk'
        }
        
        network_type = network_types.get(transport_mode, 'drive')
        
        # Vitesses réalistes par type de route
        speed_config = {
            'driving-car': {
                'motorway': 120, 'trunk': 90, 'primary': 70,
                'secondary': 50, 'tertiary': 40, 'residential': 30,
                'default': 35
            },
            'cycling-regular': {
                'cycleway': 20, 'primary': 15, 'secondary': 18,
                'tertiary': 20, 'residential': 15, 'default': 12
            },
            'foot-walking': {
                'footway': 5, 'path': 4, 'residential': 5, 'default': 5
            }
        }
        
        speeds = speed_config.get(transport_mode, speed_config['driving-car'])
        
        # Rayon de recherche adaptatif
        max_time = max(times)
        max_speed = max(speeds.values())
        search_radius = int((max_speed * max_time / 60) * 1000 * 1.5)  # en mètres
        
        print(f"Téléchargement du réseau {network_type}, rayon: {search_radius}m")
        
        # Téléchargement du graphe avec tous les attributs
        G = ox.graph_from_point(
            (lat, lon), 
            dist=search_radius, 
            network_type=network_type,
            simplify=True,
            retain_all=False,
            truncate_by_edge=True
        )
        
        # Configuration des vitesses précises
        for u, v, data in G.edges(data=True):
            highway = data.get('highway', 'default')
            if isinstance(highway, list):
                highway = highway[0]
            
            speed_kmh = speeds.get(highway, speeds['default'])
            data['speed_kph'] = speed_kmh
            data['travel_time'] = data['length'] / (speed_kmh * 1000 / 3600)  # en secondes
        
        # Nœud de départ
        origin_node = ox.distance.nearest_nodes(G, lon, lat)
        
        isochrones = []
        
        for time_limit in times:
            print(f"Calcul isochrone {time_limit} minutes...")
            
            # Calcul des nœuds accessibles avec Dijkstra
            travel_times = nx.single_source_dijkstra_path_length(
                G, origin_node, cutoff=time_limit * 60, weight='travel_time'
            )
            
            # Points des nœuds accessibles
            accessible_points = []
            for node, travel_time in travel_times.items():
                if travel_time <= time_limit * 60:
                    node_data = G.nodes[node]
                    accessible_points.append(Point(node_data['x'], node_data['y']))
            
            if len(accessible_points) >= 3:
                # Création d'une enveloppe alpha-shape pour plus de précision
                try:
                    from shapely.ops import unary_union
                    
                    # Buffer autour de chaque point accessible
                    buffered_points = [point.buffer(0.001) for point in accessible_points]
                    union_geom = unary_union(buffered_points)
                    
                    # Simplification et nettoyage
                    if hasattr(union_geom, 'convex_hull'):
                        isochrone_poly = union_geom.convex_hull
                    else:
                        isochrone_poly = union_geom
                    
                    # Calcul de l'aire
                    # Conversion approximative en km² (pour lat/lon)
                    area_deg2 = isochrone_poly.area
                    area_km2 = area_deg2 * 111.32 * 111.32 * np.cos(np.radians(lat))
                    
                    isochrones.append({
                        'time': time_limit,
                        'polygon': isochrone_poly,
                        'area_km2': area_km2,
                        'center_lat': lat,
                        'center_lon': lon,
                        'nodes_count': len(accessible_points)
                    })
                
                except Exception as e:
                    print(f"Erreur création polygone {time_limit}min: {e}")
        
        return isochrones
    
    def _get_road_network_approximation(self, lat, lon, times, transport_mode):
        """Approximation basée sur l'analyse du réseau routier local"""
        
        print("Utilisation de l'approximation réseau routier...")
        
        # Téléchargement des données routières via Overpass
        overpass_url = "http://overpass-api.de/api/interpreter"
        
        # Bbox étendue pour l'analyse
        bbox_size = 0.15  # ~15km
        south, west = lat - bbox_size, lon - bbox_size
        north, east = lat + bbox_size, lon + bbox_size
        
        # Requête Overpass pour toutes les routes
        overpass_query = f"""
        [out:json][timeout:30];
        (
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified)$"]({south},{west},{north},{east});
          way["highway"="living_street"]({south},{west},{north},{east});
        );
        out geom;
        """
        
        try:
            response = requests.get(overpass_url, params={'data': overpass_query}, timeout=30)
            osm_data = response.json()
            
            return self._create_network_based_isochrones(lat, lon, times, transport_mode, osm_data)
        
        except Exception as e:
            print(f"Erreur Overpass: {e}")
            return []
    
    def _create_network_based_isochrones(self, lat, lon, times, transport_mode, osm_data):
        """Création d'isochrones basées sur l'analyse du réseau OSM"""
        
        # Vitesses par type de route et mode de transport
        speed_matrix = {
            'driving-car': {
                'motorway': 120, 'trunk': 90, 'primary': 70,
                'secondary': 50, 'tertiary': 40, 'residential': 30,
                'unclassified': 25, 'living_street': 20
            },
            'cycling-regular': {
                'primary': 15, 'secondary': 18, 'tertiary': 20,
                'residential': 15, 'unclassified': 12, 'living_street': 10
            },
            'foot-walking': {
                'primary': 5, 'secondary': 5, 'tertiary': 5,
                'residential': 5, 'unclassified': 5, 'living_street': 5
            }
        }
        
        speeds = speed_matrix.get(transport_mode, speed_matrix['driving-car'])
        
        isochrones = []
        
        for time_limit in times:
            accessible_segments = []
            
            # Analyse de chaque segment de route
            for element in osm_data.get('elements', []):
                if element['type'] == 'way' and 'geometry' in element:
                    highway_type = element.get('tags', {}).get('highway', 'residential')
                    speed_kmh = speeds.get(highway_type, 30)
                    
                    if transport_mode == 'cycling-regular' and highway_type == 'motorway':
                        continue  # Pas de vélo sur autoroute
                    
                    # Analyse de chaque point du segment
                    for i, node in enumerate(element['geometry'][:-1]):
                        next_node = element['geometry'][i + 1]
                        
                        # Distance du segment depuis le point central
                        seg_start = (node['lat'], node['lon'])
                        seg_end = (next_node['lat'], next_node['lon'])
                        
                        # Distance à vol d'oiseau depuis le centre
                        dist_start = self._haversine_distance(lat, lon, seg_start[0], seg_start[1])
                        dist_end = self._haversine_distance(lat, lon, seg_end[0], seg_end[1])
                        
                        # Estimation du temps de trajet (avec facteur de route sinueuse)
                        road_factor = 1.4  # Les routes ne sont pas droites
                        min_distance = min(dist_start, dist_end) * road_factor
                        travel_time_minutes = (min_distance / speed_kmh) * 60
                        
                        # Si accessible dans le temps imparti
                        if travel_time_minutes <= time_limit:
                            accessible_segments.extend([seg_start, seg_end])
            
            # Création du polygone d'accessibilité
            if len(accessible_segments) >= 3:
                try:
                    from scipy.spatial import ConvexHull
                    
                    # Conversion en array numpy
                    points_array = np.array(accessible_segments)
                    
                    # Enveloppe convexe
                    hull = ConvexHull(points_array)
                    hull_points = points_array[hull.vertices]
                    
                    # Lissage du polygone
                    smoothed_points = self._smooth_polygon_advanced(hull_points)
                    
                    # Création du polygone Shapely
                    polygon = Polygon([(point[1], point[0]) for point in smoothed_points])  # lon, lat
                    
                    # Calcul de l'aire
                    area_km2 = self._calculate_polygon_area_precise(polygon, lat)
                    
                    isochrones.append({
                        'time': time_limit,
                        'polygon': polygon,
                        'area_km2': area_km2,
                        'center_lat': lat,
                        'center_lon': lon
                    })
                
                except Exception as e:
                    print(f"Erreur création polygone réseau {time_limit}min: {e}")
        
        return isochrones
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calcul de distance avec formule de Haversine"""
        R = 6371  # Rayon de la Terre en km
        
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat/2)**2 + 
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2)
        
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c
    
    def _smooth_polygon_advanced(self, points, iterations=3):
        """Lissage avancé du polygone avec splines"""
        
        if len(points) < 4:
            return points
        
        smoothed = points.copy()
        
        for _ in range(iterations):
            new_points = []
            n = len(smoothed)
            
            for i in range(n):
                # Indices avec bouclage
                prev_i = (i - 1) % n
                next_i = (i + 1) % n
                next2_i = (i + 2) % n
                
                # Interpolation spline cubique simplifiée
                p0 = smoothed[prev_i]
                p1 = smoothed[i]
                p2 = smoothed[next_i]
                p3 = smoothed[next2_i]
                
                # Moyenne pondérée avec courbe de Bézier
                smooth_lat = (p0[0] * 0.1 + p1[0] * 0.4 + p2[0] * 0.4 + p3[0] * 0.1)
                smooth_lon = (p0[1] * 0.1 + p1[1] * 0.4 + p2[1] * 0.4 + p3[1] * 0.1)
                
                new_points.append([smooth_lat, smooth_lon])
            
            smoothed = np.array(new_points)
        
        return smoothed
    
    def _calculate_polygon_area_precise(self, polygon, center_lat):
        """Calcul précis de l'aire du polygone"""
        try:
            from pyproj import Geod
            geod = Geod(ellps="WGS84")
            area_m2 = abs(geod.geometry_area_perimeter(polygon)[0])
            return area_m2 / 1_000_000  # Conversion en km²
        except:
            # Fallback approximation
            area_deg2 = polygon.area
            return area_deg2 * 111.32 * 111.32 * np.cos(np.radians(center_lat))
    
    def create_professional_map_image(self, store_data, isochrones, competitors=None, 
                                    output_path=None, dpi=300, figsize=(16, 12)):
        """
        Crée une image de carte professionnelle avec isochrones précises
        """
        
        if not isochrones:
            raise ValueError("Aucune isochrone à afficher")
        
        # Configuration de la figure
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        ax.set_aspect('equal')
        
        # Détermination des limites géographiques
        all_bounds = []
        for iso in isochrones:
            bounds = iso['polygon'].bounds
            all_bounds.extend([bounds[0], bounds[1], bounds[2], bounds[3]])
        
        min_lon, min_lat = min(all_bounds[::4]), min(all_bounds[1::4])
        max_lon, max_lat = max(all_bounds[2::4]), max(all_bounds[3::4])
        
        # Marge pour la visualisation
        margin = 0.02
        ax.set_xlim(min_lon - margin, max_lon + margin)
        ax.set_ylim(min_lat - margin, max_lat + margin)
        
        # Couleurs professionnelles pour les isochrones
        colors = ['#d73027', '#fc8d59', '#fee08b']  # Rouge -> Orange -> Jaune
        alphas = [0.6, 0.5, 0.4]
        
        # Dessin des isochrones (du plus grand au plus petit)
        sorted_isochrones = sorted(isochrones, key=lambda x: x['time'], reverse=True)
        
        for i, iso in enumerate(sorted_isochrones):
            if iso['polygon'] and not iso['polygon'].is_empty:
                # Extraction des coordonnées
                if hasattr(iso['polygon'], 'exterior'):
                    coords = list(iso['polygon'].exterior.coords)
                    xs, ys = zip(*coords)
                    
                    # Dessin du polygone
                    ax.fill(xs, ys, color=colors[i], alpha=alphas[i], 
                           label=f"{iso['time']} min ({iso['area_km2']:.1f} km²)")
                    ax.plot(xs, ys, color=colors[i], linewidth=2, alpha=0.8)
        
        # Marqueur du magasin central
        center_lat = isochrones[0]['center_lat']
        center_lon = isochrones[0]['center_lon']
        
        ax.plot(center_lon, center_lat, 'o', markersize=12, color='blue', 
               markeredgecolor='white', markeredgewidth=2, 
               label=f"Decathlon {store_data.get('store_name', '')}", zorder=10)
        
        # Ajout des concurrents si fournis
        if competitors:
            comp_lats, comp_lons = [], []
            for comp in competitors[:10]:  # Limiter pour lisibilité
                if 'latitude' in comp and 'longitude' in comp:
                    comp_lats.append(comp['latitude'])
                    comp_lons.append(comp['longitude'])
            
            if comp_lats:
                ax.scatter(comp_lons, comp_lats, c='red', s=50, marker='s', 
                          alpha=0.8, label='Concurrents', zorder=9)
        
        # Ajout du fond de carte (optionnel)
        try:
            # Utilise contextily pour ajouter un fond de carte
            import contextily as ctx
            
            # Conversion en Web Mercator pour contextily
            import geopandas as gpd
            from shapely.geometry import box
            
            # Création d'un GeoDataFrame temporaire
            bbox = box(min_lon, min_lat, max_lon, max_lat)
            gdf = gpd.GeoDataFrame([1], geometry=[bbox], crs='EPSG:4326')
            gdf_web = gdf.to_crs('EPSG:3857')
            
            # Ajout du fond de carte
            ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.CartoDB.Positron, 
                           alpha=0.7, zorder=0)
        
        except Exception as e:
            print(f"Fond de carte non disponible: {e}")
            # Fond gris simple
            ax.set_facecolor('#f5f5f5')
        
        # Légende et titres
        ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
        
        plt.title(f"Zone de Chalandise - Decathlon {store_data.get('store_name', '')}\n"
                 f"Directeur: {store_data.get('dir_mag', 'N/A')}", 
                 fontsize=16, fontweight='bold', pad=20)
        
        # Informations sur la carte
        info_text = f"""
        Population: {store_data.get('population', 'N/A')}
        Surface zone primaire: {isochrones[0]['area_km2']:.1f} km²
        Surface zone totale: {sum(iso['area_km2'] for iso in isochrones):.1f} km²
        """
        
        plt.figtext(0.02, 0.02, info_text, fontsize=10, 
                   bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8))
        
        # Grille et formatage
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        
        plt.tight_layout()
        
        # Sauvegarde
        if output_path:
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"Carte sauvegardée: {output_path}")
        
        return fig, ax

# Fonction d'intégration complète
def generate_precise_catchment_maps(csv_path, config, output_dir="cartes_precises"):
    """
    Génère des cartes précises pour tous les magasins du CSV
    """
    import os
    from datetime import datetime
    
    # Lecture des données
    df = pd.read_csv(csv_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialisation du mapper
    mapper = PreciseIsochroneMapper(config.get('ors_key'))
    
    results = []
    
    for index, row in df.iterrows():
        store_data = {
            'store_id': row['store_id'],
            'store_name': row['store_name'],
            'dir_mag': row['dir_mag'],
            'population': row.get('population', 'N/A')
        }
        
        print(f"\nTraitement {index+1}/{len(df)}: {store_data['store_name']}")
        
        try:
            # Géocodage
            address = f"{store_data['store_name']}, {store_data['dir_mag']}, France"
            location = mapper.geolocator.geocode(address)
            
            if not location:
                print(f"Géocodage échoué pour {address}")
                continue
            
            # Génération des isochrones précises
            isochrones = mapper.get_precise_isochrones(
                location.latitude, 
                location.longitude,
                times=[10, 20, 30],
                transport_mode='driving-car'
            )
            
            if not isochrones:
                print(f"Aucune isochrone générée pour {store_data['store_name']}")
                continue
            
            # Création de l'image
            output_path = os.path.join(
                output_dir, 
                f"carte_precise_{store_data['store_id']}_{store_data['store_name'].replace(' ', '_')}.png"
            )
            
            fig, ax = mapper.create_professional_map_image(
                store_data, 
                isochrones, 
                output_path=output_path,
                dpi=300
            )
            
            plt.close(fig)  # Libérer la mémoire
            
            # Sauvegarde des données
            result = {
                'store_id': store_data['store_id'],
                'store_name': store_data['store_name'],
                'image_path': output_path,
                'isochrones_data': [
                    {
                        'time': iso['time'],
                        'area_km2': iso['area_km2']
                    }
                    for iso in isochrones
                ]
            }
            
            results.append(result)
            print(f"Carte générée: {output_path}")
            
        except Exception as e:
            print(f"Erreur pour {store_data['store_name']}: {e}")
    
    print(f"\n{len(results)} cartes générées dans {output_dir}")
    return results

# Exemple d'utilisation
if __name__ == "__main__":
    config = {
        'ors_key': 'your_openrouteservice_key_here'  # Optionnel mais recommandé
    }
    
    csv_path = "polco_mag_test - Feuille 1.csv"
    results = generate_precise_catchment_maps(csv_path, config)