#!/usr/bin/env python3
"""
POLCO OFFRE PROCESSOR v3 - VERSION NETTOYÉE
Génère une analyse de l'offre produit et sportive propre pour les rapports professionnels.
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

class PolcoOffreProcessorV3:
    """Processeur OFFRE v3 pour analyse propre et professionnelle."""
    
    def __init__(self, captation_collection="polco_magasins_captation"):
        self.llm_client = get_llm_client()
        self.captation_collection = captation_collection
        self.polco_fr_content = ""
    

    def init_vertex_ai(self) -> bool:
        """Initialise Vertex AI."""
        try:
            # Le client LLM est déjà initialisé dans le constructeur
            logger.info(f"✅ Client LLM standardisé initialisé ({MODEL_NAME})")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur Vertex AI: {e}")
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
        """Récupère les résultats de captation depuis polco_magasins_enhanced."""
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
            
            # FILTRAGE CIBLÉ POUR OFFRE : seulement prompts 5, 6 (gammes produits + tendances sport)
            relevant_prompts = ['prompt_5', 'prompt_6']
            captation_content = "\n=== DONNÉES PERTINENTES POUR OFFRE ===\n"
            
            for prompt_key in relevant_prompts:
                if prompt_key in prompts_results:
                    prompt_data = prompts_results[prompt_key]
                    if prompt_data.get('status') == 'completed' and prompt_data.get('response'):
                        # Limiter à 20k caractères par prompt
                        response_text = prompt_data['response'][:20000]
                        captation_content += f"\n--- {prompt_key.upper()} (GAMMES & TENDANCES) ---\n{response_text}\n"
            
            logger.info(f"✅ Store {store_id}: données offre récupérées (prompts 5-6)")
            return captation_content
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération captation store {store_id}: {e}")
            return ""
    
    def extract_product_data(self, complete_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les données produits disponibles."""
        
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
    
    def build_clean_prompt(self, store_id: str, product_data: Dict[str, Any], country: str, language: str) -> str:
        """Construit un prompt propre pour l'analyse de l'offre."""
        
        prompt = f"""Tu es un analyste retail expert. Génère une analyse de l'offre produit et sportive DIRECTEMENT UTILISABLE dans un rapport professionnel.

🌍 **LOCALISATION ET ACTUALITÉ OBLIGATOIRES:**

- RÉDIGER ENTIÈREMENT la réponse en {language}
- Adapter l'analyse aux tendances et préférences du pays {country}

🕐 **VÉRIFICATION D'ACTUALITÉ CRITIQUE:**
- PRIORISER les offres et produits actuels (2024-2025)
- EXCLURE les gammes ou tendances manifestement périmées
- SIGNALER explicitement toute information douteuse avec "À VÉRIFIER"
- Privilégier les nouvelles gammes et innovations RÉCENTES

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
- ADAPTER le vocabulaire et l'offre au contexte {country}
- **PRÉFÉRER LES TABLEAUX** aux listes complexes pour une meilleure lisibilité et mise en forme
- Utiliser des tableaux Markdown pour les données structurées (assortiments, performances, comparaisons)
- Éviter les listes à puces trop longues ou complexes

=== DONNÉES DISPONIBLES ===

Stratégie Nationale Decathlon France 2025-2027:
{self.polco_fr_content}

Données Magasin {store_id}:
{product_data.get('synthesis', 'Données de synthèse non disponibles')}

Analyses Sectorielles:
{product_data.get('captation_content', 'Analyses sectorielles non disponibles')}

=== CONTENU À GÉNÉRER ===

## IV. QUOI VENDRE (OFFRE PRODUIT ET SPORTIVE)

### 4.1 Analyse de l'Offre Produit Actuelle
[Assortiment par sport et univers, performance marques propres vs internationales, best-sellers vs faible rotation, adéquation aux besoins clients locaux]

### 4.2 Stratégie Sportive et Animation Commerciale
[Sports prioritaires et performance, événements et animations, partenariats locaux, rôle comme hub sportif local]

### 4.3 Innovation et Tendances Marché
[Nouvelles tendances sportives et produits, potentiel nouvelles offres/services, veille concurrentielle innovations, adaptation aux évolutions pratiques]

### 4.4 Recommandations Stratégiques et Commerciales
[Synthèse opportunités et menaces, propositions concrètes optimisation performance, axes d'amélioration expérience client et offre, plan d'action priorisé avec objectifs mesurables]

=== GÉNÉRATION ===
Génère maintenant le contenu complet et professionnel selon cette structure, en te basant UNIQUEMENT sur les données fournies.
"""
        
        return prompt
    
    def process_store(self, store_data: Dict[str, Any], country: str, language: str) -> Optional[Dict[str, Any]]:
        """Traite un magasin pour l'analyse de l'offre v3."""
        
        store_id = store_data.get('store_id', 'unknown')
        logger.info(f"🛍️ PROCESSEUR OFFRE v3 - Magasin {store_id}")
        
        try:
            # Initialiser Vertex AI
            if not self.init_vertex_ai():
                return None
            
            # Charger polcoFR
            if not self.load_polco_fr():
                return None
            
            # Extraire les données produits
            product_data = self.extract_product_data(store_data)
            
            # Construire le prompt propre
            prompt = self.build_clean_prompt(store_id, product_data, country, language)
            
            logger.info(f"🛍️ Génération analyse OFFRE v3 magasin {store_id}")
            logger.info(f"📝 Prompt offre: {len(prompt)} caractères")
            
            # Générer l'analyse avec retry
            start_time = datetime.now()
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    response_text = self.llm_client.generate_simple(
                prompt=prompt,
                max_retries=3,
                temperature=0.2,
                max_tokens=32000
            )
                    break  # Succès, sortir de la boucle
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        logger.warning(f"⚠️ Erreur API Vertex (tentative {attempt + 1}/{max_retries}): {e}")
                        logger.info(f"⏳ Attente {wait_time}s avant nouvelle tentative...")
                        import time
                        time.sleep(wait_time)
                    else:
                        raise e
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if response_text:
                result_length = len(response_text)
                logger.info(f"✅ Offre v3 générée: {result_length} caractères en {duration:.1f}s")
                
                return {
                    'section': 'OFFRE',
                    'content': response_text,
                    'metadata': {
                        'store_id': store_id,
                        'generation_time': duration,
                        'input_length': len(prompt),
                        'output_length': result_length,
                        'timestamp': datetime.now().isoformat(),
                        'model_used': MODEL_NAME,
                        'version': 'v3_standardized'
                    }
                }
            else:
                logger.error(f"❌ Réponse vide pour {store_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur traitement offre v3 {store_id}: {e}")
            return None


def main():
    """Point d'entrée pour test."""
    processor = PolcoOffreProcessorV3()
    logger.info("🛍️ Test Processeur OFFRE v3 (Version Nettoyée)")
    logger.info("✅ Processeur OFFRE v3 initialisé")

if __name__ == "__main__":
    main()
