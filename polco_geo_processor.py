#!/usr/bin/env python3
"""
POLCO GEO-PROCESSOR - Visualisations Cartographiques Génériques
Génère des cartes PNG basées sur les données de captation Firestore
Analyse automatiquement les résultats de captation pour créer des cartes adaptées
"""

import os
import re
import json
import folium
import requests
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from typing import Dict, List, Optional
import logging
from datetime import datetime
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel
import warnings
warnings.filterwarnings('ignore')

# Imports pour isochrones réalistes
try:
    import osmnx as ox
    import networkx as nx
    from shapely.geometry import Point, Polygon, MultiPoint
    from shapely.ops import unary_union
    import geopandas as gpd
    from pyproj import Geod
    HAS_REALISTIC_LIBS = True
except ImportError:
    HAS_REALISTIC_LIBS = False
    print("⚠️ Bibliothèques pour isochrones réalistes non disponibles. Utilisation du mode approximation.")

# Imports pour génération d'images
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    
try:
    import playwright
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

if not HAS_SELENIUM and not HAS_PLAYWRIGHT:
    print("⚠️ Ni selenium ni playwright disponible. Utilisation du générateur de cartes statiques.")

# Import du générateur de cartes statiques
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️ Matplotlib non disponible. Les cartes seront sauvées en HTML uniquement.")

# Import du générateur d'isochrones avancé
try:
    from isochrone_enhanced import PreciseIsochroneMapper
    HAS_PRECISE_ISOCHRONES = True
    print("✅ Générateur d'isochrones précises disponible")
except ImportError:
    HAS_PRECISE_ISOCHRONES = False
    print("⚠️ isochrone_enhanced.py non disponible. Utilisation des méthodes basiques.")

