#!/usr/bin/env python3
"""
POLCO ANALYZER 3.0 - Assembleur Final
Fusion intelligente des 4 sections d'analyse en rapport final enrichi
"""

import os
import sys
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PolcoFinalAssembler:
    """Assembleur final pour créer le rapport complet."""
    
    def __init__(self):
        """Initialise l'assembleur."""
        pass
    
    def calculate_total_analysis_metrics(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule les métriques globales de l'analyse."""
        
        metrics = {
            'total_sections': len(sections),
            'total_generation_time': 0,
            'total_input_length': 0,
            'total_output_length': 0,
            'sections_summary': {},
            'processing_timestamp': datetime.now().isoformat()
        }
        
        for section in sections:
            section_name = section.get('section', 'UNKNOWN')
            metrics['total_generation_time'] += section.get('generation_time', 0)
            metrics['total_input_length'] += section.get('input_length', 0)
            metrics['total_output_length'] += section.get('output_length', 0)
            
            metrics['sections_summary'][section_name] = {
                'output_length': section.get('output_length', 0),
                'generation_time': section.get('generation_time', 0),
                'timestamp': section.get('timestamp', 'N/A')
            }
        
        return metrics
    
    def create_executive_summary(self, store_id: str, sections: List[Dict[str, Any]], 
                                complete_data: Dict[str, Any]) -> str:
        """Crée un résumé exécutif basé sur les 4 sections."""
        
        # Extraire quelques métriques clés pour le résumé
        data_sources = complete_data.get('data_sources', {})
        internal_data = data_sources.get('internal_data', {})
        csv_files = internal_data.get('csv_files', {})
        
        # Données clés
        ca_par_m2_data = csv_files.get('ca_instore_par_m2', {}).get('data', [])
        ca_par_m2 = ca_par_m2_data[0].get('revenue_per_square_meter', 'N/A') if ca_par_m2_data else 'N/A'
        
        classement_data = csv_files.get('classement_national_du_magasin_par_gmv', {}).get('data', [])
        rang_national = classement_data[0].get('national_rank', 'N/A') if classement_data else 'N/A'
        
        surface_data = csv_files.get('surface_de_vente', {}).get('data', [])
        surface = surface_data[0].get('surface_m2', 'N/A') if surface_data else 'N/A'
        
        ca_sports = csv_files.get('ca_par_sport', {}).get('data', [])
        top_sport = ca_sports[0].get('sport_department_label', 'N/A') if ca_sports else 'N/A'
        
        summary = f"""
# RÉSUMÉ EXÉCUTIF - ANALYSE POLCO 3.0

## Magasin Decathlon {store_id}

### 📊 **Métriques Clés**
- **Surface commerciale** : {surface} m²
- **CA/m²** : {ca_par_m2}€
- **Rang national** : {rang_national}
- **Sport leader** : {top_sport}

### 🎯 **Synthèse des 5 Analyses Sectorielles**

Cette analyse POLCO 3.0 présente une approche révolutionnaire avec **5 processeurs spécialisés** qui ont analysé en profondeur :

1. **🌍 CONTEXTE** : Positionnement stratégique et environnement concurrentiel
2. **👥 CIBLES** : Segmentation client et comportements d'achat détaillés  
3. **📈 POTENTIEL** : Performance quantitative et projections de croissance
4. **🛍️ OFFRE** : Stratégie produits et plans d'action opérationnels
5. **🎯 ACTIONS** : Propositions d'actions à challenger par vos équipes

### 🔍 **Points Saillants Identifiés**

*Les points ci-dessous seront extraits automatiquement des 5 sections d'analyse lors de l'implémentation complète.*

### 🚀 **Recommandations Prioritaires**

*Les recommandations transversales seront synthétisées à partir des 5 processeurs spécialisés.*

---
"""
        return summary
    
    def create_methodology_section(self, metrics: Dict[str, Any]) -> str:
        """Crée la section méthodologie."""
        
        methodology = f"""
---

## 🔬 MÉTHODOLOGIE POLCO ANALYZER 3.0

### 🏗️ **Architecture Sectorielle Innovante**

Cette analyse a été produite par le système **POLCO ANALYZER 3.0**, première solution d'analyse retail utilisant une architecture à **processeurs spécialisés** :

```
┌─────────────────────────────────────────────────┐
│ 📊 POLCO ANALYZER 3.0 - Pipeline Sectorielle   │
├─────────────────────────────────────────────────┤
│ 1️⃣ PROCESSEUR CONTEXTE                         │
│    • polcoFR.txt + données démographiques      │
│    • Zone de chalandise + SWOT approfondi      │
├─────────────────────────────────────────────────┤
│ 2️⃣ PROCESSEUR CIBLES                           │
│    • 27 fichiers CSV clients analysés          │
│    • Segmentation comportementale avancée      │
├─────────────────────────────────────────────────┤
│ 3️⃣ PROCESSEUR POTENTIEL                        │
│    • Métriques performance + projections       │
│    • Analyses quantitatives poussées           │
├─────────────────────────────────────────────────┤
│ 4️⃣ PROCESSEUR OFFRE                            │
│    • Classification stratégique des sports     │
│    • Plans d'action opérationnels détaillés    │
├─────────────────────────────────────────────────┤
│ 📊 GÉNÉRATEUR GRAPHIQUES                        │
│    • 5+ visualisations automatiques            │
├─────────────────────────────────────────────────┤
│ 🔧 ASSEMBLEUR FINAL                             │
│    • Fusion intelligente + synthèse            │
└─────────────────────────────────────────────────┘
```

### 📈 **Métriques de Traitement**

- **Sections générées** : {metrics['total_sections']}
- **Temps total d'analyse** : {metrics['total_generation_time']:.1f} secondes
- **Données en entrée** : {metrics['total_input_length']:,} caractères
- **Analyse produite** : {metrics['total_output_length']:,} caractères
- **Ratio d'exploitation** : {(metrics['total_output_length'] / max(metrics['total_input_length'], 1) * 100):.1f}%

### 🎯 **Performance par Processeur**

"""
        
        for section_name, section_metrics in metrics['sections_summary'].items():
            methodology += f"""
**{section_name}** :
- Analyse générée : {section_metrics['output_length']:,} caractères
- Temps de traitement : {section_metrics['generation_time']:.1f}s
- Efficacité : {(section_metrics['output_length'] / max(section_metrics['generation_time'], 0.1)):.0f} caractères/seconde
"""
        
        methodology += f"""

### 🔧 **Technologies Utilisées**

- **IA Générative** : Google Gemini 2.5 Pro
- **Données** : 27+ fichiers CSV + synthèse magasin + polcoFR.txt + captation externe
- **Visualisations** : Matplotlib + Seaborn (génération automatique)
- **Architecture** : Processeurs parallélisables pour analyses sectorielles

### ✅ **Garanties Qualité**

- ✅ **Données réelles** : Exploitation de 100% des données disponibles
- ✅ **Prompts spécialisés** : 4 prompts experts de 4000+ mots chacun
- ✅ **Analyses approfondies** : Minimum 3500 mots par section
- ✅ **Visualisations** : Graphiques automatiques intégrés
- ✅ **Recommandations actionnables** : Plans d'action avec budgets et ROI

---
"""
        return methodology
    
    def fix_section_numbering(self, content: str, chapter_number: int, section_name: str) -> str:
        """Corrige la numérotation des sections pour assurer l'ordre logique."""
        
        # Mapping des chapitres
        chapter_titles = {
            1: "I. CONTEXTE GÉNÉRAL ET LOCAL",
            2: "II. À QUI VENDRE (CIBLES CLIENTS)", 
            3: "III. COMBIEN VENDRE (POTENTIEL DE MARCHÉ)",
            4: "IV. QUOI VENDRE (OFFRE PRODUIT ET SPORTIVE)",
            5: "V. PROPOSITIONS D'ACTIONS À CHALLENGER PAR VOS ÉQUIPES"
        }
        
        # Patterns de remplacement pour corriger la numérotation
        wrong_patterns = [
            r"^##?\s*(I{1,4}|[1-4])\.\s*.*$",  # Titles mal numérotés
            r"^##?\s*II\.\s*À QUI VENDRE.*$",
            r"^##?\s*III\.\s*COMBIEN VENDRE.*$", 
            r"^##?\s*IV\.\s*QUOI VENDRE.*$",
            r"^##?\s*I\.\s*CONTEXTE.*$"
        ]
        
        # Correction spécifique par section
        if section_name == "CONTEXTE":
            # Remplacer toute variation de titre par le bon
            content = re.sub(
                r'^##?\s*(I{1,4}|[1-4])\.\s*CONTEXTE.*$',
                f'## {chapter_titles[1]}',
                content,
                flags=re.MULTILINE | re.IGNORECASE
            )
        elif section_name == "CIBLES":
            content = re.sub(
                r'^##?\s*(I{1,4}|[1-4])\.\s*À QUI VENDRE.*$',
                f'## {chapter_titles[2]}',
                content,
                flags=re.MULTILINE | re.IGNORECASE
            )
        elif section_name == "POTENTIEL":
            content = re.sub(
                r'^##?\s*(I{1,4}|[1-4])\.\s*COMBIEN VENDRE.*$',
                f'## {chapter_titles[3]}',
                content,
                flags=re.MULTILINE | re.IGNORECASE
            )
        elif section_name == "OFFRE":
            content = re.sub(
                r'^##?\s*(I{1,4}|[1-4])\.\s*QUOI VENDRE.*$',
                f'## {chapter_titles[4]}',
                content,
                flags=re.MULTILINE | re.IGNORECASE
            )
        elif section_name == "ACTIONS":
            content = re.sub(
                r'^##?\s*(I{1,5}|[1-5])\.\s*PROPOSITIONS.*$',
                f'## {chapter_titles[5]}',
                content,
                flags=re.MULTILINE | re.IGNORECASE
            )
        
        return content
    
    def clean_section_content(self, content: str, section_name: str) -> str:
        """Nettoie le contenu des sections en supprimant les recommandations et éléments indésirables."""
        import re
        
        # Supprimer les sections de recommandations des parties I à IV
        if section_name in ['CONTEXTE', 'CIBLES', 'POTENTIEL', 'OFFRE']:
            # Supprimer les sections avec "Recommandations"
            content = re.sub(
                r'###?\s*\d*\.?\d*\s*[Rr]ecommandations?.*?(?=###?|\Z)',
                '',
                content,
                flags=re.DOTALL | re.IGNORECASE
            )
            
            # Supprimer les sections "Plan d'action"
            content = re.sub(
                r'###?\s*\d*\.?\d*\s*Plan d\'action.*?(?=###?|\Z)',
                '',
                content,
                flags=re.DOTALL | re.IGNORECASE
            )
            
            # Supprimer les sections "Actions" ou "Propositions"
            content = re.sub(
                r'###?\s*\d*\.?\d*\s*[Aa]ctions?.*?(?=###?|\Z)',
                '',
                content,
                flags=re.DOTALL | re.IGNORECASE
            )
            
            content = re.sub(
                r'###?\s*\d*\.?\d*\s*[Pp]ropositions?.*?(?=###?|\Z)',
                '',
                content,
                flags=re.DOTALL | re.IGNORECASE
            )
        
        # Nettoyer les lignes vides multiples
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content.strip()
    
    def assemble_final_report(self, store_id: str, sections: List[Dict[str, Any]], 
                             complete_data: Dict[str, Any], 
                             chart_integration: str = "") -> Dict[str, Any]:
        """Assemble le rapport final complet."""
        
        logger.info(f"🔧 Assemblage rapport final magasin {store_id}")
        
        # Calculer les métriques
        metrics = self.calculate_total_analysis_metrics(sections)
        
        # Créer les sections du rapport
        executive_summary = self.create_executive_summary(store_id, sections, complete_data)
        methodology = self.create_methodology_section(metrics)
        
        # Assembler le contenu principal dans l'ordre logique
        section_order = ['CONTEXTE', 'CIBLES', 'POTENTIEL', 'OFFRE', 'ACTIONS']
        main_content = ""
        
        # Créer un dictionnaire pour accès rapide
        sections_dict = {section.get('section', ''): section for section in sections}
        
        for i, section_name in enumerate(section_order, 1):
            if section_name in sections_dict:
                section = sections_dict[section_name]
                section_content = section.get('content', '')
                
                # S'assurer que la numérotation est correcte
                if section_content:
                    # Nettoyer le contenu (supprimer les recommandations des sections I-IV)
                    cleaned_content = self.clean_section_content(section_content, section_name)
                    
                    # Remplacer les numérotations incorrectes par la bonne
                    section_content = self.fix_section_numbering(cleaned_content, i, section_name)
                    
                    main_content += f"""

---

{section_content}

"""
            else:
                logger.warning(f"⚠️ Section {section_name} manquante dans l'analyse")
        
        # Ajouter les sections non prévues à la fin
        processed_sections = set(section_order)
        for section in sections:
            section_name = section.get('section', '')
            if section_name not in processed_sections and section_name:
                section_content = section.get('content', '')
                main_content += f"""

---

### Section Additionnelle: {section_name}

{section_content}

"""
        
        # Intégrer les graphiques si disponibles
        graphics_section = ""
        if chart_integration:
            graphics_section = chart_integration
        
        # Assembler le rapport complet (sans partie technique/méthodologie)
        final_report_content = f"""{executive_summary}

{main_content}

{graphics_section}
"""
        
        # Préparer le résultat final
        final_report = {
            'store_id': store_id,
            'report_content': final_report_content,
            'metrics': metrics,
            'sections_processed': [s.get('section') for s in sections],
            'total_length': len(final_report_content),
            'generation_timestamp': datetime.now().isoformat(),
            'analyzer_version': '3.0_sectorial'
        }
        
        logger.info(f"✅ Rapport final assemblé: {len(final_report_content):,} caractères")
        logger.info(f"📊 Sections intégrées: {', '.join(final_report['sections_processed'])}")
        
        return final_report
    
    def save_final_report_to_firestore(self, final_report: Dict[str, Any], 
                                      db, collection_name: str = "polco_analyzer_3_0") -> bool:
        """Sauvegarde le rapport final dans Firestore."""
        
        try:
            store_id = final_report['store_id']
            doc_ref = db.collection(collection_name).document(f"analyzer_3_0_{store_id}")
            doc_ref.set(final_report)
            
            logger.info(f"✅ Rapport final sauvegardé: analyzer_3_0_{store_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde rapport final: {e}")
            return False


def main():
    """Test de l'assembleur final."""
    pass


if __name__ == "__main__":
    main()
