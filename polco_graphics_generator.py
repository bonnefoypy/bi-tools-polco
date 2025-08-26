#!/usr/bin/env python3
"""
POLCO ANALYZER 3.0 - Générateur de Graphiques
Génération automatique de visualisations pour enrichir les analyses
"""

import os
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import base64
from io import BytesIO

# Configuration
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration matplotlib pour le français
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

# Palette couleurs Decathlon
DECATHLON_COLORS = ['#0082C3', '#00A651', '#FF6900', '#E6007E', '#8B2635', '#FFD100']
sns.set_palette(DECATHLON_COLORS)


class PolcoGraphicsGenerator:
    """Générateur de graphiques pour les analyses POLCO."""
    
    def __init__(self, output_dir: str = "analytics_charts"):
        """Initialise le générateur."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def create_top_sports_bar_chart(self, ca_par_sport: List[Dict], store_id: str, top_n: int = 10) -> str:
        """Crée un graphique en barres des top sports par CA."""
        
        try:
            if not ca_par_sport:
                return ""
            
            # Préparer les données
            sorted_sports = sorted(ca_par_sport, 
                                 key=lambda x: float(str(x.get('total_gmv', 0)).replace(',', '')), 
                                 reverse=True)[:top_n]
            
            sports = [sport.get('sport_department_label', 'N/A')[:20] + '...' if len(sport.get('sport_department_label', '')) > 20 
                     else sport.get('sport_department_label', 'N/A') for sport in sorted_sports]
            cas = [float(str(sport.get('total_gmv', 0)).replace(',', '')) for sport in sorted_sports]
            
            # Créer le graphique
            fig, ax = plt.subplots(figsize=(14, 8))
            bars = ax.barh(range(len(sports)), cas, color=DECATHLON_COLORS[0])
            
            # Personnalisation
            ax.set_yticks(range(len(sports)))
            ax.set_yticklabels(sports)
            ax.set_xlabel('Chiffre d\'Affaires (€)')
            ax.set_title(f'TOP {top_n} Sports par CA - Magasin {store_id}', fontsize=14, fontweight='bold')
            
            # Ajouter les valeurs sur les barres
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width + max(cas) * 0.01, bar.get_y() + bar.get_height()/2, 
                       f'{width:,.0f}€', ha='left', va='center', fontweight='bold')
            
            plt.tight_layout()
            
            # Sauvegarder
            filename = f"top_sports_ca_{store_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Erreur création graphique top sports: {e}")
            return ""
    
    def create_age_distribution_chart(self, age_data: List[Dict], store_id: str) -> str:
        """Crée un graphique de répartition par âge."""
        
        try:
            if not age_data:
                return ""
            
            # Préparer les données
            ages = [row.get('age_range', 'N/A') for row in age_data]
            percentages = [float(str(row.get('percentage', 0))) for row in age_data]
            
            # Créer le graphique en secteurs
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Couleurs dégradées
            colors = plt.cm.Set3(np.linspace(0, 1, len(ages)))
            
            wedges, texts, autotexts = ax.pie(percentages, labels=ages, autopct='%1.1f%%', 
                                            colors=colors, startangle=90)
            
            # Personnalisation
            ax.set_title(f'Répartition Clients par Tranche d\'Âge - Magasin {store_id}', 
                        fontsize=14, fontweight='bold')
            
            # Améliorer la lisibilité
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            plt.tight_layout()
            
            # Sauvegarder
            filename = f"age_distribution_{store_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Erreur création graphique âge: {e}")
            return ""
    
    def create_monthly_evolution_chart(self, monthly_data: List[Dict], store_id: str) -> str:
        """Crée un graphique d'évolution mensuelle du CA."""
        
        try:
            if not monthly_data:
                return ""
            
            # Préparer les données
            months = []
            revenues = []
            
            for row in monthly_data:
                month = row.get('month', '')
                revenue = float(str(row.get('monthly_revenue', 0)).replace(',', ''))
                if month and revenue:
                    months.append(month)
                    revenues.append(revenue)
            
            if not months:
                return ""
            
            # Créer le graphique
            fig, ax = plt.subplots(figsize=(14, 8))
            
            ax.plot(months, revenues, marker='o', linewidth=3, markersize=8, 
                   color=DECATHLON_COLORS[0])
            ax.fill_between(months, revenues, alpha=0.3, color=DECATHLON_COLORS[0])
            
            # Personnalisation
            ax.set_xlabel('Mois')
            ax.set_ylabel('Chiffre d\'Affaires (€)')
            ax.set_title(f'Évolution Mensuelle du CA - Magasin {store_id}', 
                        fontsize=14, fontweight='bold')
            
            # Rotation des labels de mois
            plt.xticks(rotation=45)
            
            # Ajouter la valeur sur chaque point
            for i, revenue in enumerate(revenues):
                ax.annotate(f'{revenue:,.0f}€', (months[i], revenue), 
                           textcoords="offset points", xytext=(0,10), ha='center')
            
            plt.tight_layout()
            
            # Sauvegarder
            filename = f"monthly_evolution_{store_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Erreur création graphique évolution: {e}")
            return ""
    
    def create_brand_mix_chart(self, brand_data: List[Dict], store_id: str) -> str:
        """Crée un graphique de répartition des marques."""
        
        try:
            if not brand_data:
                return ""
            
            # Préparer les données - gestion des deux formats possibles
            brands = []
            values = []
            percentages = []
            
            # Calculer le total pour les pourcentages
            total_ca = 0
            for row in brand_data:
                # Format 1: avec percentage et amount 
                if 'percentage' in row:
                    brands.append(row.get('brand_type', 'N/A'))
                    percentages.append(float(str(row.get('percentage', 0))))
                    values.append(float(str(row.get('amount', 0))))
                # Format 2: avec total_gmv seulement
                elif 'total_gmv' in row:
                    brands.append(row.get('brand_type', 'N/A'))
                    gmv = float(str(row.get('total_gmv', 0)))
                    values.append(gmv)
                    total_ca += gmv
            
            # Si on a que des total_gmv, calculer les pourcentages
            if not percentages and total_ca > 0:
                percentages = [(value / total_ca * 100) for value in values]
            elif not percentages:
                logger.warning(f"⚠️ Données marques invalides pour {store_id}")
                return ""
            
            # Créer le graphique
            fig, ax = plt.subplots(figsize=(12, 8))
            
            bars = ax.bar(brands, percentages, color=DECATHLON_COLORS[:len(brands)])
            
            # Personnalisation
            ax.set_ylabel('Pourcentage du CA (%)')
            ax.set_title(f'Mix Marques - Magasin {store_id}', fontsize=14, fontweight='bold')
            
            # Ajouter les valeurs sur les barres
            for i, bar in enumerate(bars):
                height = bar.get_height()
                value_text = f'{height:.1f}%'
                if i < len(values):
                    value_text += f'\\n({values[i]:,.0f}€)'
                ax.text(bar.get_x() + bar.get_width()/2., height + max(percentages) * 0.01,
                       value_text, ha='center', va='bottom', fontweight='bold')
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Sauvegarder
            filename = f"brand_mix_{store_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"✅ Graphique marques créé: {len(brands)} marques, total {total_ca:,.0f}€")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Erreur création graphique marques: {e}")
            import traceback
            logger.error(f"Détails: {traceback.format_exc()}")
            return ""
    
    def create_dvs_heatmap(self, dvs_data: List[Dict], store_id: str) -> str:
        """Crée une heatmap des durées de vie des stocks."""
        
        try:
            if not dvs_data:
                return ""
            
            # Filtrer les DVS problématiques (> 90 jours)
            problematic_dvs = [row for row in dvs_data 
                             if float(str(row.get('stock_lifetime_days', 0))) > 90]
            
            if not problematic_dvs:
                return ""
            
            # Préparer les données
            sports = [row.get('sport_department_label', 'N/A')[:15] + '...' 
                     if len(row.get('sport_department_label', '')) > 15 
                     else row.get('sport_department_label', 'N/A') for row in problematic_dvs[:15]]
            dvs_values = [float(str(row.get('stock_lifetime_days', 0))) for row in problematic_dvs[:15]]
            
            # Créer la heatmap
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Créer une matrice pour la heatmap
            data_matrix = np.array(dvs_values).reshape(-1, 1)
            
            im = ax.imshow(data_matrix, cmap='Reds', aspect='auto')
            
            # Personnalisation
            ax.set_yticks(range(len(sports)))
            ax.set_yticklabels(sports)
            ax.set_xticks([0])
            ax.set_xticklabels(['DVS (jours)'])
            ax.set_title(f'Durée de Vie des Stocks Problématiques - Magasin {store_id}', 
                        fontsize=14, fontweight='bold')
            
            # Ajouter les valeurs dans les cellules
            for i, value in enumerate(dvs_values):
                ax.text(0, i, f'{value:.0f}j', ha='center', va='center', 
                       color='white' if value > max(dvs_values) * 0.7 else 'black',
                       fontweight='bold')
            
            # Colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Jours de stock')
            
            plt.tight_layout()
            
            # Sauvegarder
            filename = f"dvs_heatmap_{store_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Erreur création heatmap DVS: {e}")
            return ""
    
    def create_performance_dashboard(self, complete_data: Dict[str, Any], store_id: str) -> List[str]:
        """Crée un dashboard complet de graphiques."""
        
        logger.info(f"📊 Génération dashboard graphiques magasin {store_id}")
        
        generated_charts = []
        
        # Extraire les données
        data_sources = complete_data.get('data_sources', {})
        internal_data = data_sources.get('internal_data', {})
        csv_files = internal_data.get('csv_files', {})
        
        # 1. Top sports par CA
        ca_par_sport = csv_files.get('ca_par_sport', {}).get('data', [])
        if ca_par_sport:
            chart = self.create_top_sports_bar_chart(ca_par_sport, store_id)
            if chart:
                generated_charts.append(chart)
        
        # 2. Répartition par âge
        age_data = csv_files.get('repartition_des_ages_pour_les_comptes_du_magasin', {}).get('data', [])
        if age_data:
            chart = self.create_age_distribution_chart(age_data, store_id)
            if chart:
                generated_charts.append(chart)
        
        # 3. Évolution mensuelle
        monthly_data = csv_files.get('chiffre_d_affaires_instore_sur_les_12_derniers_mois_par_mois', {}).get('data', [])
        if monthly_data:
            chart = self.create_monthly_evolution_chart(monthly_data, store_id)
            if chart:
                generated_charts.append(chart)
        
        # 4. Mix marques
        brand_data = csv_files.get('repartition_du_ca_par_type_de_marque', {}).get('data', [])
        if brand_data:
            chart = self.create_brand_mix_chart(brand_data, store_id)
            if chart:
                generated_charts.append(chart)
        
        # 5. DVS heatmap
        dvs_data = csv_files.get('duree_de_vie_des_stocks_par_sport', {}).get('data', [])
        if dvs_data:
            chart = self.create_dvs_heatmap(dvs_data, store_id)
            if chart:
                generated_charts.append(chart)
        
        logger.info(f"✅ {len(generated_charts)} graphiques générés pour magasin {store_id}")
        return generated_charts
    
    def generate_chart_markdown_integration(self, chart_filenames: List[str]) -> str:
        """Génère le code Markdown pour intégrer les graphiques."""
        
        if not chart_filenames:
            return ""
        
        markdown_content = """

---

## 📊 VISUALISATIONS DE DONNÉES

"""
        
        chart_titles = {
            'top_sports_ca': '### 🏆 Top Sports par Chiffre d\'Affaires',
            'age_distribution': '### 👥 Répartition de la Clientèle par Âge',
            'monthly_evolution': '### 📈 Évolution Mensuelle du Chiffre d\'Affaires',
            'brand_mix': '### 🏷️ Mix Marques',
            'dvs_heatmap': '### ⚠️ Durées de Vie des Stocks Problématiques'
        }
        
        for chart_file in chart_filenames:
            # Identifier le type de graphique
            chart_type = None
            for key in chart_titles.keys():
                if key in chart_file:
                    chart_type = key
                    break
            
            if chart_type:
                markdown_content += f"""
{chart_titles[chart_type]}

![{chart_titles[chart_type].replace('#', '').strip()}](./analytics_charts/{chart_file})

"""
        
        return markdown_content


def main():
    """Test du générateur de graphiques."""
    pass


if __name__ == "__main__":
    main()
