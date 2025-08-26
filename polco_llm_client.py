#!/usr/bin/env python3
"""
POLCO - Client LLM Standardisé
Classe unifiée pour tous les appels au LLM avec gestion d'erreurs robuste
Basée sur la méthode qui fonctionne dans polco_captation.py
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolcoLLMClient:
    """Client LLM standardisé pour tous les modules POLCO."""
    
    def __init__(self, project_id: str = "polcoaigeneration-ved6", region: str = "us-central1", model_name: str = "gemini-2.5-pro"):
        """Initialise le client LLM."""
        self.project_id = project_id
        self.region = region
        self.model_name = model_name
        self.genai_client = None
        self.genai_types = None
        self.is_initialized = False
        
        logger.info(f"🚀 Initialisation du client LLM POLCO standardisé avec {model_name}")
    
    def check_credentials(self) -> bool:
        """Vérifie les credentials."""
        if not os.path.exists("credentials.json"):
            logger.error("❌ Fichier credentials.json non trouvé")
            return False
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("credentials.json")
        logger.info("✅ Credentials configurés")
        return True
    
    def init_client(self) -> bool:
        """Initialise le client Google GenAI."""
        try:
            from google import genai
            from google.genai import types
            
            self.genai_client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.region,
            )
            
            self.genai_types = types
            self.is_initialized = True
            
            logger.info(f"✅ Client LLM initialisé avec {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation client LLM: {e}")
            return False
    
    def generate_content(self, 
                        prompt: str, 
                        max_retries: int = 3, 
                        temperature: float = 0.1,
                        max_tokens: int = 8192,
                        use_google_search: bool = False) -> Optional[str]:
        """
        Génère du contenu avec le LLM avec gestion d'erreurs robuste.
        
        Args:
            prompt: Le prompt à envoyer
            max_retries: Nombre maximum de tentatives
            temperature: Température pour la génération
            max_tokens: Nombre maximum de tokens
            use_google_search: Utiliser Google Search ou non
        
        Returns:
            Le contenu généré ou None en cas d'échec
        """
        if not self.is_initialized:
            if not self.check_credentials() or not self.init_client():
                logger.error("❌ Client LLM non initialisé")
                return None
        
        for attempt in range(max_retries):
            try:
                # Configuration de l'appel
                contents = [
                    self.genai_types.Content(
                        role="user",
                        parts=[self.genai_types.Part(text=prompt)]
                    )
                ]
                
                # Outils (Google Search optionnel)
                tools = []
                if use_google_search:
                    tools.append(self.genai_types.Tool(google_search=self.genai_types.GoogleSearch()))
                
                generate_content_config = self.genai_types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=8192,  # Augmenter pour éviter MAX_TOKENS
                    safety_settings=[
                        self.genai_types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="OFF"
                        ),
                        self.genai_types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="OFF"
                        ),
                        self.genai_types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="OFF"
                        ),
                        self.genai_types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="OFF"
                        )
                    ],
                    tools=tools if tools else None,
                )
                
                # Appel non-streaming pour éviter les problèmes de MAX_TOKENS
                logger.info(f"📤 Envoi prompt ({len(prompt)} chars) vers {self.model_name}...")
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generate_content_config
                )
                
                # Traitement de la réponse avec logs clairs
                if response and response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts and len(candidate.content.parts) > 0:
                        result = candidate.content.parts[0].text.strip()
                        logger.info(f"📥 Réponse reçue ({len(result)} chars)")
                    else:
                        result = ""
                        logger.warning("⚠️ Réponse vide (finish_reason: {candidate.finish_reason})")
                else:
                    result = ""
                    logger.warning("⚠️ Réponse malformée")
                
                if result and len(result) > 0:  # Seuil très bas pour le test
                    logger.info(f"✅ Génération LLM réussie ({len(result)} chars)")
                    return result
                else:
                    logger.warning(f"⚠️ Réponse vide (tentative {attempt + 1}/{max_retries})")
                    
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg or "Server disconnected" in error_msg or "Socket closed" in error_msg:
                    logger.warning(f"⚠️ Erreur 503/Connexion (tentative {attempt + 1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 15  # Attente plus longue pour les erreurs 503
                        logger.info(f"⏳ Attente {wait_time}s avant nouvelle tentative...")
                        time.sleep(wait_time)
                else:
                    logger.warning(f"⚠️ Erreur API Vertex (tentative {attempt + 1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        logger.info(f"⏳ Attente {wait_time}s avant nouvelle tentative...")
                        time.sleep(wait_time)
        
        logger.error(f"❌ Échec définitif après {max_retries} tentatives")
        return None
    
    def generate_with_search(self, prompt: str, max_retries: int = 3, temperature: float = 0.1, max_tokens: int = 8192) -> Optional[str]:
        """Génère du contenu avec Google Search activé."""
        return self.generate_content(prompt, max_retries, temperature, max_tokens, use_google_search=True)
    
    def generate_simple(self, prompt: str, max_retries: int = 3, temperature: float = 0.1, max_tokens: int = 8192) -> Optional[str]:
        """Génère du contenu sans Google Search."""
        return self.generate_content(prompt, max_retries, temperature, max_tokens, use_google_search=False)


# Instance globale pour réutilisation
_llm_client = None

def get_llm_client(model_name: str = "gemini-2.5-pro") -> PolcoLLMClient:
    """Retourne l'instance globale du client LLM."""
    global _llm_client
    if _llm_client is None or _llm_client.model_name != model_name:
        _llm_client = PolcoLLMClient(model_name=model_name)
        logger.info(f"🔄 Nouveau client LLM créé avec {model_name}")
    return _llm_client
