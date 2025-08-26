#!/usr/bin/env python3
"""
POLCO - Processeur de Captation avec Google Search Avancé
Utilise les prompts de captation pour obtenir un maximum de contexte local
Intègre des requêtes Google Search ciblées et multiples
"""

import os
import sys
import re
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import logging

# Configuration
PROJECT_ID = "polcoaigeneration-ved6"
REGION = "global"
MODEL_NAME = "gemini-2.5-flash"  # Modèle plus puissant pour analyses complexes
CSV_FILE = "polco_mag_test - Feuille 1.csv"
PROMPTS_FILE = "prompts/prompt_captation.md"

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polco_captation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PolcoCaptationProcessor:
    """Processeur POLCO de captation avec Google Search avancé."""
    
    def __init__(self):
        """Initialise le processeur de captation."""
        self.project_id = PROJECT_ID
        self.region = "us-central1"  # Région pour Vertex AI
        self.model_name = "gemini-2.5-flash"  # Modèle flash pour la captation
        self.prompts = []
        self.stores_df = None
        self.db = None
        self.llm_client = None  # Utilise la classe LLM standardisée
        self.stats = {
            'total_stores': 0,
            'processed_stores': 0,
            'successful_prompts': 0,
            'failed_prompts': 0,
            'start_time': None,
            'errors': []
        }
        
        logger.info("🚀 Initialisation du processeur POLCO Captation avec Google Search Avancé")
    
    def check_credentials(self) -> bool:
        """Vérifie les credentials."""
        if not os.path.exists("credentials.json"):
            logger.error("❌ Fichier credentials.json non trouvé")
            return False
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("credentials.json")
        logger.info("✅ Credentials configurés")
        return True
    
    def init_services(self) -> bool:
        """Initialise les services Google AI et Firestore."""
        try:
            # Initialiser Firestore d'abord
            from google.cloud import firestore
            self.db = firestore.Client(project=self.project_id)
            logger.info("✅ Firestore initialisé")
            
            # Initialiser le client LLM standardisé avec gemini-2.5-flash
            from polco_llm_client import get_llm_client
            self.llm_client = get_llm_client("gemini-2.5-flash")
            
            logger.info(f"✅ Client LLM standardisé initialisé avec {self.model_name} + Google Search")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation services: {e}")
            return False
    
    def load_prompts(self) -> bool:
        """Charge les 6 prompts de captation depuis le fichier."""
        try:
            if not os.path.exists(PROMPTS_FILE):
                logger.error(f"❌ Fichier {PROMPTS_FILE} non trouvé")
                return False
            
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extraire les 7 prompts avec regex améliorée
            prompt_pattern = r'\*\*Prompt (\d+)\s*:\s*([^*]+)\*\*(.*?)(?=\*\*Prompt \d+|---|\Z)'
            matches = re.findall(prompt_pattern, content, re.DOTALL)
            
            for match in matches:
                prompt_num, title, content = match
                self.prompts.append({
                    'number': int(prompt_num),
                    'title': title.strip(),
                    'content': content.strip()
                })
            
            if len(self.prompts) != 7:
                logger.error(f"❌ {len(self.prompts)} prompts trouvés, 7 attendus")
                return False
            
            logger.info(f"✅ {len(self.prompts)} prompts de captation chargés")
            for prompt in self.prompts:
                logger.info(f"   📋 Prompt {prompt['number']}: {prompt['title']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement prompts: {e}")
            return False
    
    def load_stores(self) -> bool:
        """Charge la liste des magasins depuis le CSV."""
        try:
            if not os.path.exists(CSV_FILE):
                logger.error(f"❌ Fichier {CSV_FILE} non trouvé")
                return False
            
            self.stores_df = pd.read_csv(CSV_FILE)
            self.stats['total_stores'] = len(self.stores_df)
            
            logger.info(f"✅ {self.stats['total_stores']} magasins chargés depuis {CSV_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement magasins: {e}")
            return False
    
    def detect_country_and_language(self, store_row, max_retries: int = 3) -> tuple:
        """Détecte le pays et la langue via LLM avec une logique de tentatives multiples."""
        try:
            # 1. Préparation du prompt avec les informations du CSV
            store_name = store_row.get('store_name', 'INCONNU')
            ville = store_row.get('ville', '')
            country_name = store_row.get('country_name', 'FRANCE')
            
            # Utiliser la ville du CSV si disponible, sinon extraire du nom
            if ville:
                city_name = ville
            else:
                city_match = re.search(r'(?:DECATHLON\s+)?(.+?)(?:\s+\d+)?$', store_name.strip(), re.IGNORECASE)
                city_name = city_match.group(1).strip() if city_match else store_name.strip()
            
            # Si le pays est déjà dans le CSV, l'utiliser directement
            if country_name and country_name != 'FRANCE':
                # Mapper les pays aux langues
                country_language_map = {
                    'FRANCE': 'Français',
                    'ALLEMAGNE': 'Deutsch',
                    'ROYAUME-UNI': 'English',
                    'ESPAGNE': 'Español',
                    'ITALIE': 'Italiano',
                    'BELGIQUE': 'Français',
                    'SUISSE': 'Deutsch',
                    'PAYS-BAS': 'Nederlands'
                }
                language = country_language_map.get(country_name, 'Français')
                logger.info(f"🌍 Utilisation pays CSV: {country_name}, {language}")
                return country_name, language
            
            detection_prompt = f"""Dans quel pays est située la ville "{city_name}", et quelle langue officielle principale y est utilisée?

Réponds UNIQUEMENT sous ce format exact:
PAYS: [Nom du pays en français]
LANGUE: [Langue principale]

Exemples:
- Pour "Forbach": PAYS: France, LANGUE: Français  
- Pour "München": PAYS: Allemagne, LANGUE: Deutsch
- Pour "Barcelona": PAYS: Espagne, LANGUE: Español
- Pour "Milano": PAYS: Italie, LANGUE: Italiano"""

            # 2. Boucle de tentatives avec le client LLM standardisé
            for attempt in range(max_retries):
                try:
                    # Utiliser le client LLM standardisé avec Google Search
                    result = self.llm_client.generate_with_search(
                        prompt=detection_prompt,
                        max_retries=3,
                        temperature=0.1,
                        max_tokens=150
                    )

                    # 3. Validation de la réponse (logique adaptée à cette fonction)
                    if result:
                        country_match = re.search(r'PAYS:\s*([^,\n]+)', result, re.IGNORECASE)
                        language_match = re.search(r'LANGUE:\s*([^,\n]+)', result, re.IGNORECASE)
                        
                        if country_match and language_match:
                            country = country_match.group(1).strip()
                            language = language_match.group(1).strip()
                            logger.info(f"🌍 Détection LLM réussie: {city_name} -> {country}, {language}")
                            return country, language # Succès, on quitte la fonction
                    
                    logger.warning(f"⚠️ Réponse invalide ou mal formatée pour {store_name} (tentative {attempt + 1}/{max_retries})")

                except Exception as e:
                    logger.error(f"❌ Erreur détection LLM pour {store_name} (tentative {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5 # Attente plus courte pour cette fonction rapide
                        logger.info(f"⏳ Attente {wait_time}s avant nouvelle tentative...")
                        time.sleep(wait_time)
            
            logger.error(f"❌ Échec définitif de la détection pour {store_name} après {max_retries} tentatives.")

        except Exception as e:
            # Gère les erreurs en amont de la boucle (ex: préparation du prompt)
            logger.error(f"❌ Erreur critique dans detect_country_and_language pour {store_name}: {e}")

        # 4. Fallback par défaut si toutes les tentatives échouent
        logger.info(f"🌍 Fallback par défaut pour {store_name}: France, Français")
        return 'France', 'Français'

    def create_search_context(self, store_row) -> str:
        """Crée un contexte de recherche ciblé pour Google Search avec localisation linguistique."""
        store_name = store_row.get('store_name', 'INCONNU')
        
        # Détecter le pays et la langue
        country, language = self.detect_country_and_language(store_row)
        
        context = f"""
🌍 **LOCALISATION LINGUISTIQUE OBLIGATOIRE :**
- RÉDIGER ENTIÈREMENT la réponse en {language}
- Adapter les références culturelles et contextuelles au pays {country}
- Utiliser les organismes statistiques locaux du pays

🕐 Fiabilité & Actualité (Protocole de Vérification Stricte) :
Période de validité : Toutes les informations doivent être valides pour 2024-2025.
Processus de validation OBLIGATOIRE pour chaque concurrent :
VÉRIFICATION N°1 (Source prioritaire) : Consulter le localisateur de magasins officiel de l'enseigne (ex: intersport.fr, sport2000.fr). Si le magasin n'y est pas listé, il est considéré comme FERMÉ.
VÉRIFICATION N°2 (Google Maps) : Vérifier le statut sur la fiche Google Maps. Rechercher la mention "Définitivement fermé". Analyser les dates des avis les plus récents. Une absence d'avis récents (< 6 mois) est un signal de fermeture probable.
VÉRIFICATION N°3 (Presse Locale) : En cas de doute, rechercher des articles de presse locale mentionnant une fermeture.
Mention d'incertitude : Si le statut ne peut être confirmé avec certitude via ces 3 étapes, marquer le concurrent comme ⚠️ À VÉRIFIER - STATUT INCERTAIN. Ne jamais affirmer qu'un magasin est ouvert sans preuve formelle issue de l'étape 1 ou 2.
Exclusion : Ne mentionner AUCUN magasin si sa fermeture est confirmée."
"""
        return context
    
    def create_multi_search_queries(self, store_row, prompt_number: int) -> List[str]:
        """Génère des requêtes Google Search spécialisées selon le prompt."""
        # Extraire les informations complètes du magasin
        store_name = store_row.get('store_name', 'INCONNU')
        ville = store_row.get('ville', '')
        codeCP = store_row.get('codeCP', '')
        adress = store_row.get('adress', '')
        country_name = store_row.get('country_name', 'FRANCE')
        
        # Créer l'identifiant complet du magasin
        store_identifier = f" {store_name} {adress} {codeCP} {ville} {country_name}"
        
        # Utiliser la ville comme référence principale pour les recherches
        city = ville if ville else store_name
        
        # Requêtes spécialisées par prompt
        queries_by_prompt = {
            1: [  # Zone de chalandise
                f"Decathlon {city} adresse exacte coordonnées GPS",
                f"magasins Decathlon près {city} distances kilomètres",
                f"{city} zone commerciale Actisud centre ville",
                f"transport public {city} bus métro desserte",
                f"axes routiers {city} autoroute nationale départementale"
            ],
            2: [  # SWOT
                f"Decathlon {city} avis clients Google Pages Jaunes",
                f"magasins sport {city} concurrents Intersport Go Sport",
                f"{city} parking Decathlon accessibilité transports",
                f"projets urbanisme {city} zones commerciales",
                f"{city} économie locale emploi entreprises"
            ],
            3: [  # Démographie
                f"{city} population INSEE démographie âge revenus",
                f"{city} familles enfants composition ménages",
                f"{city} CSP cadres employés ouvriers statistiques",
                f"{city} revenu médian pouvoir achat niveau vie",
                f"{city} géographie relief altitude lacs rivières"
            ],
            4: [  # Tourisme/Infrastructures
                f"{city} tourisme nombre visiteurs hébergements",
                f"stades {city} terrains sport football capacité",
                f"piscines {city} centre aquatique horaires tarifs",
                f"pistes cyclables {city} vélo itinéraires kilomètres",
                f"salles sport fitness {city} musculation tarifs"
            ],
            5: [  # Concurrence
                f"magasins sport {city} adresses Sport 2000 Intersport",
                f"spécialistes sport {city} running vélo tennis",
                f"clubs sportifs {city} licenciés adhérents football",
                f"événements sportifs {city} courses marathon trail",
                f"salles fitness {city} Basic-Fit prix abonnements"
            ],
            6: [  # Mobilité/Potentiel
                f"{city} mobilité vélo marche transport modes",
                f"infrastructures cyclables {city} pistes bandes",
                f"pratiques sportives {city} sports populaires",
                f"licenciés sport {city} fédérations données",
                f"marché sport {city} équipements budget dépenses"
            ],
            7: [  # Concurrence détaillée
                f"magasins Decathlon {city} zone chalandise 50km",
                f"Intersport Sport2000 {city} adresses magasins",
                f"concurrents sport {city} grandes surfaces Leclerc Carrefour",
                f"spécialistes sport {city} indépendants franchises",
                f"magasins fermeture {city} presse locale articles"
            ]
        }
        
        return queries_by_prompt.get(prompt_number, [f"{city} sport infrastructure"])
    
    def execute_captation_prompt(self, store_row, prompt_content: str, prompt_number: int, context: str, max_retries: int = 3) -> Optional[str]:
        """Exécute un prompt avec recherches Google multiples et ciblées."""
        
        # Extraire les informations complètes du magasin
        store_name = store_row.get('store_name', 'INCONNU')
        ville = store_row.get('ville', '')
        codeCP = store_row.get('codeCP', '')
        adress = store_row.get('adress', '')
        country_name = store_row.get('country_name', 'FRANCE')
        
        # Créer l'identifiant complet du magasin pour remplacer XXXX
        store_identifier = f" {store_name} {adress} {codeCP} {ville} {country_name}"
        
        # Générer des requêtes de recherche spécialisées
        search_queries = self.create_multi_search_queries(store_row, prompt_number)       
       
        full_prompt = f"""

{prompt_content.replace('XXXX', store_identifier)}

RAPPEL CRITIQUE: Utilise Google Search pour obtenir des informations précises, récentes et vérifiables. Ne te contente pas de généralités.
"""
        #logger.info(f"🔍 Prompt envoyé : {full_prompt}...")
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 Recherche Google avancée pour prompt {prompt_number}...")
                logger.info(f"📋 {len(search_queries)} requêtes ciblées préparées")
                
                # Utiliser le client LLM standardisé avec Google Search
                response_text = self.llm_client.generate_with_search(
                    prompt=full_prompt,
                    max_retries=3,
                    temperature=0.1,
                    max_tokens=8192
                )
                
                if response_text and len(response_text) > 100:
                    logger.info(f"✅ Prompt {prompt_number} réussi ({len(response_text)} chars)")
                    return response_text
                else:
                    logger.warning(f"⚠️ Réponse courte pour prompt {prompt_number} (tentative {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"❌ Erreur prompt {prompt_number} (tentative {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    logger.info(f"⏳ Attente {wait_time}s avant nouvelle tentative...")
                    time.sleep(wait_time)
        
        logger.error(f"❌ Échec définitif prompt {prompt_number} après {max_retries} tentatives")
        return None
    
    def process_store(self, store_row) -> Dict[str, Any]:
        """Traite un magasin avec les 7 prompts de captation."""
        store_id = store_row.get('store_id', 'N/A')
        store_name = store_row.get('store_name', 'INCONNU')
        
        logger.info(f"🏪 Traitement magasin {store_name} (ID: {store_id})")
        
        # Créer le contexte de recherche enrichi
        context = self.create_search_context(store_row)
        
        # Structure pour sauvegarder les résultats
        store_result = {
            'store_id': store_id,
            'store_name': store_name,
            'processing_date': datetime.now().isoformat(),
            'status': 'processing',
            'prompts_results': {},
            'metadata': {
                'model_used': self.model_name,
                'google_search': True,
                'total_prompts': len(self.prompts)
            },
            'summary': {}
        }
        
        successful_prompts = 0
        
        # Traiter chaque prompt
        for prompt in self.prompts:
            prompt_key = f"prompt_{prompt['number']}"
            logger.info(f"📝 Prompt {prompt['number']}: {prompt['title']}")
            
            start_time = time.time()
            
            # Exécuter le prompt avec recherche Google ultra-ciblée
            result = self.execute_captation_prompt(
                store_row, 
                prompt['content'], 
                prompt['number'],
                context
            )
            
            execution_time = time.time() - start_time
            
            if result:
                store_result['prompts_results'][prompt_key] = {
                    'question': prompt['content'],
                    'response': result,
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': execution_time,
                    'title': prompt['title'],
                    'model': self.model_name,
                    'features': ['google_search', 'multi_queries']
                }
                successful_prompts += 1
                self.stats['successful_prompts'] += 1
                logger.info(f"✅ Prompt {prompt['number']} terminé ({execution_time:.1f}s)")
            else:
                store_result['prompts_results'][prompt_key] = {
                    'question': prompt['content'],
                    'response': None,
                    'status': 'failed',
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': execution_time,
                    'title': prompt['title'],
                    'error': 'Échec après plusieurs tentatives'
                }
                self.stats['failed_prompts'] += 1
                logger.error(f"❌ Prompt {prompt['number']} échoué")
            
            # Pause entre prompts pour éviter rate limiting
            time.sleep(5)
        
        # Finaliser le résultat
        store_result['status'] = 'completed' if successful_prompts > 0 else 'failed'
        store_result['summary'] = {
            'total_prompts': len(self.prompts),
            'successful_prompts': successful_prompts,
            'failed_prompts': len(self.prompts) - successful_prompts,
            'completion_rate': successful_prompts / len(self.prompts) * 100
        }
        
        logger.info(f"🎯 Magasin {store_name}: {successful_prompts}/{len(self.prompts)} prompts réussis")
        
        return store_result
    
    def save_to_firestore(self, store_result: Dict[str, Any]) -> bool:
        """Sauvegarde les résultats dans Firestore."""
        try:
            doc_name = f"store_{store_result['store_id']}"
            doc_ref = self.db.collection('polco_magasins_captation').document(doc_name)
            doc_ref.set(store_result)
            
            logger.info(f"💾 Sauvegardé: {doc_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde Firestore: {e}")
            return False
    
    def run(self, limit: Optional[int] = None, test_mode: bool = False, store_id: Optional[str] = None):
        """Lance le traitement POLCO Captation."""
        logger.info("🚀 Démarrage du traitement POLCO Captation")
        logger.info("=" * 80)
        
        self.stats['start_time'] = datetime.now()
        
        # Vérifications
        if not self.check_credentials():
            return False
        
        if not self.init_services():
            return False
        
        if not self.load_prompts():
            return False
        
        if not self.load_stores():
            return False
        
        # Mode test, limite ou magasin spécifique
        stores_to_process = self.stores_df
        
        if store_id:
            # Filtrer uniquement le magasin spécifié
            stores_to_process = self.stores_df[self.stores_df['store_id'].astype(str) == str(store_id)]
            if stores_to_process.empty:
                logger.error(f"❌ Magasin ID '{store_id}' non trouvé dans le CSV")
                logger.info("📋 Magasins disponibles:")
                for _, row in self.stores_df.iterrows():
                    logger.info(f"   • {row['store_id']} - {row['store_name']}")
                return False
            logger.info(f"🎯 Mode magasin spécifique: {stores_to_process.iloc[0]['store_name']} (ID: {store_id})")
        elif test_mode or limit:
            n = limit if limit else 1
            stores_to_process = self.stores_df.head(n)
            logger.info(f"🧪 Mode test activé: traitement de {len(stores_to_process)} magasin(s)")
        
        logger.info(f"📊 {len(stores_to_process)} magasins à traiter")
        logger.info(f"📋 7 prompts de captation par magasin")
        logger.info(f"🔍 Recherche Google multi-requêtes activée")
        logger.info(f"⏱️ Temps estimé: {len(stores_to_process) * 8:.0f} minutes")
        logger.info("")
        
        # Traiter chaque magasin
        for index, store_row in stores_to_process.iterrows():
            try:
                logger.info(f"🏪 [{index + 1}/{len(stores_to_process)}] {store_row.get('store_name', 'INCONNU')}")
                
                # Traiter le magasin
                store_result = self.process_store(store_row)
                
                # Sauvegarder
                if self.save_to_firestore(store_result):
                    self.stats['processed_stores'] += 1
                
            except KeyboardInterrupt:
                logger.info("\n⏹️ Traitement interrompu par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur traitement magasin {store_row.get('store_name', 'INCONNU')}: {e}")
                self.stats['errors'].append(str(e))
        
        # Rapport final
        end_time = datetime.now()
        duration = (end_time - self.stats['start_time']).total_seconds()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 POLCO CAPTATION - RAPPORT FINAL")
        logger.info("=" * 80)
        logger.info(f"⏱️ Durée totale: {duration/60:.1f} minutes")
        logger.info(f"🏪 Magasins traités: {self.stats['processed_stores']}/{self.stats['total_stores']}")
        logger.info(f"✅ Prompts réussis: {self.stats['successful_prompts']}")
        logger.info(f"❌ Prompts échoués: {self.stats['failed_prompts']}")
        logger.info(f"📈 Taux de réussite: {self.stats['successful_prompts']/(self.stats['successful_prompts']+self.stats['failed_prompts'])*100:.1f}%")
        logger.info(f"🗄️ Collection Firestore: polco_magasins_captation")
        logger.info("")
        logger.info("🎉 Traitement POLCO Captation terminé !")
        
        return True


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='POLCO Captation - Google Search Avancé')
    parser.add_argument('--test', action='store_true', help='Mode test (1 magasin)')
    parser.add_argument('--limit', type=int, help='Nombre de magasins à traiter')
    parser.add_argument('--store-id', type=str, help='Traiter uniquement le magasin avec cet ID')
    
    args = parser.parse_args()
    
    processor = PolcoCaptationProcessor()
    
    try:
        processor.run(
            limit=args.limit,
            test_mode=args.test,
            store_id=getattr(args, 'store_id', None)
        )
    except KeyboardInterrupt:
        logger.info("\n⏹️ Processus interrompu")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
