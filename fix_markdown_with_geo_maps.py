#!/usr/bin/env python3
"""
Script pour ajouter manuellement les cartes géographiques au rapport Markdown
"""

def add_geo_maps_to_markdown(file_path: str, store_id: str):
    """Ajoute les cartes géographiques au rapport Markdown."""
    
    # Lire le fichier existant
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Section cartes géographiques à ajouter
    geo_section = f"""

## 🗺️ ANALYSES GÉOGRAPHIQUES

*Cartes interactives générées automatiquement par POLCO GEO-PROCESSOR*


### 🏪 Positionnement Concurrentiel

![🏪 Positionnement Concurrentiel](./graphics/geo_competition_map_{store_id}.png)

**Analyse géographique :**
- Zones d'influence par type de concurrent (Généralistes, Spécialistes, Mode)  
- Distances précises depuis le magasin Decathlon
- Zones primaire (0-15km) et secondaire (15-30km) de chalandise
- Opportunités géographiques de développement commercial


### 🏃 Infrastructures Sportives Locales

![🏃 Infrastructures Sportives Locales](./graphics/geo_sports_infrastructure_{store_id}.png)

**Écosystème sportif territorial :**
- Équipements majeurs géolocalisés (stades, salles, piscines)
- Capacités et spécialisations par infrastructure  
- Projets futurs et opportunités de partenariat
- Potentiel de synergies avec l'offre magasin


### ⏰ Zones de Chalandise

![⏰ Zones de Chalandise](./graphics/geo_isochrone_zones_{store_id}.png)

**Accessibilité et zone d'influence :**
- Zones de temps de trajet (0-10min, 10-20min, 20-30min)
- Délimitation précise zone primaire/secondaire
- Potentiel de clientèle par zone géographique
- Optimisation de l'accessibilité et des flux


"""
    
    # Trouver où insérer la section (avant MÉTHODOLOGIE)
    methodology_marker = "## 🔬 MÉTHODOLOGIE POLCO ANALYZER 3.0"
    
    if methodology_marker in content:
        # Insérer avant la méthodologie
        content = content.replace(methodology_marker, geo_section + methodology_marker)
    else:
        # Ajouter à la fin
        content += geo_section
    
    # Sauvegarder le fichier modifié
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Cartes géographiques ajoutées au rapport {file_path}")


if __name__ == "__main__":
    import sys
    
    store_id = sys.argv[1] if len(sys.argv) > 1 else "42"
    file_path = f"reports_polco_3_0/POLCO_3_0_DECATHLON_{store_id}_Analyse_Sectorielle.md"
    
    try:
        add_geo_maps_to_markdown(file_path, store_id)
        print(f"🎉 Cartes géographiques intégrées avec succès pour le magasin {store_id}")
    except Exception as e:
        print(f"❌ Erreur: {e}")