# Configuration
PROJECT_ID = "polcoaigeneration-ved6"
REGION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"
CAPTATION_COLLECTION = "polco_magasins_captation"

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polco_geo_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RealisticIsochroneGenerator:
    """Générateur d'isochrones basé sur le réseau routier réel"""
    
    def __init__(self, openrouteservice_key=None, here_api_key=None):
        self.ors_key = openrouteservice_key
        self.here_key = here_api_key
        
    def get_real_isochrones(self, lat, lon, times=[10, 20, 30], transport_mode='car'):
        """Génère des isochrones réelles basées sur le réseau routier"""
        methods = [
            self._get_ors_isochrones,
            self._get_here_isochrones, 
            self._get_osmnx_isochrones,
            self._get_smart_approximation
        ]
        
        for method in methods:
            try:
                result = method(lat, lon, times, transport_mode)
                if result and len(result) > 0:
                    logger.info(f"Isochrones générées avec: {method.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"Échec {method.__name__}: {e}")
                continue
        
        raise Exception("Impossible de générer des isochrones avec tous les services")
    
    def _get_ors_isochrones(self, lat, lon, times, transport_mode):
        """OpenRouteService - Service gratuit avec limite"""
        if not self.ors_key:
            return None
            
        ors_profiles = {
            'car': 'driving-car',
            'bike': 'cycling-regular', 
            'walk': 'foot-walking'
        }
        
        profile = ors_profiles.get(transport_mode, 'driving-car')
        url = f"https://api.openrouteservice.org/v2/isochrones/{profile}"
        
        headers = {
            'Authorization': self.ors_key,
            'Content-Type': 'application/json'
        }
        
        body = {
            "locations": [[lon, lat]],
            "range": [t * 60 for t in times],
            "range_type": "time",
            "smoothing": 10
        }
        
        response = requests.post(url, json=body, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            isochrones = []
            
            for i, feature in enumerate(data['features']):
                coords = feature['geometry']['coordinates'][0]
                folium_coords = [[coord[1], coord[0]] for coord in coords]
                
                isochrones.append({
                    'time': times[i],
                    'coordinates': folium_coords,
                    'area_km2': self._calculate_polygon_area(folium_coords),
                    'method': 'openrouteservice'
                })
            
            return isochrones
        
        return None
    
    def _get_here_isochrones(self, lat, lon, times, transport_mode):
        """HERE Maps Isochrone API"""
        if not self.here_key:
            return None
            
        here_modes = {
            'car': 'car',
            'bike': 'bicycle',
            'walk': 'pedestrian'
        }
        
        mode = here_modes.get(transport_mode, 'car')
        url = "https://isoline.route.ls.hereapi.com/routing/7.2/calculateisoline.json"
        
        isochrones = []
        
        for time_min in times:
            params = {
                'apikey': self.here_key,
                'start': f'geo!{lat},{lon}',
                'mode': f'fastest;{mode}',
                'range': str(time_min * 60),
                'rangetype': 'time'
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'response' in data and 'isoline' in data['response']:
                    shape = data['response']['isoline'][0]['component'][0]['shape']
                    
                    coords = []
                    for i in range(0, len(shape), 2):
                        lat_point = float(shape[i])
                        lon_point = float(shape[i + 1])
                        coords.append([lat_point, lon_point])
                    
                    isochrones.append({
                        'time': time_min,
                        'coordinates': coords,
                        'area_km2': self._calculate_polygon_area(coords),
                        'method': 'here_maps'
                    })
        
        return isochrones if isochrones else None
    
    def _get_osmnx_isochrones(self, lat, lon, times, transport_mode):
        """Utilise OSMnx pour calculer des isochrones sur le réseau OpenStreetMap"""
        if not HAS_REALISTIC_LIBS:
            return None
            
        try:
            network_types = {
                'car': 'drive',
                'bike': 'bike', 
                'walk': 'walk'
            }
            
            network_type = network_types.get(transport_mode, 'drive')
            
            speeds = {
                'car': 40,
                'bike': 15,
                'walk': 5
            }
            
            speed_kmh = speeds[transport_mode]
            
            max_time = max(times)
            search_radius = (speed_kmh * max_time / 60) * 1000 * 1.5
            
            logger.info(f"Téléchargement du réseau {network_type} autour de {lat}, {lon}...")
            G = ox.graph_from_point((lat, lon), dist=search_radius, network_type=network_type)
            
            origin_node = ox.distance.nearest_nodes(G, lon, lat)
            
            G = ox.add_edge_speeds(G)
            G = ox.add_edge_travel_times(G)
            
            for u, v, data in G.edges(data=True):
                if transport_mode == 'car':
                    data['speed_kph'] = min(data.get('speed_kph', speed_kmh), speed_kmh)
                else:
                    data['speed_kph'] = speed_kmh
                    
                data['travel_time'] = data['length'] / (data['speed_kph'] * 1000 / 3600)
            
            isochrones = []
            
            for time_limit in times:
                subgraph = nx.ego_graph(G, origin_node, radius=time_limit*60, distance='travel_time')
                
                node_points = []
                for node in subgraph.nodes():
                    node_data = G.nodes[node]
                    node_points.append(Point(node_data['x'], node_data['y']))
                
                if len(node_points) >= 3:
                    multipoint = MultiPoint(node_points)
                    hull = multipoint.convex_hull
                    expanded = hull.buffer(0.001)
                    
                    if hasattr(expanded, 'exterior'):
                        coords = [[y, x] for x, y in expanded.exterior.coords]
                        
                        isochrones.append({
                            'time': time_limit,
                            'coordinates': coords,
                            'area_km2': self._calculate_polygon_area(coords),
                            'nodes_count': len(node_points),
                            'method': 'osmnx'
                        })
            
            return isochrones if isochrones else None
            
        except Exception as e:
            logger.warning(f"Erreur OSMnx: {e}")
            return None
    
    def _get_smart_approximation(self, lat, lon, times, transport_mode):
        """Approximation intelligente tenant compte des contraintes géographiques"""
        logger.info("Utilisation de l'approximation intelligente...")
        
        params = {
            'car': {
                'base_speed': 35,
                'highway_factor': 1.4,
                'urban_factor': 0.6,
                'directions': {
                    0: 1.2, 45: 0.9, 90: 1.1, 135: 0.9,
                    180: 1.2, 225: 0.8, 270: 1.1, 315: 0.8
                }
            },
            'bike': {
                'base_speed': 16,
                'highway_factor': 0.8,
                'urban_factor': 1.0,
                'directions': {d: 1.0 for d in [0, 45, 90, 135, 180, 225, 270, 315]}
            },
            'walk': {
                'base_speed': 5,
                'highway_factor': 1.0,
                'urban_factor': 1.0,
                'directions': {d: 1.0 for d in [0, 45, 90, 135, 180, 225, 270, 315]}
            }
        }
        
        mode_params = params.get(transport_mode, params['car'])
        base_speed = mode_params['base_speed']
        directions = mode_params['directions']
        
        isochrones = []
        
        for time_minutes in times:
            base_distance = (base_speed * time_minutes) / 60
            
            points = []
            
            for bearing in range(0, 360, 5):
                dir_factor = self._interpolate_direction_factor(bearing, directions)
                adjusted_distance = base_distance * dir_factor
                local_variation = np.random.uniform(0.85, 1.15)
                final_distance = adjusted_distance * local_variation
                
                point = geodesic(kilometers=final_distance).destination((lat, lon), bearing)
                points.append([point.latitude, point.longitude])
            
            smoothed_points = self._smooth_isochrone_shape(points)
            
            isochrones.append({
                'time': time_minutes,
                'coordinates': smoothed_points,
                'area_km2': self._calculate_polygon_area(smoothed_points),
                'method': 'smart_approximation'
            })
        
        return isochrones
    
    def _interpolate_direction_factor(self, bearing, direction_factors):
        """Interpolation des facteurs directionnels"""
        directions = sorted(direction_factors.keys())
        
        for i, dir_angle in enumerate(directions):
            if bearing <= dir_angle:
                if i == 0:
                    prev_dir = directions[-1] - 360
                    next_dir = dir_angle
                else:
                    prev_dir = directions[i-1]
                    next_dir = dir_angle
                break
        else:
            prev_dir = directions[-1]
            next_dir = directions[0] + 360
        
        if bearing < prev_dir:
            bearing += 360
            
        weight = (bearing - prev_dir) / (next_dir - prev_dir)
        prev_factor = direction_factors.get(prev_dir % 360, 1.0)
        next_factor = direction_factors.get(next_dir % 360, 1.0)
        
        return prev_factor * (1 - weight) + next_factor * weight
    
    def _smooth_isochrone_shape(self, points, iterations=2):
        """Lisse la forme de l'isochrone pour un aspect plus naturel"""
        smoothed = points[:]
        
        for _ in range(iterations):
            new_points = []
            for i in range(len(smoothed)):
                prev_idx = (i - 1) % len(smoothed)
                next_idx = (i + 1) % len(smoothed)
                
                current = smoothed[i]
                prev_point = smoothed[prev_idx]
                next_point = smoothed[next_idx]
                
                smooth_lat = (prev_point[0] * 0.25 + current[0] * 0.5 + next_point[0] * 0.25)
                smooth_lon = (prev_point[1] * 0.25 + current[1] * 0.5 + next_point[1] * 0.25)
                
                new_points.append([smooth_lat, smooth_lon])
            
            smoothed = new_points
        
        return smoothed
    
    def _calculate_polygon_area(self, coordinates):
        """Calcule l'aire d'un polygone en km²"""
        try:
            if HAS_REALISTIC_LIBS and len(coordinates) >= 3:
                poly = Polygon([(coord[1], coord[0]) for coord in coordinates])
                geod = Geod(ellps="WGS84")
                area_m2 = abs(geod.geometry_area_perimeter(poly)[0])
                return area_m2 / 1_000_000
        except:
            pass
        return 0.0
    
    def validate_isochrones(self, isochrones, center_lat, center_lon):
        """Valide que les isochrones sont cohérentes et réalistes"""
        validated = []
        
        for iso in isochrones:
            coords = iso['coordinates']
            time_min = iso['time']
            
            if len(coords) < 3:
                continue
            
            max_distance = 0
            for coord in coords:
                dist = geodesic((center_lat, center_lon), (coord[0], coord[1])).kilometers
                max_distance = max(max_distance, dist)
            
            max_realistic_distance = {
                5: 8, 10: 15, 15: 22, 20: 25, 30: 40
            }
            
            if max_distance <= max_realistic_distance.get(time_min, 50):
                validated.append(iso)
            else:
                logger.warning(f"Isochrone {time_min}min rejetée: distance {max_distance:.1f}km trop élevée")
        
        return validated


class PolcoGeoProcessor:
    """Processeur de géolocalisation et cartographie générique pour POLCO 3.0."""
    
    def __init__(self):
        """Initialise le processeur géographique générique."""
        self.project_id = PROJECT_ID
        self.captation_collection = CAPTATION_COLLECTION
        self.db = None
        self.model = None
        self.output_dir = "analytics_charts"
        self.maps_output_dir = "geo_maps"
        self.geolocator = Nominatim(user_agent="polco_decathlon_analysis")
        
        # Générateur d'isochrones réalistes
        self.isochrone_generator = RealisticIsochroneGenerator(
            openrouteservice_key=os.getenv('OPENROUTESERVICE_KEY'),
            here_api_key=os.getenv('HERE_API_KEY')
        )
        
        # Générateur d'isochrones précises (nouvelle version)
        if HAS_PRECISE_ISOCHRONES:
            self.precise_isochrone_mapper = PreciseIsochroneMapper(
                openrouteservice_key=os.getenv('OPENROUTESERVICE_KEY')
            )
        else:
            self.precise_isochrone_mapper = None
        
        # Créer les dossiers de sortie
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.maps_output_dir, exist_ok=True)
        
        logger.info("🗺️ Initialisation POLCO GEO-PROCESSOR Générique avec isochrones réalistes")
    
    def convert_html_to_image(self, html_path: str, output_format: str = 'png') -> str:
        """Convertit une carte HTML en image PNG/JPG."""
        if not os.path.exists(html_path):
            logger.error(f"❌ Fichier HTML non trouvé: {html_path}")
            return ""
        
        base_name = os.path.splitext(html_path)[0]
        image_path = f"{base_name}.{output_format}"
        
        # Tentative avec Playwright (plus récent et fiable)
        if HAS_PLAYWRIGHT:
            try:
                return self._convert_with_playwright(html_path, image_path)
            except Exception as e:
                logger.warning(f"⚠️ Échec Playwright: {e}")
        
        # Tentative avec Selenium (fallback)
        if HAS_SELENIUM:
            try:
                return self._convert_with_selenium(html_path, image_path)
            except Exception as e:
                logger.warning(f"⚠️ Échec Selenium: {e}")
        
        logger.error("❌ Impossible de convertir en image. HTML conservé.")
        return html_path
    
    def _convert_with_playwright(self, html_path: str, image_path: str) -> str:
        """Conversion avec Playwright."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1200, 'height': 800})
            
            # Charger la carte HTML
            page.goto(f"file://{os.path.abspath(html_path)}")
            
            # Attendre que la carte soit complètement chargée
            page.wait_for_timeout(3000)  # 3 secondes
            
            # Prendre une capture d'écran
            page.screenshot(path=image_path, full_page=True)
            browser.close()
            
            logger.info(f"✅ Image générée avec Playwright: {image_path}")
            return image_path
    
    def _convert_with_selenium(self, html_path: str, image_path: str) -> str:
        """Conversion avec Selenium."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1200,800")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Charger la carte HTML
            driver.get(f"file://{os.path.abspath(html_path)}")
            
            # Attendre que la carte soit chargée
            time.sleep(3)
            
            # Prendre une capture d'écran
            driver.save_screenshot(image_path)
            
            logger.info(f"✅ Image générée avec Selenium: {image_path}")
            return image_path
            
        finally:
            driver.quit()
    
    def save_map_as_image(self, folium_map, store_id: str, map_type: str) -> str:
        """Sauve une carte Folium directement en image."""
        # D'abord sauver en HTML
        html_path = f"{self.maps_output_dir}/{map_type}_map_{store_id}.html"
        folium_map.save(html_path)
        
        # Puis convertir en image
        image_path = self.convert_html_to_image(html_path, 'png')
        
        # Optionnel: supprimer le fichier HTML temporaire
        # os.remove(html_path)
        
        return image_path
    
    def init_vertex_ai(self) -> bool:
        """Initialise Vertex AI."""
        try:
            vertexai.init(project=PROJECT_ID, location=REGION)
            self.model = GenerativeModel(MODEL_NAME)
            logger.info(f"✅ Vertex AI initialisé ({MODEL_NAME})")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur Vertex AI: {e}")
            return False
    
    def get_captation_content(self, store_id: str) -> str:
        """Récupère le contenu complet de captation depuis Firestore."""
        try:
            doc_ref = self.db.collection(self.captation_collection).document(f"store_{store_id}")
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.error(f"❌ Données de captation non trouvées pour le magasin {store_id}")
                return ""
            
            captation_data = doc.to_dict()
            
            # Fusionner tous les résultats de captation
            captation_content = "=== RÉSULTATS DE CAPTATION GÉOGRAPHIQUE ===\n\n"
            prompts_results = captation_data.get('prompts_results', {})
            
            for key, value in prompts_results.items():
                if isinstance(value, dict) and 'response' in value:
                    captation_content += f"--- {key.upper()} ---\n{value['response']}\n\n"
                elif isinstance(value, dict) and 'result' in value:
                    captation_content += f"--- {key.upper()} ---\n{value['result']}\n\n"
            
            logger.info(f"✅ Contenu de captation récupéré pour le magasin {store_id}")
            return captation_content
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération captation: {e}")
            return ""
    
    def extract_captation_data(self, store_id: str) -> Optional[Dict]:
        """Extrait et structure les données de captation via LLM."""
        try:
            # Récupérer le contenu brut de captation
            captation_content = self.get_captation_content(store_id)
            if not captation_content:
                return None
            
            # Utiliser le LLM pour structurer les données géographiques
            structured_data = self._structure_geographic_data_with_llm(captation_content, store_id)
            if not structured_data:
                return None
            
            logger.info(f"✅ Données géographiques structurées pour le magasin {store_id}")
            return structured_data
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction données captation: {e}")
            return None
    
    def _structure_geographic_data_with_llm(self, captation_content: str, store_id: str) -> Optional[Dict]:
        """Utilise le LLM pour structurer les données géographiques."""
        try:
            # Détecter le pays et la langue du magasin
            country, language = self.detect_country_and_language(store_id)
            
            prompt = f"""
Tu es un analyste géographique expert. À partir des données de captation ci-dessous, extrais et structure les informations géographiques importantes pour générer des visualisations cartographiques.

🌍 **LOCALISATION ET ACTUALITÉ OBLIGATOIRES:**
- Pays détecté: {country}
- Langue de traitement: {language}
- VÉRIFICATION D'ACTUALITÉ: Priorise uniquement les informations qui semblent actuelles et vérifiées (2024-2025)
- SIGNALER: Marque comme "status": "à_vérifier" tout concurrent ou infrastructure dont le statut d'activité est incertain

🕐 **CONTRÔLE QUALITÉ ACTUALITÉ:**
- Concurrents: Ne retenir que ceux explicitement mentionnés comme OUVERTS/ACTIFS
- Infrastructures: Privilégier celles confirmées comme ACCESSIBLES/OUVERTES
- Événements: Uniquement ceux avec dates 2024-2025 ou récurrence confirmée
- Si incertitude sur l'activité: ajouter "status": "à_vérifier" dans l'objet

DONNÉES DE CAPTATION:
{captation_content}

Tâche: Analyse ces données et retourne un JSON structuré avec les informations suivantes:

1. **store_info**: Informations sur le magasin Decathlon
   - name: nom exact du magasin
   - address: adresse complète
   - city: ville
   - country: "{country}"
   - language: "{language}"
   - surface: surface en m² (si mentionnée)
   - latitude/longitude: coordonnées GPS (si mentionnées)

2. **competitors**: Liste des concurrents identifiés ET VÉRIFIÉS ACTIFS
   Pour chaque concurrent:
   - name: nom exact
   - distance_km: distance en kilomètres (convertir si nécessaire)
   - type: catégorie ("Généraliste Sport", "Sneakers/Mode", "Spécialiste Vélo", "Spécialiste Fitness", "Autre")
   - address: adresse (si mentionnée)
   - status: "actif" ou "à_vérifier" (selon les indices d'activité dans le texte)

3. **demographics**: Données démographiques RÉCENTES de la zone
   - population: nombre d'habitants (données les plus récentes)
   - median_income: revenu médian (si mentionné)
   - unemployment_rate: taux de chômage (si mentionné)
   - growth_rate: taux de croissance (si mentionné)
   - data_year: année des données (si mentionnée)

4. **sports_infrastructure**: Infrastructures sportives ACCESSIBLES
   Pour chaque infrastructure:
   - name: nom exact
   - type: catégorie ("Stade", "Piscine", "Fitness", "Athlétisme", "Autre")
   - capacity: capacité (si mentionnée)
   - address: adresse (si mentionnée)
   - status: "ouvert" ou "à_vérifier" (selon les indices d'ouverture dans le texte)

5. **tourism**: Données touristiques ACTUELLES
   - annual_visitors: nombre de visiteurs annuels (données récentes)
   - main_attractions: principales attractions (liste)
   - data_year: année des données (si mentionnée)

6. **mobility**: Données de mobilité ACTUELLES
   - bike_lanes_km: kilomètres de pistes cyclables (si mentionné)
   - transport_lines: lignes de transport en commun importantes
   - last_update: dernière mise à jour des données (si mentionnée)

EXIGENCES RENFORCÉES:
- Convertis toutes les distances en kilomètres (ex: "640m" → 0.64)
- Nettoie les noms (supprime les caractères spéciaux inutiles)
- Catégorise intelligemment les concurrents et infrastructures
- PRIORISE les données avec indices temporels récents (2023-2025)
- EXCLUS les données manifestement périmées (fermetures mentionnées, dates anciennes)
- Ajoute "status" pour indiquer le niveau de confiance sur l'activité
- Extrais uniquement les données factuelles mentionnées dans le texte
- Si une information n'est pas disponible, ne l'inclus pas
- Retourne uniquement le JSON, sans texte d'explication
- **PRÉFÉRER LES STRUCTURES TABULAIRES** dans le JSON pour une meilleure lisibilité
- Organiser les données en tableaux structurés plutôt qu'en listes complexes

JSON de sortie:
"""
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Nettoyer la réponse pour extraire le JSON
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Parser le JSON
            structured_data = json.loads(response_text)
            
            logger.info(f"✅ Données structurées par LLM pour magasin {store_id}")
            logger.info(f"📊 Résumé: {len(structured_data.get('competitors', []))} concurrents, {len(structured_data.get('sports_infrastructure', []))} infrastructures")
            
            return structured_data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON: {e}")
            logger.error(f"Réponse LLM: {response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur structuration LLM: {e}")
            return None
    
    def _parse_store_zone_data(self, content: str) -> Dict:
        """Parse les informations sur le magasin et sa zone."""
        store_info = {}
        
        # Rechercher les informations du magasin
        store_patterns = {
            'name': r'\*\*Nom :\*\* (.+)',
            'address': r'\*\*Adresse :\*\* (.+)',
            'coordinates': r'Latitude : ([\d.]+), Longitude : ([\d.]+)',
            'surface': r'(\d+) ?m²'
        }
        
        for key, pattern in store_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if key == 'coordinates':
                    store_info['latitude'] = float(match.group(1))
                    store_info['longitude'] = float(match.group(2))
                elif key == 'surface':
                    store_info['surface'] = int(match.group(1))
                else:
                    store_info[key] = match.group(1).strip()
        
        return store_info
    
    def _parse_competitors_data(self, content: str) -> List[Dict]:
        """Parse les données des concurrents."""
        competitors = []
        
        # Rechercher les concurrents avec pattern flexible
        competitor_patterns = [
            r'\*\*([^\*]+)\*\* ?: ?([^,\n]+)[,\n].*?[Dd]istance[^\d]*([\d,\.]*)\s*([km])',
            r'([A-Z][^\n]*Sport[^\n]*) ?[:-] ?([^\n]+distance[^\d]*([\d,\.]*)\s*([km]))',
            r'([A-Z][A-Za-z\s&]+) \([^\)]*([\\d,\.]+)\s*([km])\)'
        ]
        
        for pattern in competitor_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    name = match.group(1).strip()
                    distance_str = match.group(3) if len(match.groups()) > 2 else '0'
                    distance = float(distance_str.replace(',', '.')) if distance_str else 0
                    
                    if name and len(name) > 2 and distance > 0:
                        competitors.append({
                            'name': name,
                            'distance_km': distance,
                            'type': self._categorize_competitor(name)
                        })
                except (ValueError, IndexError):
                    continue
        
        return competitors
    
    def _parse_demographics_data(self, content: str) -> Dict:
        """Parse les données démographiques."""
        demographics = {}
        
        # Population et revenus
        population_match = re.search(r'Population[^\d]*(\d[\d\s,]+)', content, re.IGNORECASE)
        if population_match:
            demographics['population'] = int(population_match.group(1).replace(' ', '').replace(',', ''))
        
        income_match = re.search(r'[Rr]evenu.*?([\d\s,]+)\s*€', content)
        if income_match:
            demographics['median_income'] = int(income_match.group(1).replace(' ', '').replace(',', ''))
        
        return demographics
    
    def _parse_infrastructure_data(self, content: str) -> List[Dict]:
        """Parse les infrastructures sportives."""
        infrastructures = []
        
        # Rechercher stades, piscines, etc.
        infra_patterns = [
            r'\*\*([^\*]+(?:[Ss]tade|[Pp]iscine|[Gg]ym|[Cc]omplexe)[^\*]*)\*\*[^\n]*([^\n]+)',
            r'([A-Z][^\n]*(?:Stade|Piscine|Gym|Complexe)[^\n]*)[^\d]*(\d+[^\n]*)',
        ]
        
        for pattern in infra_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                details = match.group(2) if len(match.groups()) > 1 else ''
                
                if name and len(name) > 5:
                    infrastructures.append({
                        'name': name,
                        'details': details,
                        'type': self._categorize_infrastructure(name)
                    })
        
        return infrastructures
    
    def _parse_swot_data(self, content: str) -> Dict:
        """Parse l'analyse SWOT."""
        return {'swot_analysis': content[:500] + '...' if len(content) > 500 else content}
    
    def _parse_tourism_data(self, content: str) -> Dict:
        """Parse les données touristiques."""
        tourism = {}
        
        # Rechercher les chiffres de fréquentation
        visitor_patterns = [
            r'([\d\s,]+)\s*(?:visiteurs|nuitées|touristes)',
            r'([\d\s,]+)\s*(?:entrées|passages)'
        ]
        
        for pattern in visitor_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    visitors = int(match.group(1).replace(' ', '').replace(',', ''))
                    tourism['annual_visitors'] = visitors
                    break
                except ValueError:
                    continue
        
        return tourism
    
    def _parse_detailed_competitors(self, content: str) -> List[Dict]:
        """Parse la concurrence détaillée."""
        competitors = []
        
        # Tableau de concurrents
        table_pattern = r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
        matches = re.finditer(table_pattern, content)
        
        for match in matches:
            enseigne = match.group(1).strip()
            adresse = match.group(2).strip()
            distance = match.group(3).strip()
            
            if enseigne and enseigne not in ['Enseigne', ':---'] and len(enseigne) > 2:
                distance_num = re.search(r'([\d,\.]+)', distance)
                if distance_num:
                    competitors.append({
                        'name': enseigne,
                        'address': adresse,
                        'distance_km': float(distance_num.group(1).replace(',', '.')),
                        'type': self._categorize_competitor(enseigne)
                    })
        
        return competitors
    
    def _parse_mobility_data(self, content: str) -> Dict:
        """Parse les données de mobilité."""
        mobility = {}
        
        # Rechercher les km de pistes cyclables
        bike_pattern = r'([\d,\.]+)\s*km.*?(?:pistes?|cyclables?)'
        match = re.search(bike_pattern, content, re.IGNORECASE)
        if match:
            mobility['bike_lanes_km'] = float(match.group(1).replace(',', '.'))
        
        return mobility
    
    def _categorize_competitor(self, name: str) -> str:
        """Catégorise un concurrent selon son nom."""
        name_lower = name.lower()
        
        if any(x in name_lower for x in ['decathlon', 'intersport', 'go sport', 'sport 2000']):
            return 'Généraliste Sport'
        elif any(x in name_lower for x in ['nike', 'adidas', 'courir', 'jd sports', 'foot locker']):
            return 'Sneakers/Mode'
        elif any(x in name_lower for x in ['vélo', 'bike', 'cycle']):
            return 'Spécialiste Vélo'
        elif any(x in name_lower for x in ['tennis', 'fitness', 'gym', 'basic-fit']):
            return 'Spécialiste Fitness'
        else:
            return 'Autre'
    
    def _categorize_infrastructure(self, name: str) -> str:
        """Catégorise une infrastructure sportive."""
        name_lower = name.lower()
        
        if any(x in name_lower for x in ['stade', 'football', 'rugby']):
            return 'Stade'
        elif any(x in name_lower for x in ['piscine', 'natation', 'aqua']):
            return 'Piscine'
        elif any(x in name_lower for x in ['gym', 'fitness', 'musculation']):
            return 'Fitness'
        elif any(x in name_lower for x in ['athlétisme', 'piste', 'anneau']):
            return 'Athlétisme'
        else:
            return 'Autre'
    
    def geocode_address(self, address: str) -> tuple:
        """Géocode une adresse pour obtenir lat/lon."""
        # Essayer plusieurs variantes d'adresse
        addresses_to_try = [
            address,
            address.replace("Zone Actisud -", "").strip(),
            f"Decathlon {address}",
            f"{address}, France",
            "Decathlon Metz Augny, France",
            "Rue des Gravières, Augny, France"
        ]
        
        for addr in addresses_to_try:
            try:
                location = self.geolocator.geocode(addr, timeout=10)
                if location:
                    logger.info(f"✅ Géocodage réussi avec: {addr} -> {location.latitude:.4f}, {location.longitude:.4f}")
                    return location.latitude, location.longitude
            except Exception as e:
                logger.debug(f"Échec géocodage {addr}: {e}")
                continue
        
        logger.warning(f"❌ Impossible de géocoder: {address}")
        return None, None

    def detect_country_and_language(self, store_name: str) -> tuple:
        """Détecte le pays et la langue à partir du nom du magasin."""
        # Dictionnaire des villes connues par pays
        country_cities = {
            'France': ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes', 'Montpellier', 'Strasbourg', 'Bordeaux', 'Lille', 'Rennes', 'Reims', 'Le Havre', 'Saint-Étienne', 'Toulon', 'Grenoble', 'Dijon', 'Angers', 'Villeurbanne', 'Le Mans', 'Aix-en-Provence', 'Clermont-Ferrand', 'Brest', 'Tours', 'Limoges', 'Amiens', 'Annecy', 'Perpignan', 'Boulogne-Billancourt', 'Metz', 'Augny'],
            'Germany': ['Berlin', 'Hamburg', 'München', 'Köln', 'Frankfurt', 'Stuttgart', 'Düsseldorf', 'Leipzig', 'Dortmund', 'Essen', 'Bremen', 'Dresden', 'Hannover', 'Nürnberg'],
            'Spain': ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Zaragoza', 'Málaga', 'Murcia', 'Palma', 'Las Palmas', 'Bilbao'],
            'Italy': ['Roma', 'Milano', 'Napoli', 'Torino', 'Palermo', 'Genova', 'Bologna', 'Firenze', 'Bari', 'Catania'],
            'Belgium': ['Brussels', 'Antwerp', 'Gent', 'Charleroi', 'Liège', 'Bruges', 'Namur', 'Leuven'],
            'Switzerland': ['Zürich', 'Geneva', 'Basel', 'Lausanne', 'Bern', 'Winterthur']
        }
        
        # Mapping pays -> langue
        country_languages = {
            'France': 'Français',
            'Germany': 'Deutsch', 
            'Spain': 'Español',
            'Italy': 'Italiano',
            'Belgium': 'Français',
            'Switzerland': 'Français'
        }
        
        # Recherche du pays
        for country, cities in country_cities.items():
            for known_city in cities:
                if known_city.lower() in store_name.lower():
                    return country, country_languages[country]
        
        # Par défaut
        return 'France', 'Français'

    def create_static_map(self, data: Dict, store_id: str, map_type: str) -> str:
        """Crée une carte statique PNG selon le type demandé."""
        if not HAS_MATPLOTLIB:
            logger.warning("Matplotlib non disponible, retour à HTML")
            return ""
        
        try:
            # Priorité aux isochrones précises pour zone_chalandise
            if map_type == 'zone_chalandise' and self.precise_isochrone_mapper:
                return self._create_precise_zone_map(data, store_id)
            elif map_type == 'competition':
                if self.precise_isochrone_mapper:
                    return self._create_precise_competition_map(data, store_id)
                else:
                    return self._create_static_competition_map(data, store_id)
            elif map_type == 'zone_chalandise':
                return self._create_static_zone_map(data, store_id)
            elif map_type == 'infrastructure':
                return self._create_static_infrastructure_map(data, store_id)
            else:
                logger.error(f"Type de carte non supporté: {map_type}")
                return ""
        except Exception as e:
            logger.error(f"Erreur création carte statique {map_type}: {e}")
            return ""

    def _create_static_competition_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte de concurrence statique."""
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_aspect('equal')
        
        competitors = data.get('competitors', [])
        store_info = data.get('store_info', {})
        
        if not competitors:
            plt.close()
            return ""
        
        # Position du magasin
        store_lat = 49.0789
        store_lon = 6.1109
        
        # Limites de la carte
        lat_range = (48.9, 49.3)
        lon_range = (5.9, 6.3)
        
        ax.set_xlim(lon_range)
        ax.set_ylim(lat_range)
        
        # Zones isochrones
        isochrone_times = [10, 20, 30]
        isochrone_colors = ['#ff444430', '#ff884430', '#ffcc4430']
        isochrone_radii = [0.15, 0.25, 0.35]
        
        for i, (time, color, radius) in enumerate(zip(isochrone_times, isochrone_colors, isochrone_radii)):
            circle = patches.Circle((store_lon, store_lat), radius, 
                                  facecolor=color, edgecolor=color.replace('30', '80'),
                                  linewidth=2, zorder=1)
            ax.add_patch(circle)
        
        # Magasin principal
        ax.scatter(store_lon, store_lat, c='blue', s=200, marker='s', 
                   label=f"Decathlon {store_info.get('name', 'Metz Augny')}", 
                   zorder=5, edgecolor='white', linewidth=2)
        
        # Couleurs par type de concurrent
        competitor_colors = {
            'Généraliste Sport': '#ff4444',
            'Sneakers/Mode': '#ff8844', 
            'Spécialiste Vélo': '#44ff44',
            'Spécialiste Fitness': '#8844ff',
            'Autre': '#888888'
        }
        
        # Ajouter les concurrents
        competitor_counts = {}
        for competitor in competitors[:15]:
            comp_type = competitor.get('type', 'Autre')
            color = competitor_colors.get(comp_type, '#888888')
            
            # Position approximative
            offset_lat = np.random.uniform(-0.1, 0.1)
            offset_lon = np.random.uniform(-0.15, 0.15)
            comp_lat = store_lat + offset_lat
            comp_lon = store_lon + offset_lon
            
            ax.scatter(comp_lon, comp_lat, c=color, s=100, marker='o',
                      alpha=0.8, zorder=3, edgecolor='white', linewidth=1)
            
            competitor_counts[comp_type] = competitor_counts.get(comp_type, 0) + 1
        
        # Configuration
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title(f'Carte Concurrence - Magasin {store_id}\\n{store_info.get("name", "Decathlon Metz Augny")}',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Légende
        legend_elements = [
            patches.Patch(color='#ff444460', label='0-10 min'),
            patches.Patch(color='#ff884460', label='10-20 min'), 
            patches.Patch(color='#ffcc4460', label='20-30 min')
        ]
        
        for comp_type, color in competitor_colors.items():
            count = competitor_counts.get(comp_type, 0)
            if count > 0:
                legend_elements.append(
                    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color,
                              markersize=8, label=f'{comp_type} ({count})')
                )
        
        legend_elements.insert(0, 
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='blue',
                      markersize=10, label='Decathlon Metz Augny')
        )
        
        ax.legend(handles=legend_elements, loc='upper right', 
                 bbox_to_anchor=(1.15, 1), fontsize=10)
        
        plt.tight_layout()
        
        # Sauvegarder
        image_path = f"{self.output_dir}/competition_map_{store_id}.png"
        plt.savefig(image_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"✅ Carte concurrence PNG sauvegardée: {image_path}")
        return image_path

    def _create_static_zone_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte de zone de chalandise statique."""
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_aspect('equal')
        
        store_info = data.get('store_info', {})
        demographics = data.get('demographics', {})
        
        # Position du magasin
        store_lat = 49.0789
        store_lon = 6.1109
        
        # Limites de la carte
        lat_range = (48.85, 49.35)
        lon_range = (5.85, 6.45)
        
        ax.set_xlim(lon_range)
        ax.set_ylim(lat_range)
        
        # Zones isochrones avec formes elliptiques
        zone_data = [
            {'time': '0-5min', 'radius': 0.08, 'color': '#ff000040', 'edge': '#ff000080'},
            {'time': '5-10min', 'radius': 0.16, 'color': '#ff444040', 'edge': '#ff444080'},
            {'time': '10-15min', 'radius': 0.24, 'color': '#ff884040', 'edge': '#ff884080'},
            {'time': '15-20min', 'radius': 0.32, 'color': '#ffcc4040', 'edge': '#ffcc4080'},
            {'time': '20-30min', 'radius': 0.42, 'color': '#ffff8840', 'edge': '#ffff8880'}
        ]
        
        # Dessiner les zones
        for zone in reversed(zone_data):
            ellipse = patches.Ellipse((store_lon, store_lat), 
                                    zone['radius'] * 1.3, zone['radius'],
                                    facecolor=zone['color'], edgecolor=zone['edge'],
                                    linewidth=2, zorder=1)
            ax.add_patch(ellipse)
        
        # Magasin principal
        ax.scatter(store_lon, store_lat, c='blue', s=300, marker='s',
                  label=f"Decathlon {store_info.get('name', 'Metz Augny')}", 
                  zorder=5, edgecolor='white', linewidth=3)
        
        # Configuration
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title(f'Zone de Chalandise - Magasin {store_id}\\n{store_info.get("name", "Decathlon Metz Augny")}',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Légende
        legend_elements = []
        for zone in zone_data:
            legend_elements.append(
                patches.Patch(color=zone['color'].replace('40', '80'), 
                            label=f"Zone {zone['time']}")
            )
        
        legend_elements.insert(0,
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='blue',
                      markersize=12, label='Magasin Decathlon')
        )
        
        ax.legend(handles=legend_elements, loc='upper right',
                 bbox_to_anchor=(1.15, 1), fontsize=10)
        
        # Informations démographiques
        if demographics:
            info_text = "Données locales:\\n"
            if demographics.get('population'):
                info_text += f"Population: {demographics['population']:,}\\n"
            if demographics.get('median_income'):
                info_text += f"Revenu médian: {demographics['median_income']:,} €\\n"
            
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                   fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        plt.tight_layout()
        
        # Sauvegarder
        image_path = f"{self.output_dir}/zone_chalandise_map_{store_id}.png"
        plt.savefig(image_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"✅ Carte zone de chalandise PNG sauvegardée: {image_path}")
        return image_path

    def _create_static_infrastructure_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte des infrastructures statique."""
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_aspect('equal')
        
        infrastructures = data.get('sports_infrastructure', [])
        store_info = data.get('store_info', {})
        
        # Position du magasin
        store_lat = 49.0789
        store_lon = 6.1109
        
        # Limites de la carte
        lat_range = (48.9, 49.25)
        lon_range = (5.95, 6.35)
        
        ax.set_xlim(lon_range)
        ax.set_ylim(lat_range)
        
        # Zone d'influence sportive
        circle = patches.Circle((store_lon, store_lat), 0.08, 
                              facecolor='#44ff4430', edgecolor='#44ff4480',
                              linewidth=2, zorder=1)
        ax.add_patch(circle)
        
        # Magasin principal
        ax.scatter(store_lon, store_lat, c='blue', s=300, marker='s',
                  label=f"Decathlon {store_info.get('name', 'Metz Augny')}", 
                  zorder=5, edgecolor='white', linewidth=3)
        
        # Types d'infrastructures
        infra_colors = {
            'Stade': '#ff4444',
            'Piscine': '#4444ff', 
            'Tennis': '#ffff44',
            'Autre': '#888888'
        }
        
        # Ajouter les infrastructures
        infra_counts = {}
        for infra in infrastructures[:10]:
            infra_type = infra.get('type', 'Autre')
            color = infra_colors.get(infra_type, '#888888')
            
            # Position approximative
            offset_lat = np.random.uniform(-0.06, 0.06)
            offset_lon = np.random.uniform(-0.08, 0.08)
            infra_lat = store_lat + offset_lat
            infra_lon = store_lon + offset_lon
            
            ax.scatter(infra_lon, infra_lat, c=color, s=120, marker='^',
                      alpha=0.8, zorder=3, edgecolor='white', linewidth=1.5)
            
            infra_counts[infra_type] = infra_counts.get(infra_type, 0) + 1
        
        # Configuration
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title(f'Infrastructures Sportives - Magasin {store_id}\\n{store_info.get("name", "Decathlon Metz Augny")}',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Légende
        legend_elements = [
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='blue',
                      markersize=12, label='Magasin Decathlon'),
            patches.Patch(color='#44ff4460', label="Zone d'influence (5km)")
        ]
        
        for infra_type, color in infra_colors.items():
            count = infra_counts.get(infra_type, 0)
            if count > 0:
                legend_elements.append(
                    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor=color,
                              markersize=8, label=f'{infra_type} ({count})')
                )
        
        ax.legend(handles=legend_elements, loc='upper right',
                 bbox_to_anchor=(1.15, 1), fontsize=10)
        
        plt.tight_layout()
        
        # Sauvegarder
        image_path = f"{self.output_dir}/infrastructures_map_{store_id}.png"
        plt.savefig(image_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"✅ Carte infrastructures PNG sauvegardée: {image_path}")
        return image_path

    def _create_precise_zone_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte de zone de chalandise avec isochrones précises."""
        store_info = data.get('store_info', {})
        
        try:
            # Géocodage du magasin
            store_lat, store_lon = self.geocode_address(store_info.get('address', ''))
            if not store_lat or not store_lon:
                # Fallback coordinates pour Metz Augny
                store_lat, store_lon = 49.0789, 6.1109
                
            logger.info(f"Génération d'isochrones précises pour {store_lat:.4f}, {store_lon:.4f}")
            
            # Génération des isochrones précises
            isochrones = self.precise_isochrone_mapper.get_precise_isochrones(
                store_lat, store_lon, times=[10, 20, 30], transport_mode='driving-car'
            )
            
            if not isochrones:
                logger.warning("Aucune isochrone précise générée, fallback vers méthode statique")
                return self._create_static_zone_map(data, store_id)
            
            # Création de l'image avec la méthode professionnelle
            output_path = f"{self.output_dir}/zone_chalandise_map_{store_id}.png"
            
            fig, ax = self.precise_isochrone_mapper.create_professional_map_image(
                store_data={
                    'store_name': store_info.get('name', 'Metz Augny'),
                    'dir_mag': store_info.get('address', ''),
                    'population': data.get('demographics', {}).get('population', 'N/A')
                },
                isochrones=isochrones,
                output_path=output_path,
                dpi=300,
                figsize=(14, 10)
            )
            
            plt.close(fig)
            logger.info(f"✅ Carte zone de chalandise précise PNG sauvegardée: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erreur génération isochrones précises: {e}")
            # Fallback vers méthode statique
            return self._create_static_zone_map(data, store_id)

    def _create_precise_competition_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte de concurrence avec isochrones précises."""
        competitors = data.get('competitors', [])
        store_info = data.get('store_info', {})
        
        try:
            # Géocodage du magasin
            store_lat, store_lon = self.geocode_address(store_info.get('address', ''))
            if not store_lat or not store_lon:
                store_lat, store_lon = 49.0789, 6.1109
            
            # Génération des isochrones précises
            isochrones = self.precise_isochrone_mapper.get_precise_isochrones(
                store_lat, store_lon, times=[10, 20, 30], transport_mode='driving-car'
            )
            
            if not isochrones:
                logger.warning("Aucune isochrone précise générée pour concurrence, fallback vers méthode statique")
                return self._create_static_competition_map(data, store_id)
            
            # Préparation des données concurrents avec géocodage approximatif
            competitors_with_coords = []
            for i, comp in enumerate(competitors[:10]):  # Limiter pour performance
                # Position approximative autour du magasin (en réalité on géocoderait chaque concurrent)
                offset_lat = np.random.uniform(-0.1, 0.1)
                offset_lon = np.random.uniform(-0.15, 0.15)
                competitors_with_coords.append({
                    'latitude': store_lat + offset_lat,
                    'longitude': store_lon + offset_lon,
                    'name': comp.get('name', f'Concurrent {i+1}'),
                    'type': comp.get('type', 'Autre')
                })
            
            # Création de l'image avec concurrents
            output_path = f"{self.output_dir}/competition_map_{store_id}.png"
            
            fig, ax = self.precise_isochrone_mapper.create_professional_map_image(
                store_data={
                    'store_name': store_info.get('name', 'Metz Augny'),
                    'dir_mag': store_info.get('address', ''),
                    'population': data.get('demographics', {}).get('population', 'N/A')
                },
                isochrones=isochrones,
                competitors=competitors_with_coords,
                output_path=output_path,
                dpi=300,
                figsize=(14, 10)
            )
            
            plt.close(fig)
            logger.info(f"✅ Carte concurrence précise PNG sauvegardée: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erreur génération carte concurrence précise: {e}")
            # Fallback vers méthode statique
            return self._create_static_competition_map(data, store_id)
    
    def get_realistic_isochrones(self, lat: float, lon: float, times: List[int] = [10, 20, 30], transport_mode: str = 'car') -> List[Dict]:
        """Génère des isochrones réalistes basées sur le réseau routier."""
        try:
            # Utilisation du générateur d'isochrones réalistes
            isochrones = self.isochrone_generator.get_real_isochrones(lat, lon, times, transport_mode)
            
            # Validation des isochrones
            validated_isochrones = self.isochrone_generator.validate_isochrones(isochrones, lat, lon)
            
            return validated_isochrones
        
        except Exception as e:
            logger.error(f"❌ Erreur génération isochrones réalistes: {e}")
            # Fallback vers l'ancienne méthode si nécessaire
            return self._get_fallback_isochrones(lat, lon, times)
    
    def _get_fallback_isochrones(self, lat: float, lon: float, times: List[int]) -> List[Dict]:
        """Méthode de fallback avec cercles approximatifs si les isochrones réalistes échouent."""
        logger.warning("🔄 Utilisation du mode fallback avec cercles approximatifs")
        
        isochrones = []
        
        for time in times:
            # Estimation: 50 km/h en voiture en moyenne
            radius_km = time * 0.83  # 50 km/h = 0.83 km/min
            
            # Création d'un polygone approximatif
            circle_points = []
            for i in range(36):  # 36 points pour un cercle lisse
                angle = i * 10 * np.pi / 180
                point = geodesic(kilometers=radius_km).destination((lat, lon), angle * 180 / np.pi)
                circle_points.append([point.latitude, point.longitude])
            
            isochrones.append({
                'time': time,
                'coordinates': circle_points,
                'radius_km': radius_km,
                'method': 'fallback_circle'
            })
        
        return isochrones
    
    def create_competition_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte géographique interactive de la concurrence."""
        try:
            competitors = data.get('competitors', [])
            store_info = data.get('store_info', {})
            
            if not competitors:
                logger.warning(f"⚠️ Aucun concurrent trouvé pour le magasin {store_id}")
                return ""
            
            # Géocodage du magasin principal
            store_address = store_info.get('address', '') or f"{store_info.get('name', 'Decathlon')}, {store_info.get('city', '')}, France"
            store_lat, store_lon = self.geocode_address(store_address)
            
            if not store_lat:
                logger.error(f"Impossible de géocoder le magasin: {store_address}")
                return ""
            
            logger.info(f"Magasin géocodé: {store_lat:.4f}, {store_lon:.4f}")
            
            # Création de la carte Folium
            m = folium.Map(location=[store_lat, store_lon], zoom_start=12)
            
            # Ajout du magasin principal
            folium.Marker(
                [store_lat, store_lon],
                popup=f"<b>{store_info.get('name', 'Decathlon')}</b><br>{store_info.get('address', '')}<br>Surface: {store_info.get('surface', 'N/A')} m²",
                icon=folium.Icon(color='blue', icon='shopping-cart', prefix='fa'),
                tooltip="Magasin Decathlon"
            ).add_to(m)
            
            # Couleurs par type de concurrent
            competitor_colors = {
                'Généraliste Sport': 'red',
                'Sneakers/Mode': 'orange',
                'Spécialiste Vélo': 'green', 
                'Spécialiste Fitness': 'purple',
                'Autre': 'gray'
            }
            
            # Géocodage et ajout des concurrents
            geocoded_competitors = 0
            for competitor in competitors[:15]:  # Limiter à 15 pour la performance
                comp_name = competitor.get('name', '')
                comp_address = competitor.get('address', '') or f"{comp_name}, {store_info.get('city', '')}, France"
                
                comp_lat, comp_lon = self.geocode_address(comp_address)
                if comp_lat:
                    color = competitor_colors.get(competitor.get('type', 'Autre'), 'gray')
                    
                    folium.Marker(
                        [comp_lat, comp_lon],
                        popup=f"<b>{comp_name}</b><br>Type: {competitor.get('type', 'N/A')}<br>Distance: {competitor.get('distance_km', 'N/A')} km",
                        icon=folium.Icon(color=color, icon='store', prefix='fa'),
                        tooltip=comp_name
                    ).add_to(m)
                    
                    geocoded_competitors += 1
            
            # Génération des isochrones réalistes (zones de temps de trajet)
            isochrones = self.get_realistic_isochrones(store_lat, store_lon, times=[10, 20, 30], transport_mode='car')
            colors = ['#ff4444', '#ff8844', '#ffcc44']
            zone_names = ['0-10min', '10-20min', '20-30min']
            
            for i, iso in enumerate(isochrones):
                area_info = f"Surface: {iso.get('area_km2', 0):.1f} km²" if iso.get('area_km2') else f"Rayon: ~{iso.get('radius_km', 0):.1f} km"
                method_info = f"Méthode: {iso.get('method', 'inconnue')}"
                
                folium.Polygon(
                    locations=iso['coordinates'],
                    color=colors[i],
                    fillColor=colors[i],
                    fillOpacity=0.2,
                    weight=2,
                    popup=f"Zone {zone_names[i]}<br>{area_info}<br>{method_info}"
                ).add_to(m)
            
            # Légende
            legend_html = f'''
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 220px; height: 160px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:12px; padding: 10px">
            <p><b>Carte Concurrence - Magasin {store_id}</b></p>
            <p><i class="fa fa-shopping-cart" style="color:blue"></i> {store_info.get('name', 'Decathlon')}</p>
            <p><i class="fa fa-store" style="color:red"></i> Généraliste Sport</p>
            <p><i class="fa fa-store" style="color:orange"></i> Sneakers/Mode</p>
            <p><i class="fa fa-store" style="color:green"></i> Spécialiste Vélo</p>
            <p><i class="fa fa-store" style="color:purple"></i> Spécialiste Fitness</p>
            <p><small>{geocoded_competitors}/{len(competitors)} concurrents géocodés</small></p>'''
            
            # Information sur la méthode d'isochrones utilisée
            if isochrones:
                method_used = isochrones[0].get('method', 'inconnue')
                if method_used in ['openrouteservice', 'here_maps', 'osmnx']:
                    legend_html += '<p style="font-size:10px;">🗺️ Zones: réseau routier réel</p>'
                elif method_used == 'smart_approximation':
                    legend_html += '<p style="font-size:10px;">🧠 Zones: approximation intelligente</p>'
                else:
                    legend_html += '<p style="font-size:10px;">⭕ Zones: approximatives</p>'
            
            legend_html += '''</div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Sauvegarder la carte comme image
            image_path = self.save_map_as_image(m, store_id, "competition")
            
            logger.info(f"✅ Carte concurrence sauvegardée: {image_path}")
            logger.info(f"📍 {geocoded_competitors} concurrents géocodés sur {len(competitors)}")
            return image_path
        
        except Exception as e:
            logger.error(f"❌ Erreur génération carte concurrence: {e}")
            return ""
    
    def create_zone_chalandise_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte complète de zone de chalandise avec isochrones et données contextuelles."""
        try:
            store_info = data.get('store_info', {})
            demographics = data.get('demographics', {})
            tourism = data.get('tourism', {})
            mobility = data.get('mobility', {})
            
            # Géocodage du magasin
            store_address = store_info.get('address', '') or f"{store_info.get('name', 'Decathlon')}, {store_info.get('city', '')}, France"
            store_lat, store_lon = self.geocode_address(store_address)
            
            if not store_lat:
                logger.error(f"Impossible de géocoder le magasin: {store_address}")
                return ""
            
            # Création de la carte
            m = folium.Map(location=[store_lat, store_lon], zoom_start=11)
            
            # Génération des isochrones réalistes détaillées basées sur le réseau routier
            isochrones = self.get_realistic_isochrones(store_lat, store_lon, times=[5, 10, 15, 20, 30], transport_mode='car')
            colors = ['#ff0000', '#ff4444', '#ff8844', '#ffcc44', '#ffff88']
            zone_names = ['0-5min', '5-10min', '10-15min', '15-20min', '20-30min']
            
            # Ajout des zones isochrones
            for i, iso in enumerate(isochrones):
                area_info = f"Surface: {iso.get('area_km2', 0):.1f} km²" if iso.get('area_km2') else f"Rayon: ~{iso.get('radius_km', 0):.1f} km"
                method_info = iso.get('method', 'inconnue')
                
                folium.Polygon(
                    locations=iso['coordinates'],
                    color=colors[i],
                    fillColor=colors[i],
                    fillOpacity=0.15,
                    weight=2,
                    popup=f"Zone {zone_names[i]}<br>{area_info}<br>Méthode: {method_info}"
                ).add_to(m)
            
            # Ajout du magasin avec informations détaillées
            popup_content = f"""
            <b>{store_info.get('name', 'Decathlon')}</b><br>
            📍 {store_info.get('address', 'N/A')}<br>
            📐 Surface: {store_info.get('surface', 'N/A')} m²<br>
            """
            
            if demographics.get('population'):
                popup_content += f"👥 Population locale: {demographics['population']:,}<br>"
            if demographics.get('median_income'):
                popup_content += f"💰 Revenu médian: {demographics['median_income']:,} €<br>"
            if tourism.get('annual_visitors'):
                popup_content += f"🏛️ Visiteurs/an: {tourism['annual_visitors']:,}<br>"
            if mobility.get('bike_lanes_km'):
                popup_content += f"🚴 Pistes cyclables: {mobility['bike_lanes_km']} km<br>"
            
            folium.Marker(
                [store_lat, store_lon],
                popup=popup_content,
                icon=folium.Icon(color='blue', icon='shopping-cart', prefix='fa', icon_size=(20, 20)),
                tooltip="Zone de Chalandise"
            ).add_to(m)
            
            # Ajout d'informations contextuelles sur la carte
            info_text = f"""
            <div style="position: fixed; top: 10px; right: 10px; width: 250px;
                        background-color: white; border: 2px solid #333; z-index: 9999;
                        padding: 10px; font-size: 11px; border-radius: 5px;">
            <h4>Zone de Chalandise - Magasin {store_id}</h4>
            <p><b>{store_info.get('name', 'Decathlon')}</b></p>
            """
            
            if demographics:
                info_text += "<p><b>Démographie locale:</b><br>"
                if demographics.get('population'):
                    info_text += f"Population: {demographics['population']:,} hab.<br>"
                if demographics.get('median_income'):
                    info_text += f"Revenu médian: {demographics['median_income']:,} €<br>"
                info_text += "</p>"
            
            if tourism or mobility:
                info_text += "<p><b>Contexte local:</b><br>"
                if tourism.get('annual_visitors'):
                    info_text += f"Tourisme: {tourism['annual_visitors']:,} visiteurs/an<br>"
                if mobility.get('bike_lanes_km'):
                    info_text += f"Mobilité douce: {mobility['bike_lanes_km']} km pistes<br>"
                info_text += "</p>"
            
            # Information sur la méthode utilisée pour les isochrones
            if isochrones:
                method_used = isochrones[0].get('method', 'inconnue')
                if method_used in ['openrouteservice', 'here_maps', 'osmnx']:
                    info_text += "<p><small>🗺️ Zones basées sur le réseau routier réel</small></p>"
                elif method_used == 'smart_approximation':
                    info_text += "<p><small>🧠 Zones par approximation intelligente</small></p>"
                else:
                    info_text += "<p><small>⭕ Zones approximatives (fallback)</small></p>"
            
            info_text += "</div>"
            m.get_root().html.add_child(folium.Element(info_text))
            
            # Sauvegarder comme image
            image_path = self.save_map_as_image(m, store_id, "zone_chalandise")
            
            logger.info(f"✅ Carte zone de chalandise sauvegardée: {image_path}")
            return image_path
        
        except Exception as e:
            logger.error(f"❌ Erreur génération carte zone de chalandise: {e}")
            return ""
    
    def create_demographics_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte des infrastructures sportives et lieux d'intérêt."""
        try:
            infrastructures = data.get('sports_infrastructure', [])
            store_info = data.get('store_info', {})
            tourism = data.get('tourism', {})
            
            if not infrastructures and not tourism.get('main_attractions'):
                logger.warning(f"⚠️ Aucune infrastructure ou attraction trouvée pour le magasin {store_id}")
                return ""
            
            # Géocodage du magasin
            store_address = store_info.get('address', '') or f"{store_info.get('name', 'Decathlon')}, {store_info.get('city', '')}, France"
            store_lat, store_lon = self.geocode_address(store_address)
            
            if not store_lat:
                logger.error(f"Impossible de géocoder le magasin: {store_address}")
                return ""
            
            # Création de la carte
            m = folium.Map(location=[store_lat, store_lon], zoom_start=12)
            
            # Ajout du magasin
            folium.Marker(
                [store_lat, store_lon],
                popup=f"<b>{store_info.get('name', 'Decathlon')}</b><br>{store_info.get('address', '')}",
                icon=folium.Icon(color='blue', icon='shopping-cart', prefix='fa'),
                tooltip="Magasin Decathlon"
            ).add_to(m)
            
            # Couleurs par type d'infrastructure
            infra_colors = {
                'Stade': 'red',
                'Piscine': 'lightblue',
                'Fitness': 'green', 
                'Athlétisme': 'orange',
                'Autre': 'gray'
            }
            
            # Icônes par type
            infra_icons = {
                'Stade': 'futbol-o',
                'Piscine': 'tint',
                'Fitness': 'heartbeat',
                'Athlétisme': 'road',
                'Autre': 'building'
            }
            
            # Géocodage et ajout des infrastructures sportives
            geocoded_infras = 0
            for infra in infrastructures[:10]:  # Limiter à 10
                infra_name = infra.get('name', '')
                infra_address = infra.get('address', '') or f"{infra_name}, {store_info.get('city', '')}, France"
                
                infra_lat, infra_lon = self.geocode_address(infra_address)
                if infra_lat:
                    infra_type = infra.get('type', 'Autre')
                    color = infra_colors.get(infra_type, 'gray')
                    icon = infra_icons.get(infra_type, 'building')
                    
                    popup_content = f"<b>{infra_name}</b><br>Type: {infra_type}"
                    if infra.get('capacity'):
                        popup_content += f"<br>Capacité: {infra['capacity']}"
                    if infra.get('address'):
                        popup_content += f"<br>📍 {infra['address']}"
                    
                    folium.Marker(
                        [infra_lat, infra_lon],
                        popup=popup_content,
                        icon=folium.Icon(color=color, icon=icon, prefix='fa'),
                        tooltip=infra_name
                    ).add_to(m)
                    
                    geocoded_infras += 1
            
            # Ajout des attractions touristiques si disponibles
            attractions = tourism.get('main_attractions', [])
            for attraction in attractions[:5]:  # Limiter à 5
                if isinstance(attraction, str):
                    attr_address = f"{attraction}, {store_info.get('city', '')}, France"
                    attr_lat, attr_lon = self.geocode_address(attr_address)
                    if attr_lat:
                        folium.Marker(
                            [attr_lat, attr_lon],
                            popup=f"<b>{attraction}</b><br>Attraction touristique",
                            icon=folium.Icon(color='pink', icon='camera', prefix='fa'),
                            tooltip=attraction
                        ).add_to(m)
            
            # Zone d'influence sportive (cercle de 5km)
            folium.Circle(
                [store_lat, store_lon],
                radius=5000,
                popup="Zone d'influence sportive (5km)",
                color='green',
                fillColor='green',
                fillOpacity=0.1,
                weight=2
            ).add_to(m)
            
            # Légende
            legend_html = f'''
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 220px; height: 140px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:12px; padding: 10px">
            <p><b>Infrastructures Sportives - {store_id}</b></p>
            <p><i class="fa fa-shopping-cart" style="color:blue"></i> {store_info.get('name', 'Decathlon')}</p>
            <p><i class="fa fa-futbol-o" style="color:red"></i> Stades</p>
            <p><i class="fa fa-tint" style="color:lightblue"></i> Piscines</p>
            <p><i class="fa fa-heartbeat" style="color:green"></i> Fitness</p>
            <p><i class="fa fa-camera" style="color:pink"></i> Attractions</p>
            <p><small>{geocoded_infras} infrastructures géocodées</small></p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Sauvegarder comme image
            image_path = self.save_map_as_image(m, store_id, "infrastructures")
            
            logger.info(f"✅ Carte infrastructures sauvegardée: {image_path}")
            logger.info(f"🏃 {geocoded_infras} infrastructures géocodées sur {len(infrastructures)}")
            return image_path
        
        except Exception as e:
            logger.error(f"❌ Erreur génération carte infrastructures: {e}")
            return ""
    
    def create_infrastructure_map(self, data: Dict, store_id: str) -> str:
        """Crée une carte des infrastructures sportives."""
        try:
            infrastructures = data.get('sports_infrastructure', [])
            store_info = data.get('store_info', {})
            
            if not infrastructures:
                logger.warning(f"⚠️ Aucune infrastructure trouvée pour le magasin {store_id}")
                return ""
            
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Compter par type
            type_counts = {}
            for infra in infrastructures:
                infra_type = infra.get('type', 'Autre')
                type_counts[infra_type] = type_counts.get(infra_type, 0) + 1
            
            # Couleurs par type
            color_map = {
                'Stade': '#FF4444',
                'Piscine': '#4444FF', 
                'Fitness': '#44AA44',
                'Athlétisme': '#FF8800',
                'Autre': '#CCCCCC'
            }
            
            types = list(type_counts.keys())
            counts = list(type_counts.values())
            colors = [color_map.get(t, '#CCCCCC') for t in types]
            
            # Graphique en secteurs
            wedges, texts, autotexts = ax.pie(counts, labels=types, colors=colors, autopct='%1.0f',
                                             startangle=90, explode=[0.05] * len(types))
            
            # Personnaliser les textes
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(12)
            
            for text in texts:
                text.set_fontsize(11)
                text.set_fontweight('bold')
            
            ax.set_title(f'Infrastructures Sportives - Magasin {store_id}\n{store_info.get("name", "Decathlon")} - {len(infrastructures)} infrastructures identifiées', 
                        fontsize=14, fontweight='bold', pad=20)
            
            # Liste détaillée en bas
            infra_list = '\n'.join([f"• {infra.get('name', 'Inconnu')} ({infra.get('type', 'Autre')})" 
                                   for infra in infrastructures[:8]])  # Limiter à 8
            if len(infrastructures) > 8:
                infra_list += f"\n... et {len(infrastructures) - 8} autres"
            
            plt.figtext(0.02, 0.02, infra_list, fontsize=9, verticalalignment='bottom')
            
            plt.tight_layout()
            
            # Sauvegarder
            png_path = f"{self.output_dir}/geo_infrastructure_map_{store_id}.png"
            plt.savefig(png_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            logger.info(f"✅ Carte infrastructures sauvegardée: {png_path}")
            return png_path
            
        except Exception as e:
            logger.error(f"❌ Erreur génération carte infrastructures: {e}")
            return ""
    
    def determine_appropriate_maps(self, data: Dict) -> List[str]:
        """Détermine quelles cartes géographiques générer selon les données disponibles."""
        maps_to_generate = []
        
        # Carte de concurrence si on a des concurrents
        if data.get('competitors'):
            maps_to_generate.append('competition')
        
        # Carte de zone de chalandise (toujours utile s'il y a des données contextuelles)
        if data.get('demographics') or data.get('mobility') or data.get('tourism'):
            maps_to_generate.append('zone_chalandise')
        
        # Carte des infrastructures si on a des infrastructures ou attractions
        if data.get('sports_infrastructure') or (data.get('tourism', {}).get('main_attractions')):
            maps_to_generate.append('infrastructure')
        
        logger.info(f"🗺️ {len(maps_to_generate)} types de cartes géographiques à générer: {', '.join(maps_to_generate)}")
        return maps_to_generate
    
    def init_firestore(self) -> bool:
        """Initialise Firestore."""
        try:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
            self.db = firestore.Client(project=self.project_id)
            logger.info("✅ Firestore initialisé")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur Firestore: {e}")
            return False
    
    def process_store(self, store_id: str) -> Dict:
        """Traite un magasin et génère les cartes appropriées."""
        logger.info(f"🗺️ Démarrage traitement géographique magasin {store_id}")
        
        try:
            # Extraire les données de captation
            captation_data = self.extract_captation_data(store_id)
            if not captation_data:
                return {"success": False, "error": "Données de captation non trouvées"}
            
            # Déterminer les cartes à générer
            maps_to_generate = self.determine_appropriate_maps(captation_data)
            
            if not maps_to_generate:
                return {"success": False, "error": "Aucune donnée suffisante pour générer des cartes"}
            
            # Générer les cartes
            generated_maps = {}
            
            for map_type in maps_to_generate:
                # Priorité à la génération PNG statique
                image_path = self.create_static_map(captation_data, store_id, map_type)
                if image_path:
                    generated_maps[map_type] = image_path
                else:
                    # Fallback vers HTML si PNG échoue
                    if map_type == 'competition':
                        html_path = self.create_competition_map(captation_data, store_id)
                        if html_path:
                            generated_maps['competition'] = html_path
                    
                    elif map_type == 'zone_chalandise':
                        html_path = self.create_zone_chalandise_map(captation_data, store_id)
                        if html_path:
                            generated_maps['zone_chalandise'] = html_path
                    
                    elif map_type == 'infrastructure':
                        html_path = self.create_demographics_map(captation_data, store_id)
                        if html_path:
                            generated_maps['infrastructure'] = html_path
            
            result = {
                "success": True,
                "store_id": store_id,
                "maps_generated": generated_maps,
                "processing_date": datetime.now().isoformat(),
                "maps_count": len(generated_maps),
                "data_summary": {
                    "competitors_found": len(captation_data.get('competitors', [])),
                    "infrastructures_found": len(captation_data.get('sports_infrastructure', [])),
                    "has_demographics": bool(captation_data.get('demographics')),
                    "has_tourism_data": bool(captation_data.get('tourism'))
                }
            }
            
            logger.info(f"✅ Traitement géographique terminé: {len(generated_maps)} cartes générées")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement magasin {store_id}: {e}")
            return {"success": False, "error": str(e)}


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='POLCO Geo-Processor Générique - Cartographie basée sur captation')
    parser.add_argument('--store-id', type=str, default='42',
                      help='ID du magasin à traiter (défaut: 42)')
    
    args = parser.parse_args()
    
    processor = PolcoGeoProcessor()
    
    try:
        if not processor.init_firestore():
            logger.error("❌ Impossible d'initialiser Firestore")
            return 1
        
        if not processor.init_vertex_ai():
            logger.error("❌ Impossible d'initialiser Vertex AI")
            return 1
        
        result = processor.process_store(args.store_id)
        
        if result["success"]:
            logger.info(f"🎉 Géo-traitement réussi ! {result['maps_count']} cartes générées")
            logger.info(f"📁 Cartes disponibles dans: {processor.output_dir}/")
            logger.info(f"📊 Résumé: {result['data_summary']}")
            return 0
        else:
            logger.error(f"❌ Échec du traitement: {result.get('error', 'Erreur inconnue')}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        return 1


if __name__ == "__main__":
    exit(main())