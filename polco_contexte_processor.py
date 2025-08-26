#!/usr/bin/env python3
"""
POLCO CONTEXTE PROCESSOR v3 - VERSION STANDARDISÉE
Génère une analyse de contexte propre pour les rapports professionnels.
Utilise la classe LLM standardisée pour éviter les erreurs de connexion.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from polco_llm_client import get_llm_client

# Configuration
PROJECT_ID = "polcoaigeneration-ved6"
REGION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolcoContexteProcessorV3:
    """Processeur CONTEXTE v3 pour analyse propre et professionnelle."""
    
    def __init__(self, captation_collection="polco_magasins_captation"):
        self.llm_client = get_llm_client()
        self.polco_fr_content = ""
        self.captation_collection = captation_collection
    

    def init_vertex_ai(self) -> bool:
        """Initialise le client LLM standardisé."""
        try:
            logger.info(f"🔧 Initialisation client LLM standardisé...")
            logger.info(f"  - Project: {PROJECT_ID}")
            logger.info(f"  - Region: {REGION}")
            logger.info(f"  - Model: {self.llm_client.model_name}")
            
            # Le client LLM est déjà initialisé dans le constructeur
            logger.info(f"✅ Client LLM standardisé initialisé ({self.llm_client.model_name})")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur client LLM: {e}")
            return False
    
    def load_polco_fr(self) -> bool:
        """Charge le contenu polcoFR.txt."""
        try:
            with open("polcoFR.txt", 'r', encoding='utf-8') as f:
                self.polco_fr_content = f.read()
            logger.info(f"✅ polcoFR.txt chargé ({len(self.polco_fr_content)} caractères)")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur lecture polcoFR.txt: {e}")
            return False
    
    def get_captation_results(self, store_id: str) -> str:
        """Récupère les résultats de captation depuis la collection configurée."""
        try:
            from google.cloud import firestore
            db = firestore.Client(project="polcoaigeneration-ved6")
            doc_ref = db.collection(self.captation_collection).document(f"store_{store_id}")
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"⚠️ Aucun résultat de captation trouvé pour store {store_id}")
                return ""
            
            data = doc.to_dict()
            prompts_results = data.get('prompts_results', {})
            
            if len(prompts_results) < 6:
                logger.warning(f"⚠️ Store {store_id}: seulement {len(prompts_results)}/6 prompts disponibles")
                return ""
            
            # FILTRAGE CIBLÉ POUR CONTEXTE : seulement prompts 1, 2, 3
            relevant_prompts = ['prompt_1', 'prompt_2', 'prompt_3', 'prompt_7']
            captation_content = "\n=== DONNÉES PERTINENTES POUR CONTEXTE ===\n"
            
            for prompt_key in relevant_prompts:
                if prompt_key in prompts_results:
                    prompt_data = prompts_results[prompt_key]
                    if prompt_data.get('status') == 'completed' and prompt_data.get('response'):
                        # Limiter chaque prompt à 10k caractères pour éviter les timeouts
                        response_text = prompt_data['response'][:10000]
                        captation_content += f"\n--- {prompt_key.upper()} (ZONE & CONCURRENCE) ---\n{response_text}\n"
            
            logger.info(f"✅ Store {store_id}: données contexte récupérées (prompts 1-3)")
            return captation_content
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération captation store {store_id}: {e}")
            return ""
    
    def extract_available_data(self, complete_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait uniquement les données réellement disponibles."""
        
        store_id = complete_data.get('store_id')
        data_sources = complete_data.get('data_sources', {})
        internal_data = data_sources.get('internal_data', {})
        
        # Données internes
        synthesis = internal_data.get('synthesis_file', {})
        csv_files = internal_data.get('csv_files', {})
        
        # Récupérer les données de captation depuis Firestore
        captation_content = self.get_captation_results(store_id)
        
        return {
            'store_id': store_id,
            'synthesis': synthesis.get('content', '') if synthesis else '',
            'captation_content': captation_content,
            'csv_files_count': len(csv_files)
        }
    
    def build_clean_prompt(self, store_id: str, available_data: Dict[str, Any], country: str, language: str) -> str:
        """Construit un prompt propre pour génération de rapport professionnel."""
        
        prompt = f"""Tu es un analyste retail expert. Génère une analyse de contexte DIRECTEMENT UTILISABLE dans un rapport professionnel.

🌍 **LOCALISATION ET ACTUALITÉ OBLIGATOIRES:**

- RÉDIGER ENTIÈREMENT la réponse en {language}
- Adapter l'analyse au contexte économique et culturel du pays {country}

=== INSTRUCTIONS CRITIQUES ===
- NE PAS inclure de formules de politesse ("Voici", "Absolument", etc.)
- NE PAS mentionner de limitations de données ou fichiers manquants
- NE PAS répéter les instructions
- Générer UNIQUEMENT le contenu du rapport
- Format Markdown professionnel
- Ton factuel et analytique
- CONSERVER TOUS LES DÉTAILS des données ultra enhanced (chiffres exacts, noms précis, adresses, coordonnées)
- DÉVELOPPER EXHAUSTIVEMENT plutôt que résumer
- INTÉGRER TOUS les éléments factuels des analyses sectorielles
- ADAPTER le vocabulaire et les références au contexte {country}
- **PRÉFÉRER LES TABLEAUX** aux listes complexes pour une meilleure lisibilité et mise en forme
- Utiliser des tableaux Markdown pour les données structurées (concurrents, métriques, comparaisons)
- Éviter les listes à puces trop longues ou complexes

=== DONNÉES DISPONIBLES ===

Données Magasin {store_id}:
{available_data.get('synthesis', 'Données de synthèse non disponibles')[:15000]}

Analyses Sectorielles:
{available_data.get('captation_content', 'Analyses sectorielles non disponibles')}

=== CONTENU À GÉNÉRER ===

## I. CONTEXTE GÉNÉRAL ET LOCAL

### 1.1 Stratégie Nationale Decathlon (Vision 2025-2027)
[DÉVELOPPER EXHAUSTIVEMENT : orientations stratégiques complètes, ambitions PDM détaillées avec chiffres exacts, sports prioritaires avec pourcentages, implications directes et chiffrées pour le magasin {store_id}]

### 1.2 Profil et Positionnement du Magasin
[DÉVELOPPER EXHAUSTIVEMENT : format magasin avec surface exacte, positionnement national avec rang précis, CA exact, rentabilité par m², flux détaillés, rôle précis dans l'écosystème Decathlon local/régional]

### 1.3 Zone de Chalandise et Environnement Local
[DÉVELOPPER EXHAUSTIVEMENT : zone de chalandise avec limites précises, analyse démographique complète (population exacte, CSP détaillées avec %), économie (revenus exacts, taux chômage), infrastructures sportives nommées avec adresses, saisonnalité chiffrée, potentiel touristique quantifié]

### 1.4 Analyse Concurrentielle Locale
[DÉVELOPPER EXHAUSTIVEMENT : mapping concurrents avec noms exacts, adresses précises, distances, forces/faiblesses détaillées par segment, positionnement prix quantifié, opportunités de différenciation factuelles]

### 1.5 Matrice SWOT Approfondie du Magasin
[DÉVELOPPER EXHAUSTIVEMENT : FORCES, FAIBLESSES, OPPORTUNITÉS, MENACES avec tous les éléments concrets, chiffres exacts, noms précis et données mesurables des analyses sectorielles]

=== GÉNÉRATION ===
Génère maintenant le contenu complet et professionnel selon cette structure, en te basant UNIQUEMENT sur les données fournies.
"""
        #logger.info(f"🔍 Prompt envoyé : {prompt}...")
        return prompt
    
    def process_store(self, store_data: Dict[str, Any], country: str, language: str) -> Optional[Dict[str, Any]]:
        """Traite un magasin pour l'analyse contextuelle v3."""
        
        store_id = store_data.get('store_id', 'unknown')
        logger.info(f"🎯 PROCESSEUR CONTEXTE v3 - Magasin {store_id}")
        
        try:
            # Initialiser Vertex AI
            if not self.init_vertex_ai():
                return None
            
            # Charger polcoFR
            if not self.load_polco_fr():
                return None
            
            # Extraire les données disponibles
            available_data = self.extract_available_data(store_data)

            # Construire le prompt propre
            prompt = self.build_clean_prompt(store_id, available_data, country, language)

            logger.info(f"📊 Génération analyse CONTEXTE v3 magasin {store_id}")
            logger.info(f"📝 Prompt contexte: {len(prompt)} caractères")
            
            # Diagnostic détaillé
            logger.info(f"🔍 Diagnostic prompt store {store_id}:")
            logger.info(f"  - Taille synthesis: {len(available_data.get('synthesis', ''))} chars")  
            logger.info(f"  - Taille captation: {len(available_data.get('captation_content', ''))} chars")
            logger.info(f"  - Model: {self.llm_client.model_name}")

            # Générer l'analyse avec le client LLM standardisé
            start_time = datetime.now()
            
            logger.info(f"🔄 Génération avec client LLM standardisé pour store {store_id}")
            
            response_text = self.llm_client.generate_simple(
                prompt=prompt,
                max_retries=3,
                temperature=0.1,
                max_tokens=20000
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if response_text:
                result_length = len(response_text)
                logger.info(f"✅ Contexte v3 généré: {result_length} caractères en {duration:.1f}s")
                
                return {
                    'section': 'CONTEXTE',
                    'content': response_text,
                    'metadata': {
                        'store_id': store_id,
                        'generation_time': duration,
                        'input_length': len(prompt),
                        'output_length': result_length,
                        'timestamp': datetime.now().isoformat(),
                        'model_used': self.llm_client.model_name,
                        'version': 'v3_standardized'
                    }
                }
            else:
                logger.error(f"❌ Réponse vide pour {store_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur traitement contexte v3 {store_id}: {e}")
            return None


    def test_api_simple(self) -> bool:
        """Test simple de l'API avec le client LLM standardisé."""
        try:
            logger.info("🧪 Test API simple avec client LLM standardisé...")
            
            simple_prompt = """Réponds: Paris, 2.1 millions d'habitants."""

            response_text = self.llm_client.generate_simple(
                prompt=simple_prompt,
                max_retries=3,
                temperature=0.1,
                max_tokens=1000
            )
            
            if response_text:
                logger.info(f"✅ Test API réussi: {len(response_text)} chars")
                logger.info(f"📝 Réponse: {response_text[:100]}...")
                return True
            else:
                logger.error("❌ Test API échoué: réponse vide")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test API échoué: {e}")
            return False

def main():
    """Point d'entrée pour test."""
    processor = PolcoContexteProcessorV3()
    logger.info("🎯 Test Processeur CONTEXTE v3 (Version Nettoyée)")
    
    # Test d'initialisation
    if not processor.init_vertex_ai():
        logger.error("❌ Échec initialisation Vertex AI")
        return
    
    # Test API simple
    if not processor.test_api_simple():
        logger.error("❌ Échec test API simple")
        return
        
    logger.info("✅ Processeur CONTEXTE v3 opérationnel")

if __name__ == "__main__":
    main()
