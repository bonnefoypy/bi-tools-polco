#!/usr/bin/env python3
"""
POLCO ANALYZER 3.0 - Orchestrateur Principal
Système d'analyse retail avec architecture sectorielle
Coordonne les 4 processeurs spécialisés + graphiques + assembleur final
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# Configuration
PROJECT_ID = "polcoaigeneration-ved6"
DATA_COLLECTION = "polco_magasins_data"
RESULT_COLLECTION = "polco_analyzer_3_0"

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polco_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PolcoAnalyzer30:
    """Orchestrateur principal POLCO ANALYZER 3.0."""
    
    def __init__(self, captation_collection="polco_magasins_captation"):
        """Initialise l'orchestrateur."""
        self.project_id = PROJECT_ID
        self.data_collection = DATA_COLLECTION
        self.result_collection = RESULT_COLLECTION
        self.captation_collection = captation_collection
        self.db = None
        self.stats = {
            'total_stores': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'start_time': None,
            'processing_details': {},
            'errors': []
        }
        
        logger.info("🚀 Initialisation POLCO ANALYZER 3.0")
    
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
    
    def check_dependencies(self) -> bool:
        """Vérifie que tous les modules sont disponibles."""
        try:
            # Vérifier les processeurs spécialisés
            from polco_contexte_processor import PolcoContexteProcessorV3
            from polco_cibles_processor import PolcoCiblesProcessorV3
            from polco_potentiel_processor import PolcoPotentielProcessorV3
            from polco_offre_processor import PolcoOffreProcessorV3
            from polco_actions_processor import PolcoActionsProcessorV3
            from polco_graphics_generator import PolcoGraphicsGenerator
            from polco_final_assembler import PolcoFinalAssembler
            
            logger.info("✅ Tous les modules POLCO 3.0 v3 disponibles (5 processeurs + graphiques + assembleur)")
            return True
        except ImportError as e:
            logger.error(f"❌ Module manquant: {e}")
            return False
    
    def get_stores_data(self) -> List[Dict[str, Any]]:
        """Récupère les données des magasins depuis Firestore."""
        try:
            docs = self.db.collection(self.data_collection).stream()
            stores_data = []
            
            for doc in docs:
                store_data = doc.to_dict()
                stores_data.append(store_data)
            
            self.stats['total_stores'] = len(stores_data)
            logger.info(f"✅ {self.stats['total_stores']} magasins récupérés depuis {self.data_collection}")
            
            return stores_data
        except Exception as e:
            logger.error(f"❌ Erreur récupération données magasins: {e}")
            return []
    
    def check_existing_analysis(self, store_id: str) -> Optional[Dict[str, Any]]:
        """Vérifie si une analyse POLCO 3.0 existe déjà pour ce magasin."""
        try:
            doc_ref = self.db.collection(self.result_collection).document(f"analyzer_3_0_{store_id}")
            doc = doc_ref.get()
            
            if doc.exists:
                existing_data = doc.to_dict()
                # Vérifier que l'analyse est complète (5 sections)
                sections = existing_data.get('sections_processed', [])
                if len(sections) >= 5:
                    logger.info(f"♻️ [{store_id}] Analyse existante trouvée ({len(sections)} sections)")
                    return existing_data
                else:
                    logger.info(f"⚠️ [{store_id}] Analyse incomplète trouvée ({len(sections)}/5), regénération nécessaire")
                    return None
            else:
                logger.info(f"🆕 [{store_id}] Nouvelle analyse requise")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ [{store_id}] Erreur vérification existant: {e}")
            return None

    def detect_country_and_language(self, store_name: str, max_retries: int = 3) -> tuple:
        """Détecte le pays et la langue via LLM avec une logique de tentatives multiples."""
        import re
        import time
        try:
            # 1. Préparation du prompt
            city_match = re.search(r'(?:DECATHLON\s+)?(.+?)(?:\s+\d+)?$', store_name.strip(), re.IGNORECASE)
            city_name = city_match.group(1).strip() if city_match else store_name.strip()
            
            detection_prompt = f"""Dans quel pays est située le decathlon de  "{city_name}", et quelle langue officielle principale y est utilisée?

Réponds UNIQUEMENT sous ce format exact:
PAYS: [Nom du pays en français]
LANGUE: [Langue principale]

Exemples:
- Pour "Forbach": PAYS: France, LANGUE: Français  
- Pour "München": PAYS: Allemagne, LANGUE: Deutsch
- Pour "Barcelona": PAYS: Espagne, LANGUE: Español
- Pour "Milano": PAYS: Italie, LANGUE: Italiano"""
            logger.info(f"response: {detection_prompt}")
            # 2. Boucle de tentatives
            for attempt in range(max_retries):
                try:
                    # Initialiser le modèle si nécessaire
                    if not hasattr(self, 'model') or self.model is None:
                        from vertexai.generative_models import GenerativeModel
                        self.model = GenerativeModel("gemini-2.5-flash-lite")
                    
                    # Appel simple au modèle
                    response = self.model.generate_content(detection_prompt)
                    result = response.text.strip() if response.text else ""

                    logger.error(f"response: {result}")

                    # 3. Validation de la réponse
                    if result:
                        country_match = re.search(r'PAYS:\s*([^,\n]+)', result, re.IGNORECASE)
                        language_match = re.search(r'LANGUE:\s*([^,\n]+)', result, re.IGNORECASE)
                        
                        if country_match and language_match:
                            country = country_match.group(1).strip()
                            language = language_match.group(1).strip()
                            logger.info(f"🌍 Détection LLM réussie: {city_name} -> {country}, {language}")
                            return country, language
                    
                    logger.warning(f"⚠️ Réponse invalide ou mal formatée pour {store_name} (tentative {attempt + 1}/{max_retries})")

                except Exception as e:
                    logger.error(f"❌ Erreur détection LLM pour {store_name} (tentative {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        logger.info(f"⏳ Attente {wait_time}s avant nouvelle tentative...")
                        time.sleep(wait_time)
            
            logger.error(f"❌ Échec définitif de la détection pour {store_name} après {max_retries} tentatives.")

        except Exception as e:
            logger.error(f"❌ Erreur critique dans detect_country_and_language pour {store_name}: {e}")

        # 4. Fallback par défaut si toutes les tentatives échouent
        logger.info(f"🌍 Fallback par défaut pour {store_name}: France, Français")
        return 'France', 'Français'

    def process_single_store(self, store_data: Dict[str, Any], force_regenerate: bool = False) -> Optional[Dict[str, Any]]:
        """Traite un magasin avec les 4 processeurs + graphiques + assemblage."""
        
        store_id = store_data.get('store_id', 'unknown')
        store_name = store_data.get('store_name', f'Store_{store_id}')
        force_regenerate = True
        try:
            # Vérifier si l'analyse existe déjà (sauf si force)
            if not force_regenerate:
                existing_analysis = self.check_existing_analysis(store_id)
                if existing_analysis:
                    logger.info(f"✅ [{store_id}] Utilisation analyse existante")
                    return existing_analysis
            
            logger.info(f"🏪 [{store_id}] Démarrage analyse complète POLCO 3.0")
            start_time = datetime.now()
            
            # NOUVELLE LIGNE: Détection centralisée du pays et de la langue
            country, language = self.detect_country_and_language(store_name)
            
            # Importer les processeurs spécialisés
            from polco_contexte_processor import PolcoContexteProcessorV3
            from polco_cibles_processor import PolcoCiblesProcessorV3
            from polco_potentiel_processor import PolcoPotentielProcessorV3
            from polco_offre_processor import PolcoOffreProcessorV3
            from polco_actions_processor import PolcoActionsProcessorV3
            from polco_graphics_generator import PolcoGraphicsGenerator
            from polco_final_assembler import PolcoFinalAssembler
            
            # Initialiser les processeurs v3 avec la collection de captation configurée
            contexte_processor = PolcoContexteProcessorV3(self.captation_collection)
            cibles_processor = PolcoCiblesProcessorV3(self.captation_collection)
            potentiel_processor = PolcoPotentielProcessorV3(self.captation_collection)
            offre_processor = PolcoOffreProcessorV3(self.captation_collection)
            actions_processor = PolcoActionsProcessorV3(self.captation_collection)
            graphics_generator = PolcoGraphicsGenerator()
            final_assembler = PolcoFinalAssembler()
            
            sections_results = []
            
            # 1. PROCESSEUR CONTEXTE v2
            logger.info(f"🎯 [{store_id}] Analyse CONTEXTE...")
            contexte_result = contexte_processor.process_store(store_data, country, language)
            if contexte_result:
                sections_results.append(contexte_result)
                logger.info(f"✅ [{store_id}] Contexte terminé ({contexte_result['metadata']['output_length']} chars)")
            else:
                logger.error(f"❌ [{store_id}] Échec processeur CONTEXTE")
            
            # 2. PROCESSEUR CIBLES v2
            logger.info(f"👥 [{store_id}] Analyse CIBLES...")
            cibles_result = cibles_processor.process_store(store_data, country, language)
            if cibles_result:
                sections_results.append(cibles_result)
                logger.info(f"✅ [{store_id}] Cibles terminé ({cibles_result['metadata']['output_length']} chars)")
            else:
                logger.error(f"❌ [{store_id}] Échec processeur CIBLES")
            
            # 3. PROCESSEUR POTENTIEL v2
            logger.info(f"📈 [{store_id}] Analyse POTENTIEL...")
            potentiel_result = potentiel_processor.process_store(store_data, country, language)
            if potentiel_result:
                sections_results.append(potentiel_result)
                logger.info(f"✅ [{store_id}] Potentiel terminé ({potentiel_result['metadata']['output_length']} chars)")
            else:
                logger.error(f"❌ [{store_id}] Échec processeur POTENTIEL")
            
            # 4. PROCESSEUR OFFRE v3
            logger.info(f"🛍️ [{store_id}] Analyse OFFRE...")
            offre_result = offre_processor.process_store(store_data, country, language)
            if offre_result:
                sections_results.append(offre_result)
                logger.info(f"✅ [{store_id}] Offre terminé ({offre_result['metadata']['output_length']} chars)")
            else:
                logger.error(f"❌ [{store_id}] Échec processeur OFFRE")
            
            # 5. PROCESSEUR ACTIONS v3 (Propositions d'actions basées sur les 4 analyses)
            logger.info(f"🎯 [{store_id}] Génération PROPOSITIONS D'ACTIONS...")
            actions_result = actions_processor.process_store(store_data, sections_results, country, language)
            if actions_result:
                sections_results.append(actions_result)
                logger.info(f"✅ [{store_id}] Actions terminé ({actions_result['metadata']['output_length']} chars)")
            else:
                logger.error(f"❌ [{store_id}] Échec processeur ACTIONS")
            
            # Vérifier qu'on a au moins une section
            if not sections_results:
                logger.error(f"❌ [{store_id}] Aucune section générée")
                return None
            
            # 6. GÉNÉRATEUR DE GRAPHIQUES
            logger.info(f"📊 [{store_id}] Génération graphiques...")
            chart_filenames = graphics_generator.create_performance_dashboard(store_data, store_id)
            chart_integration = graphics_generator.generate_chart_markdown_integration(chart_filenames)
            
            if chart_filenames:
                logger.info(f"✅ [{store_id}] {len(chart_filenames)} graphiques générés")
            else:
                logger.warning(f"⚠️ [{store_id}] Aucun graphique généré")
            
            # 6. ASSEMBLEUR FINAL
            logger.info(f"🔧 [{store_id}] Assemblage rapport final...")
            final_report = final_assembler.assemble_final_report(
                store_id, sections_results, store_data, chart_integration
            )
            
            # 7. SAUVEGARDE FIRESTORE
            logger.info(f"💾 [{store_id}] Sauvegarde Firestore...")
            saved = final_assembler.save_final_report_to_firestore(
                final_report, self.db, self.result_collection
            )
            
            if saved:
                total_time = (datetime.now() - start_time).total_seconds()
                
                # Statistiques de traitement
                processing_stats = {
                    'sections_completed': len(sections_results),
                    'total_output_length': final_report['total_length'],
                    'charts_generated': len(chart_filenames),
                    'processing_time': total_time,
                    'sections_list': [s['section'] for s in sections_results]
                }
                
                self.stats['processing_details'][store_id] = processing_stats
                
                logger.info(f"🎉 [{store_id}] Analyse POLCO 3.0 terminée !")
                logger.info(f"📊 [{store_id}] Stats: {len(sections_results)} sections, "
                           f"{final_report['total_length']:,} chars, {total_time:.1f}s")
                
                return final_report
            else:
                logger.error(f"❌ [{store_id}] Échec sauvegarde")
                return None
                
        except Exception as e:
            logger.error(f"❌ [{store_id}] Erreur analyse complète: {e}")
            self.stats['errors'].append(f"{store_id}: {str(e)}")
            return None
    
    def process_all_stores(self, limit: Optional[int] = None, target_store: Optional[str] = None) -> bool:
        """Traite tous les magasins avec POLCO 3.0."""
        
        # Récupérer les données
        stores_data = self.get_stores_data()
        
        if not stores_data:
            logger.error("❌ Aucune donnée magasin disponible")
            return False
        
        # Filtrer par store spécifique si demandé
        if target_store:
            stores_data = [s for s in stores_data if s.get('store_id') == target_store]
            if not stores_data:
                logger.error(f"❌ Store {target_store} non trouvé")
                return False
            logger.info(f"🎯 Mode test: traitement du store {target_store} uniquement")
        # Limiter le nombre si demandé (pour tests génériques)
        elif limit:
            stores_data = stores_data[:limit]
            logger.info(f"🔬 Mode test: traitement de {limit} magasins seulement")
        
        # Traiter chaque magasin
        for i, store_data in enumerate(stores_data, 1):
            store_id = store_data.get('store_id', f'store_{i}')
            
            logger.info(f"🏪 [{i}/{len(stores_data)}] Traitement magasin {store_id}")
            
            result = self.process_single_store(store_data, force_regenerate=getattr(self, 'force_regenerate', False))
            
            if result:
                self.stats['successful_analyses'] += 1
            else:
                self.stats['failed_analyses'] += 1
        
        return True
    
    def run(self, test_mode: bool = False, test_limit: int = 1, target_store: Optional[str] = None) -> bool:
        """Lance POLCO ANALYZER 3.0."""
        
        self.stats['start_time'] = datetime.now()
        
        logger.info("=" * 80)
        logger.info("🚀 POLCO ANALYZER 3.0 - SYSTÈME D'ANALYSE SECTORIELLE")
        logger.info("📊 Architecture: 4 Processeurs + Graphiques + Assembleur")
        logger.info("=" * 80)
        
        # Vérifications
        if not self.check_credentials():
            return False
        
        if not self.init_firestore():
            return False
        
        if not self.check_dependencies():
            return False
        
        # Traitement
        if target_store:
            success = self.process_all_stores(target_store=target_store)
        else:
            limit = test_limit if test_mode else None
            success = self.process_all_stores(limit)
        
        # Résumé final
        self.print_final_summary()
        
        return success and self.stats['successful_analyses'] > 0
    
    def print_final_summary(self):
        """Affiche le résumé final."""
        
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        logger.info("\\n" + "=" * 80)
        logger.info("📊 POLCO ANALYZER 3.0 - RÉSUMÉ FINAL")
        logger.info("=" * 80)
        
        logger.info(f"⏱️ Durée totale: {duration:.1f} secondes")
        logger.info(f"🏪 Magasins traités: {self.stats['total_stores']}")
        logger.info(f"✅ Analyses réussies: {self.stats['successful_analyses']}")
        logger.info(f"❌ Analyses échouées: {self.stats['failed_analyses']}")
        logger.info(f"🗄️ Collection résultats: {self.result_collection}")
        
        if self.stats['processing_details']:
            logger.info("\\n📈 Détails des analyses réussies:")
            for store_id, details in self.stats['processing_details'].items():
                logger.info(f"   🏪 {store_id}:")
                logger.info(f"      • {details['sections_completed']} sections: {', '.join(details['sections_list'])}")
                logger.info(f"      • {details['total_output_length']:,} caractères générés")
                logger.info(f"      • {details['charts_generated']} graphiques")
                logger.info(f"      • {details['processing_time']:.1f}s de traitement")
        
        if self.stats['errors']:
            logger.warning(f"\\n⚠️ {len(self.stats['errors'])} erreurs détectées:")
            for error in self.stats['errors']:
                logger.warning(f"   • {error}")
        
        if self.stats['successful_analyses'] > 0:
            logger.info("\\n🎉 POLCO ANALYZER 3.0 - Analyses sectorielles terminées avec succès !")
            logger.info("🔄 Consultez les rapports complets dans Firestore")
        else:
            logger.error("\\n❌ Aucune analyse complétée avec succès")


def main():
    """Point d'entrée principal."""
    try:
        import argparse
        parser = argparse.ArgumentParser(description='POLCO ANALYZER - Analyses sectorielles ultra-détaillées')
        parser.add_argument('--test', action='store_true', 
                          help='Mode test (traite seulement 1 magasin)')
        parser.add_argument('--limit', type=int, default=1,
                          help='Nombre de magasins à traiter en mode test')
        parser.add_argument('--force', action='store_true',
                          help='Force la regénération même si analyses existent')
        parser.add_argument('--store-id', type=str,
                          help='ID du magasin spécifique à traiter (ex: 42)')
        
        args = parser.parse_args()
        
        # Toujours utiliser captation (version simplifiée)
        analyzer = PolcoAnalyzer30("polco_magasins_captation")
        analyzer.force_regenerate = args.force
        
        # Utiliser --store-id
        target_store = getattr(args, 'store_id', None)
        success = analyzer.run(test_mode=args.test, test_limit=args.limit, target_store=target_store)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\\n⏹️ Analyse interrompue par l'utilisateur")
        return 1
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
