#!/usr/bin/env python3
"""
POLCO ACTIONS PROCESSOR v3 - Propositions d'Actions
Génère des propositions d'actions stratégiques basées sur les 4 analyses précédentes.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from polco_llm_client import get_llm_client

# Configuration
PROJECT_ID = "polcoaigeneration-ved6"
REGION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolcoActionsProcessorV3:
    """Processeur ACTIONS v3 pour propositions d'actions stratégiques."""
    
    def __init__(self, captation_collection="polco_magasins_captation"):
        self.llm_client = get_llm_client()
        self.captation_collection = captation_collection
    

    def init_vertex_ai(self) -> bool:
        """Initialise Vertex AI."""
        try:
            # Le client LLM est déjà initialisé dans le constructeur
            logger.info(f"✅ Client LLM standardisé initialisé ({MODEL_NAME})")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur Vertex AI: {e}")
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
            
            # Fusionner tous les résultats de captation
            captation_content = "\n=== RÉSULTATS DE CAPTATION (6 PROMPTS) ===\n"
            for prompt_key, prompt_data in prompts_results.items():
                if prompt_data.get('status') == 'completed' and prompt_data.get('response'):
                    captation_content += f"\n--- {prompt_key.upper()} ---\n{prompt_data['response']}\n"
            
            logger.info(f"✅ Store {store_id}: {len(prompts_results)} prompts de captation récupérés")
            return captation_content
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération captation store {store_id}: {e}")
            return ""
    
    def extract_sections_content(self, sections_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Extrait le contenu des 4 sections précédentes."""
        
        sections_content = {
            'CONTEXTE': '',
            'CIBLES': '',
            'POTENTIEL': '',
            'OFFRE': ''
        }
        
        for section_data in sections_data:
            section_name = section_data.get('section', '')
            section_content = section_data.get('content', '')
            
            if section_name in sections_content:
                sections_content[section_name] = section_content
        
        return sections_content
    
    def build_actions_prompt(self, store_id: str, sections_content: Dict[str, str], country: str, language: str, captation_content: str = "") -> str:
        """Construit le prompt pour les propositions d'actions."""
        
        prompt = f"""Tu es un consultant retail expert. Génère des propositions d'actions stratégiques DIRECTEMENT UTILISABLES dans un rapport professionnel.

🌍 **LOCALISATION ET ACTUALITÉ OBLIGATOIRES:**

- RÉDIGER ENTIÈREMENT la réponse en {language}
- Adapter les actions au contexte réglementaire et culturel du pays {country}

🕐 **VÉRIFICATION D'ACTUALITÉ CRITIQUE:**
- PROPOSER uniquement des actions réalisables et actuelles (2024-2025)
- TENIR COMPTE des évolutions récentes du marché retail
- EXCLURE les actions devenues obsolètes ou non pertinentes
- ADAPTER aux tendances et réglementations locales actuelles

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
- OBLIGATOIRE : Préciser que ces actions sont proposées par Intelligence Artificielle
- ADAPTER le vocabulaire et les actions au contexte {country}
- **PRÉFÉRER LES TABLEAUX** aux listes complexes pour une meilleure lisibilité et mise en forme
- Utiliser des tableaux Markdown pour les données structurées (actions, priorités, échéanciers)
- Éviter les listes à puces trop longues ou complexes

=== DONNÉES DISPONIBLES POUR LE MAGASIN {store_id} ===

## ANALYSES SECTORIELLES (4 PROCESSEURS) :

### CONTEXTE :
{sections_content.get('CONTEXTE', 'Non disponible')}

### CIBLES :
{sections_content.get('CIBLES', 'Non disponible')}

### POTENTIEL :
{sections_content.get('POTENTIEL', 'Non disponible')}

### OFFRE :
{sections_content.get('OFFRE', 'Non disponible')}

## DONNÉES DE CAPTATION (6 PROMPTS) :
{captation_content if captation_content else 'Non disponible'}

=== CONTENU À GÉNÉRER ===

## V. PROPOSITIONS D'ACTIONS À CHALLENGER PAR VOS ÉQUIPES

**⚠️ AVERTISSEMENT** : Ces propositions d'actions sont générées par Intelligence Artificielle sur la base des analyses précédentes. Elles constituent des pistes de réflexion à challenger, adapter et valider avec vos équipes terrain et votre connaissance du marché local.

### 5.1 Actions Court Terme (0-6 mois)

[Pour chaque action proposée, indiquer :]
- **Action** : Description précise
- **Objectif** : Impact attendu
- **Difficulté** : ⭐ (Facile) à ⭐⭐⭐⭐⭐ (Très difficile)
- **Ressources** : Moyens nécessaires
- **Indicateurs** : Comment mesurer le succès

### 5.2 Actions Moyen Terme (6-18 mois)

[Même structure que court terme]

### 5.3 Actions Long Terme (18+ mois)

[Même structure que court terme]

### 5.4 Priorisation et Feuille de Route

[Synthèse des actions prioritaires avec échéancier]

=== GÉNÉRATION ===
Génère maintenant le contenu complet selon cette structure, en te basant EXCLUSIVEMENT sur les analyses fournies. Propose des actions concrètes, réalistes et mesurables.
"""
        
        return prompt
    
    def process_store(self, store_data: Dict[str, Any], sections_data: List[Dict[str, Any]], country: str, language: str) -> Optional[Dict[str, Any]]:
        """Traite un magasin pour les propositions d'actions."""
        
        store_id = store_data.get('store_id', 'unknown')
        logger.info(f"🎯 PROCESSEUR ACTIONS v3 - Magasin {store_id}")
        
        try:
            # Initialiser Vertex AI
            if not self.init_vertex_ai():
                return None
            
            # Extraire le contenu des sections précédentes
            sections_content = self.extract_sections_content(sections_data)
            
            # Récupérer les données de captation
            captation_content = self.get_captation_results(store_id)
            
            # Vérifier qu'on a au moins quelques sections
            available_sections = [k for k, v in sections_content.items() if v.strip()]
            if len(available_sections) < 2:
                logger.error(f"❌ Pas assez de sections disponibles pour {store_id}")
                return None
            
            logger.info(f"📊 Sections analysées : {', '.join(available_sections)}")
            if captation_content:
                logger.info(f"📊 Données de captation : {len(captation_content)} caractères")
            
            # Construire le prompt
            prompt = self.build_actions_prompt(store_id, sections_content, country, language, captation_content)
            
            logger.info(f"🎯 Génération propositions ACTIONS magasin {store_id}")
            logger.info(f"📝 Prompt actions: {len(prompt)} caractères")
            
            # Générer l'analyse avec retry
            start_time = datetime.now()
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": 32000,  
                            "temperature": 0.3,  # Créatif mais pas trop
                            "top_p": 0.8,
                            "top_k": 40
                        }
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
                logger.info(f"✅ Actions v3 générées: {result_length} caractères en {duration:.1f}s")
                
                return {
                    'section': 'ACTIONS',
                    'content': response_text,
                    'metadata': {
                        'store_id': store_id,
                        'generation_time': duration,
                        'input_length': len(prompt),
                        'output_length': result_length,
                        'timestamp': datetime.now().isoformat(),
                        'model_used': MODEL_NAME,
                        'version': 'v3_standardized',
                        'sections_analyzed': available_sections
                    }
                }
            else:
                logger.error(f"❌ Réponse vide pour {store_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur traitement actions v3 {store_id}: {e}")
            return None


def main():
    """Point d'entrée pour test."""
    processor = PolcoActionsProcessorV3()
    logger.info("🎯 Test Processeur ACTIONS v3")
    logger.info("✅ Processeur ACTIONS v3 initialisé")

if __name__ == "__main__":
    main()
