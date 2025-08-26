#!/usr/bin/env python3
"""
Générateur de cartes statiques PNG pour POLCO
Utilise matplotlib et des données géographiques pour créer des images
"""

import os
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Dict, List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class StaticMapGenerator:
    """Générateur de cartes statiques PNG."""
    
    def __init__(self, output_dir: str = "geo_maps"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Couleurs par type de concurrent
        self.competitor_colors = {
            'Généraliste Sport': '#ff4444',
            'Sneakers/Mode': '#ff8844', 
            'Spécialiste Vélo': '#44ff44',
            'Spécialiste Fitness': '#8844ff',
            'Autre': '#888888'
        }
        
        # Configuration matplotlib
        plt.style.use('default')
        
    def create_competition_map_image(self, data: Dict, store_id: str) -> str:
        """Crée une carte de concurrence en PNG."""
        
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_aspect('equal')
        
        competitors = data.get('competitors', [])
        store_info = data.get('store_info', {})
        
        if not competitors:
            return ""
        
        # Position du magasin principal (centre)
        store_lat = 49.0789
        store_lon = 6.1109
        
        # Limites de la carte (approximative zone de Metz)
        lat_range = (48.9, 49.3)
        lon_range = (5.9, 6.3)
        
        ax.set_xlim(lon_range)
        ax.set_ylim(lat_range)
        
        # Ajouter le magasin principal
        ax.scatter(store_lon, store_lat, c='blue', s=200, marker='s', 
                   label=f"Decathlon {store_info.get('name', 'Metz Augny')}", 
                   zorder=5, edgecolor='white', linewidth=2)
        
        # Ajouter les zones isochrones (cercles approximatifs)
        isochrone_times = [10, 20, 30]
        isochrone_colors = ['#ff444430', '#ff884430', '#ffcc4430']
        isochrone_radii = [0.15, 0.25, 0.35]  # En degrés approximatifs
        
        for i, (time, color, radius) in enumerate(zip(isochrone_times, isochrone_colors, isochrone_radii)):
            circle = patches.Circle((store_lon, store_lat), radius, 
                                  facecolor=color, edgecolor=isochrone_colors[i].replace('30', '80'),
                                  linewidth=2, zorder=1)
            ax.add_patch(circle)
        
        # Ajouter les concurrents
        competitor_counts = {}
        for competitor in competitors[:15]:  # Limiter pour la lisibilité
            comp_type = competitor.get('type', 'Autre')
            color = self.competitor_colors.get(comp_type, '#888888')
            
            # Position approximative (vous devriez avoir les vraies coordonnées)
            # Ici on disperse aléatoirement autour du magasin
            offset_lat = np.random.uniform(-0.1, 0.1)
            offset_lon = np.random.uniform(-0.15, 0.15)
            comp_lat = store_lat + offset_lat
            comp_lon = store_lon + offset_lon
            
            ax.scatter(comp_lon, comp_lat, c=color, s=100, marker='o',
                      alpha=0.8, zorder=3, edgecolor='white', linewidth=1)
            
            # Compter par type
            competitor_counts[comp_type] = competitor_counts.get(comp_type, 0) + 1
        
        # Configuration des axes
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title(f'Carte Concurrence - Magasin {store_id}\\n{store_info.get("name", "Decathlon Metz Augny")}',
                    fontsize=16, fontweight='bold', pad=20)
        
        # Grille de fond
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Légende des zones isochrones
        legend_elements = [
            patches.Patch(color='#ff444460', label='0-10 min'),
            patches.Patch(color='#ff884460', label='10-20 min'), 
            patches.Patch(color='#ffcc4460', label='20-30 min')
        ]
        
        # Ajouter les types de concurrents à la légende
        for comp_type, color in self.competitor_colors.items():
            count = competitor_counts.get(comp_type, 0)
            if count > 0:
                legend_elements.append(
                    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color,
                              markersize=8, label=f'{comp_type} ({count})')
                )
        
        # Magasin principal
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
    
    def create_zone_chalandise_image(self, data: Dict, store_id: str) -> str:
        """Crée une carte de zone de chalandise en PNG."""
        
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
        
        # Zones isochrones avec formes plus réalistes
        zone_data = [
            {'time': '0-5min', 'radius': 0.08, 'color': '#ff000040', 'edge': '#ff000080'},
            {'time': '5-10min', 'radius': 0.16, 'color': '#ff444040', 'edge': '#ff444080'},
            {'time': '10-15min', 'radius': 0.24, 'color': '#ff884040', 'edge': '#ff884080'},
            {'time': '15-20min', 'radius': 0.32, 'color': '#ffcc4040', 'edge': '#ffcc4080'},
            {'time': '20-30min', 'radius': 0.42, 'color': '#ffff8840', 'edge': '#ffff8880'}
        ]
        
        # Dessiner les zones (de la plus grande à la plus petite)
        for zone in reversed(zone_data):
            # Forme légèrement elliptique pour plus de réalisme
            ellipse = patches.Ellipse((store_lon, store_lat), 
                                    zone['radius'] * 1.3,  # Largeur
                                    zone['radius'],         # Hauteur
                                    facecolor=zone['color'], 
                                    edgecolor=zone['edge'],
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
        
        # Légende des zones
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
    
    def create_infrastructure_image(self, data: Dict, store_id: str) -> str:
        """Crée une carte des infrastructures en PNG."""
        
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
        
        # Zone d'influence sportive (5km)
        circle = patches.Circle((store_lon, store_lat), 0.08, 
                              facecolor='#44ff4430', edgecolor='#44ff4480',
                              linewidth=2, zorder=1, label="Zone d'influence (5km)")
        ax.add_patch(circle)
        
        # Magasin principal
        ax.scatter(store_lon, store_lat, c='blue', s=300, marker='s',
                  label=f"Decathlon {store_info.get('name', 'Metz Augny')}", 
                  zorder=5, edgecolor='white', linewidth=3)
        
        # Types d'infrastructures et leurs couleurs
        infra_colors = {
            'Stade': '#ff4444',
            'Piscine': '#4444ff', 
            'Salle de sport': '#44ff44',
            'Tennis': '#ffff44',
            'Autre': '#888888'
        }
        
        # Ajouter les infrastructures
        infra_counts = {}
        for infra in infrastructures[:10]:  # Limiter à 10
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

def main():
    """Test du générateur de cartes statiques."""
    
    # Données de test
    test_data = {
        'store_info': {
            'name': 'Metz Augny',
            'address': 'Zone Actisud - Route des Gravières, 57685 Augny'
        },
        'competitors': [
            {'name': 'Intersport', 'type': 'Généraliste Sport', 'distance_km': 3},
            {'name': 'JD Sports', 'type': 'Sneakers/Mode', 'distance_km': 7},
            {'name': 'Basic-Fit', 'type': 'Spécialiste Fitness', 'distance_km': 1.5},
            {'name': 'Veloland', 'type': 'Spécialiste Vélo', 'distance_km': 2},
        ],
        'sports_infrastructure': [
            {'name': 'Stade Saint-Symphorien', 'type': 'Stade'},
            {'name': 'Piscine Lothaire', 'type': 'Piscine'},
            {'name': 'Tennis Club Metz', 'type': 'Tennis'},
        ],
        'demographics': {
            'population': 230314,
            'median_income': 23000
        }
    }
    
    # Générer les cartes
    generator = StaticMapGenerator()
    
    print("🗺️ Génération des cartes statiques PNG")
    
    competition_map = generator.create_competition_map_image(test_data, "42")
    zone_map = generator.create_zone_chalandise_image(test_data, "42") 
    infra_map = generator.create_infrastructure_image(test_data, "42")
    
    print(f"✅ Cartes générées:")
    print(f"   - {competition_map}")
    print(f"   - {zone_map}")
    print(f"   - {infra_map}")

if __name__ == "__main__":
    main()