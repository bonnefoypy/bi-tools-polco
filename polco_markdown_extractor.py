#!/usr/bin/env python3
"""
POLCO 3.0 Markdown Extractor
Extracteur Markdown spécialisé pour les analyses POLCO ANALYZER 3.0
"""

import os
import sys
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import shutil

# Configuration
PROJECT_ID = "polcoaigeneration-ved6"
SOURCE_COLLECTION = "polco_analyzer_3_0"
OUTPUT_DIR = "reports_polco_3_0"
GRAPHICS_DIR = "analytics_charts"

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Polco30MarkdownExtractor:
    """Extracteur Markdown spécialisé pour POLCO ANALYZER 3.0."""
    
    def __init__(self):
        """Initialise l'extracteur."""
        self.project_id = PROJECT_ID
        self.source_collection = SOURCE_COLLECTION
        self.output_dir = OUTPUT_DIR
        self.graphics_dir = GRAPHICS_DIR
        self.db = None
        self.stats = {
            'total_analyses': 0,
            'extracted_reports': 0,
            'failed_extractions': 0,
            'start_time': None,
            'errors': []
        }
        
        logger.info("🚀 Initialisation extracteur POLCO 3.0 Markdown")
    
    def check_credentials(self) -> bool:
        """Vérifie les credentials."""
        if not os.path.exists("credentials.json"):
            logger.error("❌ Fichier credentials.json non trouvé")
            return False
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("credentials.json")
        logger.info("✅ Credentials configurés")
        return True
    
    def init_firestore(self) -> bool:
        """Initialise Firestore."""
        try:
            from google.cloud import firestore
            self.db = firestore.Client(project=self.project_id)
            logger.info("✅ Firestore initialisé")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation de Firestore: {e}")
            return False
    
    def prepare_output_directory(self) -> bool:
        """Prépare le dossier de sortie."""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Copier les graphiques si disponibles
            if os.path.exists(self.graphics_dir):
                target_graphics = os.path.join(self.output_dir, "graphics")
                if os.path.exists(target_graphics):
                    shutil.rmtree(target_graphics)
                shutil.copytree(self.graphics_dir, target_graphics)
                logger.info(f"✅ Graphiques copiés vers {target_graphics}")
            
            logger.info(f"✅ Dossier de sortie préparé: {self.output_dir}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur préparation dossier: {e}")
            return False
    
    def get_polco_3_0_analyses(self) -> List[Dict[str, Any]]:
        """Récupère toutes les analyses POLCO 3.0."""
        try:
            docs = self.db.collection(self.source_collection).stream()
            analyses = []
            
            for doc in docs:
                analysis_data = doc.to_dict()
                analyses.append(analysis_data)
            
            self.stats['total_analyses'] = len(analyses)
            logger.info(f"✅ {self.stats['total_analyses']} analyses POLCO 3.0 récupérées")
            
            return analyses
        except Exception as e:
            logger.error(f"❌ Erreur récupération analyses: {e}")
            return []
    
    def enhance_markdown_with_graphics(self, markdown_content: str, store_id: str) -> str:
        """Enrichit le Markdown avec les graphiques disponibles."""
        
        # Rechercher les graphiques pour ce magasin
        graphics_path = os.path.join(self.output_dir, "graphics")
        if not os.path.exists(graphics_path):
            return markdown_content
        
        graphics_files = []
        for filename in os.listdir(graphics_path):
            if filename.endswith('.png') and store_id in filename:
                graphics_files.append(filename)
        
        if not graphics_files:
            return markdown_content
        
        # Ajouter section graphiques améliorée
        graphics_section = """

---

## 📊 VISUALISATIONS POLCO 3.0

*Graphiques générés automatiquement par le système d'analyse sectorielle*

"""
        
        graphics_titles = {
            'top_sports_ca': '### 🏆 Performance des Sports par Chiffre d\'Affaires',
            'age_distribution': '### 👥 Pyramide des Âges de la Clientèle',
            'monthly_evolution': '### 📈 Évolution Mensuelle du CA',
            'brand_mix': '### 🏷️ Répartition du Mix Marques',
            'dvs_heatmap': '### ⚠️ Cartographie des Stocks (DVS)',
            'geo_competition_map': '### 🏪 Positionnement Concurrentiel',
            'geo_sports_infrastructure': '### 🏃 Infrastructures Sportives Locales',
            'geo_isochrone_zones': '### ⏰ Zones de Chalandise'
        }
        
        for graphics_file in sorted(graphics_files):
            # Identifier le type de graphique
            chart_type = None
            for key in graphics_titles.keys():
                if key in graphics_file:
                    chart_type = key
                    break
            
            if chart_type:
                title = graphics_titles[chart_type]
                graphics_section += f"""
{title}

![{title.replace('#', '').strip()}](./graphics/{graphics_file})

*Analyse automatique générée par POLCO ANALYZER 3.0*

"""
        
        # Insérer avant la section méthodologie
        methodology_marker = "## 🔬 MÉTHODOLOGIE POLCO ANALYZER 3.0"
        if methodology_marker in markdown_content:
            return markdown_content.replace(methodology_marker, graphics_section + methodology_marker)
        else:
            return markdown_content + graphics_section
    
    def fix_chapter_order(self, content: str) -> str:
        """Corrige l'ordre des chapitres dans le contenu (pour les anciennes analyses)."""
        
        # Patterns pour identifier les sections (plus robustes)  
        patterns = {
            'CONTEXTE': r'(##\s*\*?\*?[IVX]*\.?\s*CONTEXTE.*?)(?=\n##\s*[🔬📊]|\n##\s*\*?\*?[IVX]*\.|\Z)',
            'CIBLES': r'(##\s*\*?\*?[IVX]*\.?\s*(?:CIBLES|À QUI VENDRE).*?)(?=\n##\s*[🔬📊]|\n##\s*\*?\*?[IVX]*\.|\Z)',
            'POTENTIEL': r'(##\s*\*?\*?[IVX]*\.?\s*(?:POTENTIEL|COMBIEN VENDRE).*?)(?=\n##\s*[🔬📊]|\n##\s*\*?\*?[IVX]*\.|\Z)',
            'OFFRE': r'(##\s*\*?\*?[IVX]*\.?\s*(?:OFFRE|QUOI VENDRE).*?)(?=\n##\s*[🔬📊]|\n##\s*\*?\*?[IVX]*\.|\Z)',
            'ACTIONS': r'(##\s*\*?\*?[IVX]*\.?\s*(?:ACTIONS|PROPOSITIONS).*?)(?=\n##\s*[🔬📊]|\n##\s*\*?\*?[IVX]*\.|\Z)'
        }
        
        # Extraire les sections
        sections = {}
        remaining_content = content
        
        for section_name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches:
                sections[section_name] = matches[0]
                # Supprimer cette section du contenu restant
                remaining_content = re.sub(pattern, '', remaining_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Si on a trouvé des sections à réorganiser
        if len(sections) >= 2:
            logger.info(f"🔧 Réorganisation chapitres détectée: {list(sections.keys())}")
            
            # Reconstruire dans le bon ordre (5 sections maintenant)
            ordered_sections = ['CONTEXTE', 'CIBLES', 'POTENTIEL', 'OFFRE', 'ACTIONS']
            chapter_numbers = ['I', 'II', 'III', 'IV', 'V']
            
            # Garder le début (jusqu'au premier chapitre)
            header_match = re.search(r'(.*?)(?=##.*?(?:CONTEXTE|CIBLES|POTENTIEL|OFFRE|ACTIONS|PROPOSITIONS))', content, re.DOTALL | re.IGNORECASE)
            header_part = header_match.group(1) if header_match else ""
            
            # Reconstituer le contenu ordonné
            ordered_content = header_part
            
            for i, section_name in enumerate(ordered_sections):
                if section_name in sections:
                    section_content = sections[section_name]
                    
                    # Corriger la numérotation
                    section_content = re.sub(
                        r'^##\s*[IVX]+\.\s*(.*?)$',
                        f'## {chapter_numbers[i]}. \\1',
                        section_content,
                        flags=re.MULTILINE
                    )
                    
                    ordered_content += "\n\n---\n\n" + section_content
            
            # Ajouter le contenu restant (méthodologie, etc.)
            if remaining_content.strip():
                ordered_content += "\n\n" + remaining_content
            
            return ordered_content
        else:
            # Pas de réorganisation nécessaire
            return content
    
    def extract_single_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """Extrait une analyse POLCO 3.0 en Markdown."""
        
        try:
            store_id = analysis_data.get('store_id', 'unknown')
            report_content = analysis_data.get('report_content', '')
            
            if not report_content:
                logger.error(f"❌ [{store_id}] Contenu rapport vide")
                return False
            
            # Corriger l'ordre des chapitres si nécessaire
            corrected_content = self.fix_chapter_order(report_content)
            
            # Enrichir avec les graphiques
            enhanced_content = self.enhance_markdown_with_graphics(corrected_content, store_id)
            
            # Ajouter header POLCO 3.0
            header = f"""<!-- POLCO ANALYZER 3.0 - Analyse Sectorielle -->
<!-- Store ID: {store_id} -->
<!-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->

"""
            
            final_content = header + enhanced_content
            
            # Nom de fichier
            filename = f"POLCO_3_0_DECATHLON_{store_id}_Analyse_Sectorielle.md"
            filepath = os.path.join(self.output_dir, filename)
            
            # Sauvegarder
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            logger.info(f"✅ [{store_id}] Rapport extrait: {filename} ({len(final_content):,} chars)")
            return True
            
        except Exception as e:
            store_id = analysis_data.get('store_id', 'unknown')
            logger.error(f"❌ [{store_id}] Erreur extraction: {e}")
            return False
    
    def create_index_file(self, analyses: List[Dict[str, Any]]) -> bool:
        """Crée un fichier index des rapports POLCO 3.0."""
        
        try:
            index_content = f"""# INDEX - Analyses POLCO ANALYZER 3.0

*Analyses sectorielles approfondies générées le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*

---

## 🌟 À Propos de POLCO ANALYZER 3.0

**POLCO ANALYZER 3.0** représente une révolution dans l'analyse retail grâce à son **architecture sectorielle** :

- 🎯 **4 Processeurs spécialisés** : Contexte, Cibles, Potentiel, Offre
- 📊 **Analyses 5x plus détaillées** : 50k+ caractères vs 15k ancien système  
- 📈 **Visualisations automatiques** : Graphiques intégrés
- 🎯 **Plans d'action chiffrés** : ROI et budgets inclus

---

## 📋 Analyses Disponibles ({len(analyses)} magasins)

| Magasin | Fichier | Taille | Sections | Graphiques |
|---------|---------|---------|----------|------------|
"""
            
            for analysis in sorted(analyses, key=lambda x: x.get('store_id', '')):
                store_id = analysis.get('store_id', 'N/A')
                report_length = analysis.get('total_length', 0)
                sections = analysis.get('sections_processed', [])
                
                # Compter les graphiques pour ce magasin
                graphics_count = 0
                graphics_path = os.path.join(self.output_dir, "graphics")
                if os.path.exists(graphics_path):
                    graphics_count = len([f for f in os.listdir(graphics_path) 
                                        if f.endswith('.png') and store_id in f])
                
                filename = f"POLCO_3_0_DECATHLON_{store_id}_Analyse_Sectorielle.md"
                
                index_content += f"| **{store_id}** | [{filename}](./{filename}) | {report_length:,} chars | {len(sections)} sections | {graphics_count} graphiques |\n"
            
            index_content += f"""

---

## 📊 Statistiques Globales

- **Total analyses** : {len(analyses)} magasins
- **Sections générées** : {sum(len(a.get('sections_processed', [])) for a in analyses)} sections
- **Contenu total** : {sum(a.get('total_length', 0) for a in analyses):,} caractères
- **Graphiques** : {len([f for f in os.listdir(os.path.join(self.output_dir, 'graphics')) if f.endswith('.png')]) if os.path.exists(os.path.join(self.output_dir, 'graphics')) else 0} visualisations

---

## 🔧 Architecture Technique

```
┌─────────────────────────────────────────────────┐
│ 📊 POLCO ANALYZER 3.0 - Architecture           │
├─────────────────────────────────────────────────┤
│ 1️⃣ PROCESSEUR CONTEXTE                         │
│    • Analyse stratégique + SWOT                │
├─────────────────────────────────────────────────┤
│ 2️⃣ PROCESSEUR CIBLES                           │
│    • Segmentation + comportements              │
├─────────────────────────────────────────────────┤
│ 3️⃣ PROCESSEUR POTENTIEL                        │
│    • Métriques + projections                   │
├─────────────────────────────────────────────────┤
│ 4️⃣ PROCESSEUR OFFRE                            │
│    • Plans d'action + ROI                      │
├─────────────────────────────────────────────────┤
│ 📊 GÉNÉRATEUR GRAPHIQUES                        │
│    • Visualisations automatiques               │
├─────────────────────────────────────────────────┤
│ 🔧 ASSEMBLEUR FINAL                             │
│    • Fusion intelligente                       │
└─────────────────────────────────────────────────┘
```

---

*Système POLCO ANALYZER 3.0 - Analyses sectorielles nouvelle génération*
"""
            
            # Sauvegarder l'index
            index_filepath = os.path.join(self.output_dir, "INDEX.md")
            with open(index_filepath, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            logger.info(f"✅ Index créé: INDEX.md")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur création index: {e}")
            return False
    
    def run(self, store_id: Optional[str] = None) -> bool:
        """Lance l'extraction Markdown POLCO 3.0."""
        
        self.stats['start_time'] = datetime.now()
        
        logger.info("=" * 80)
        logger.info("📄 POLCO 3.0 MARKDOWN EXTRACTOR")
        if store_id:
            logger.info(f"🎯 Extraction magasin spécifique: {store_id}")
        else:
            logger.info("🌟 Extraction des analyses sectorielles")
        logger.info("=" * 80)
        
        # Vérifications
        if not self.check_credentials():
            return False
        
        if not self.init_firestore():
            return False
        
        if not self.prepare_output_directory():
            return False
        
        # Récupérer les analyses
        analyses = self.get_polco_3_0_analyses()
        
        if not analyses:
            logger.warning("⚠️ Aucune analyse POLCO 3.0 trouvée")
            logger.info("💡 Lancez d'abord POLCO ANALYZER 3.0")
            return False
        
        # Filtrer par store_id si spécifié
        if store_id:
            analyses = [a for a in analyses if a.get('store_id') == store_id]
            if not analyses:
                logger.error(f"❌ Aucune analyse POLCO 3.0 trouvée pour le magasin {store_id}")
                logger.info("📋 Magasins disponibles:")
                all_analyses = self.get_polco_3_0_analyses()
                for analysis in all_analyses:
                    logger.info(f"   • {analysis.get('store_id', 'N/A')}")
                return False
            logger.info(f"🎯 Extraction du magasin {store_id} uniquement")
        
        logger.info(f"✅ {len(analyses)} analyses POLCO 3.0 récupérées")
        
        # Extraire chaque analyse
        for i, analysis in enumerate(analyses, 1):
            analysis_store_id = analysis.get('store_id', f'store_{i}')
            logger.info(f"📄 [{i}/{len(analyses)}] Extraction {analysis_store_id}...")
            
            if self.extract_single_analysis(analysis):
                self.stats['extracted_reports'] += 1
            else:
                self.stats['failed_extractions'] += 1
        
        # Créer l'index
        self.create_index_file(analyses)
        
        # Résumé final
        self.print_final_summary()
        
        return self.stats['extracted_reports'] > 0
    
    def print_final_summary(self):
        """Affiche le résumé final."""
        
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        logger.info("\\n" + "=" * 80)
        logger.info("📊 POLCO 3.0 MARKDOWN EXTRACTOR - RÉSUMÉ")
        logger.info("=" * 80)
        
        logger.info(f"⏱️ Durée d'extraction: {duration:.1f} secondes")
        logger.info(f"📊 Analyses POLCO 3.0: {self.stats['total_analyses']}")
        logger.info(f"✅ Rapports extraits: {self.stats['extracted_reports']}")
        logger.info(f"❌ Échecs: {self.stats['failed_extractions']}")
        logger.info(f"📁 Dossier de sortie: {self.output_dir}/")
        
        if self.stats['extracted_reports'] > 0:
            logger.info("\\n📄 Fichiers générés:")
            logger.info(f"   • {self.stats['extracted_reports']} rapports .md")
            logger.info(f"   • 1 fichier INDEX.md")
            
            # Compter les graphiques
            graphics_path = os.path.join(self.output_dir, "graphics")
            if os.path.exists(graphics_path):
                graphics_count = len([f for f in os.listdir(graphics_path) if f.endswith('.png')])
                logger.info(f"   • {graphics_count} graphiques copiés")
            
            logger.info(f"\\n🔗 Consultation:")
            logger.info(f"   open {self.output_dir}/INDEX.md")
        else:
            logger.error("\\n❌ Aucun rapport extrait")


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='POLCO 3.0 Markdown Extractor')
    parser.add_argument('--store-id', type=str, help='Extraire uniquement le magasin avec cet ID')
    
    args = parser.parse_args()
    
    try:
        extractor = Polco30MarkdownExtractor()
        success = extractor.run(store_id=getattr(args, 'store_id', None))
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\\n⏹️ Extraction interrompue par l'utilisateur")
        return 1
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
