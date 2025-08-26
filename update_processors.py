#!/usr/bin/env python3
"""
Script pour mettre à jour tous les processeurs POLCO
pour utiliser la classe LLM standardisée
"""

import os
import re

def update_processor_file(filename):
    """Met à jour un fichier processeur pour utiliser la classe LLM standardisée."""
    print(f"🔄 Mise à jour de {filename}...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer les imports
    content = re.sub(
        r'import vertexai\s*\nfrom vertexai\.generative_models import GenerativeModel',
        'from polco_llm_client import get_llm_client',
        content
    )
    
    # Remplacer l'initialisation du modèle
    content = re.sub(
        r'self\.model = None',
        'self.llm_client = get_llm_client()',
        content
    )
    
    # Remplacer la fonction init_vertex_ai
    content = re.sub(
        r'def init_vertex_ai\(self\) -> bool:\s*"""Initialise Vertex AI\."""\s*try:\s*logger\.info\(f"🔧 Initialisation Vertex AI\.\.\."\)\s*logger\.info\(f"  - Project: {PROJECT_ID}"\)\s*logger\.info\(f"  - Region: {REGION}"\)\s*logger\.info\(f"  - Model: {MODEL_NAME}"\)\s*vertexai\.init\(project=PROJECT_ID, location=REGION\)\s*self\.model = GenerativeModel\(MODEL_NAME\)\s*logger\.info\(f"✅ Vertex AI initialisé \({MODEL_NAME}\)"\)\s*return True\s*except Exception as e:\s*logger\.error\(f"❌ Erreur Vertex AI: {e}"\)\s*return False',
        '''def init_vertex_ai(self) -> bool:
        """Initialise le client LLM standardisé."""
        try:
            logger.info(f"🔧 Initialisation client LLM standardisé...")
            logger.info(f"  - Project: {PROJECT_ID}")
            logger.info(f"  - Region: {REGION}")
            logger.info(f"  - Model: {MODEL_NAME}")
            
            # Le client LLM est déjà initialisé dans le constructeur
            logger.info(f"✅ Client LLM standardisé initialisé ({MODEL_NAME})")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur client LLM: {e}")
            return False''',
        content,
        flags=re.DOTALL
    )
    
    # Remplacer les appels generate_content
    content = re.sub(
        r'response = self\.model\.generate_content\(\s*prompt,\s*generation_config=\{\s*"max_output_tokens": (\d+),\s*"temperature": ([\d.]+),\s*"top_p": ([\d.]+),\s*"top_k": (\d+)\s*\}\s*\)',
        r'response_text = self.llm_client.generate_simple(\n                prompt=prompt,\n                max_retries=3,\n                temperature=\2,\n                max_tokens=\1\n            )',
        content
    )
    
    # Remplacer response.text par response_text
    content = re.sub(r'response\.text', 'response_text', content)
    
    # Remplacer response and response.text par response_text
    content = re.sub(r'response and response\.text', 'response_text', content)
    
    # Mettre à jour la version dans les métadonnées
    content = re.sub(r"'version': 'v\d+[^']*'", "'version': 'v3_standardized'", content)
    
    # Écrire le fichier modifié
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ {filename} mis à jour")

def main():
    """Met à jour tous les processeurs."""
    processors = [
        'polco_cibles_processor.py',
        'polco_potentiel_processor.py', 
        'polco_offre_processor.py',
        'polco_actions_processor.py'
    ]
    
    for processor in processors:
        if os.path.exists(processor):
            update_processor_file(processor)
        else:
            print(f"⚠️ {processor} non trouvé")

if __name__ == "__main__":
    main()
