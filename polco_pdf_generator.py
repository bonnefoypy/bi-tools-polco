#!/usr/bin/env python3
"""
POLCO PDF Generator - Version Simplifiée et Robuste
Convertit les rapports POLCO 3.0 Markdown en PDF professionnels Decathlon
Architecture: pyppeteer (conversion HTML vers PDF)
"""

import os
import sys
import subprocess
import shutil
import re
import logging
import asyncio
import markdown
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

try:
    from pyppeteer import launch
    PYPETEER_AVAILABLE = True
except ImportError:
    PYPETEER_AVAILABLE = False

# Configuration
REPORTS_DIR = "reports_polco_3_0"
OUTPUT_DIR = "pdfs_polco_3_0"

# Couleurs Decathlon
COLORS = {
    'blue_primary': '#0082C3',
    'blue_dark': '#003d82', 
    'green': '#00A651',
    'orange': '#FF6900',
    'text_dark': '#1a1a1a',
    'text_light': '#666',
    'border_light': '#e0e0e0'
}

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PolcoPDFGenerator:
    """Générateur PDF simplifié et robuste pour POLCO 3.0 utilisant pyppeteer."""
    
    def __init__(self):
        """Initialise le générateur PDF."""
        self.reports_dir = REPORTS_DIR
        self.output_dir = OUTPUT_DIR
        self.available_tools = self.check_tools()
        
        # Créer le dossier de sortie
        Path(self.output_dir).mkdir(exist_ok=True)
        
        logger.info("🎨 Générateur PDF POLCO 3.0 - Version Pyppeteer")
        logger.info(f"🛠️ Outils disponibles: {', '.join(self.available_tools)}")
    
    def check_tools(self) -> List[str]:
        """Vérifie les outils PDF disponibles."""
        tools = []
        
        # Vérifier pyppeteer
        if PYPETEER_AVAILABLE:
            tools.append('pyppeteer')
            logger.info("✅ pyppeteer disponible")
        else:
            logger.error("❌ pyppeteer non trouvé")
            logger.info("💡 Installation: pip install pyppeteer")
        
        if not tools:
            logger.error("❌ Aucun outil PDF disponible!")
            logger.error("Installez pyppeteer: pip install pyppeteer")
        
        return tools
    
    def detect_language(self, content: str) -> str:
        """Détecte la langue du contenu Markdown."""
        sample = ' '.join(content.split('\n')[:50]).lower()
        
        # Mots-clés par langue
        keywords = {
            "de": ['kontext', 'analyse', 'strategie', 'kunde', 'geschäft', 'umsatz', 'potenzial', 'markt'],
            "es": ['contexto', 'análisis', 'estrategia', 'cliente', 'tienda', 'ingresos', 'potencial'],
            "it": ['contesto', 'analisi', 'strategia', 'cliente', 'negozio', 'ricavi', 'potenziale'],
            "en": ['context', 'analysis', 'strategy', 'customer', 'store', 'revenue', 'potential'],
            "fr": ['contexte', 'analyse', 'stratégie', 'clientèle', 'magasin', 'chiffre', 'potentiel']
        }
        
        scores = {lang: sum(1 for word in words if word in sample) 
                 for lang, words in keywords.items()}
        
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "fr"
    
    def extract_store_info(self, filename: str, content: str) -> Tuple[str, str]:
        """Extrait les infos du magasin depuis le nom de fichier et contenu."""
        # Extraire store_id du nom de fichier
        match = re.search(r'POLCO_3_0_DECATHLON_(\d+)_', filename)
        store_id = match.group(1) if match else "XXX"
        
        # Chercher le nom du magasin dans le contenu
        store_name_patterns = [
            r'Magasin\s+(\w+)',
            r'Store\s+(\w+)', 
            r'Decathlon\s+(\w+)',
            r'magasin cible.*?(\w+)',
        ]
        
        store_name = f"Store_{store_id}"
        for pattern in store_name_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                store_name = match.group(1).upper()
                break
        
        return store_id, store_name
    
    def create_cover_image_svg(self, store_name: str, language: str) -> str:
        """Crée une couverture sous forme d'image SVG intégrée."""
        texts = {
            "fr": {"title": "POLITIQUE COMMERCIALE"},
            "de": {"title": "HANDELSPOLITIK"},
            "es": {"title": "POLÍTICA COMERCIAL"},
            "en": {"title": "COMMERCIAL POLICY"},
            "it": {"title": "POLITICA COMMERCIALE"}
        }
        
        text = texts.get(language, texts["fr"])
        period = f"2023 - 2025 {store_name.upper()}"
        
        svg_cover = f'''
        <svg width="595" height="842" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="{COLORS['blue_primary']}"/>
            <text x="50" y="60" fill="white" font-size="20" font-weight="bold" font-family="Arial">DECATHLON</text>
            <text x="50%" y="40%" text-anchor="middle" fill="white" font-size="36" font-weight="bold" font-family="Arial">
                {text['title']}
            </text>
            <text x="50%" y="50%" text-anchor="middle" fill="white" font-size="18" font-family="Arial">
                {period}
            </text>
            <text x="50%" y="90%" text-anchor="middle" fill="white" font-size="12" font-family="Arial">
                © 2025 Decathlon - POLCO ANALYZER 3.0
            </text>
        </svg>
        '''
        
        import base64
        svg_encoded = base64.b64encode(svg_cover.encode()).decode()
        
        return f'''
        <div class="cover-page">
            <img src="data:image/svg+xml;base64,{svg_encoded}" style="width: 100%; height: 100%; object-fit: cover;">
        </div>
        <div class="page-break"></div>
        '''
    
    def create_cover_page(self, store_id: str, store_name: str, language: str) -> str:
        """Crée la page de couverture HTML."""
        
        # Textes par langue
        texts = {
            "fr": {
                "title": "POLITIQUE COMMERCIALE",
                "period": f"2023 - 2025 {store_name.upper()}",
                "footer": "Analyse générée par POLCO ANALYZER 3.0"
            },
            "de": {
                "title": "HANDELSPOLITIK",
                "period": f"2023 - 2025 {store_name.upper()}",
                "footer": "Analyse erstellt von POLCO ANALYZER 3.0"
            },
            "es": {
                "title": "POLÍTICA COMERCIAL",
                "period": f"2023 - 2025 {store_name.upper()}",
                "footer": "Análisis generado por POLCO ANALYZER 3.0"
            },
            "en": {
                "title": "COMMERCIAL POLICY",
                "period": f"2023 - 2025 {store_name.upper()}",
                "footer": "Analysis generated by POLCO ANALYZER 3.0"
            },
            "it": {
                "title": "POLITICA COMMERCIALE",
                "period": f"2023 - 2025 {store_name.upper()}",
                "footer": "Analisi generata da POLCO ANALYZER 3.0"
            }
        }
        
        text = texts.get(language, texts["fr"])
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        return f"""
        <div class="cover-page">
            <div class="cover-logo">
                DECATHLON
            </div>
            <div class="cover-main">
                <h1 class="cover-title">{text['title']}</h1>
                <h2 class="cover-period">{text['period']}</h2>
            </div>
            <div class="cover-footer">
                {text['footer']}<br>
                {current_date} - © 2025 Decathlon
            </div>
        </div>
        <div class="page-break"></div>
        """
    
    def extract_toc(self, content: str, language: str) -> str:
        """Extrait et génère la table des matières."""
        
        toc_titles = {
            "fr": "SOMMAIRE",
            "de": "INHALTSVERZEICHNIS", 
            "es": "ÍNDICE",
            "en": "TABLE OF CONTENTS",
            "it": "INDICE"
        }
        
        title = toc_titles.get(language, "SOMMAIRE")
        
        # Extraire le nom du magasin pour personnaliser
        store_name_match = re.search(r'(SAARLOUIS|FORBACH|AUGNY|MAGASIN\s+(\w+)|Decathlon\s+(\w+))', content, re.IGNORECASE)
        if store_name_match:
            if store_name_match.group(2):  # MAGASIN XXX
                store_name = store_name_match.group(2)
            elif store_name_match.group(3):  # Decathlon XXX
                store_name = store_name_match.group(3)
            else:  # SAARLOUIS, FORBACH, AUGNY
                store_name = store_name_match.group(1)
        else:
            store_name = "MAGASIN"
        
        toc_html = f"""
        <div class="toc-page">
            <div class="toc-header">
                <div class="decathlon-logo-small">DECATHLON</div>
                <h1>{title}</h1>
            </div>
            <div class="toc-grid">
                <div class="toc-column-left">
                    <div class="toc-section">
                        <h3>► Contexte</h3>
                        <ul>
                            <li>Marché identifié</li>
                            <li>La ville de {store_name}</li>
                            <li>Concurrence locale / digitale</li>
                            <li>Rapport d'étonnement</li>
                        </ul>
                    </div>
                    <div class="toc-section">
                        <h3>► À qui vendre ?</h3>
                        <ul>
                            <li>Zone de leadership</li>
                            <li>Concurrence sports 1</li>
                            <li>Comportement d'achat</li>
                        </ul>
                    </div>
                </div>
                <div class="toc-column-right">
                    <div class="toc-section">
                        <h3>► Quoi vendre ?</h3>
                        <ul>
                            <li>Classification des sports</li>
                            <li>Sports & produits</li>
                        </ul>
                    </div>
                    <div class="toc-section">
                        <h3>► Comment vendre ?</h3>
                        <ul>
                            <li>Qui fait quoi</li>
                            <li>Notre histoire</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        <div class="page-break"></div>
        """
        
        return toc_html
    
    def enhance_content(self, content: str) -> str:
        """Améliore le contenu Markdown avec des classes CSS."""
        
        # Nettoyer le contenu YAML et commentaires
        content = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL)
        content = re.sub(r'^<!--.*?-->\n', '', content, flags=re.MULTILINE)
        
        # CORRECTION PRÉALABLE: Corriger les nombres coupés dans le contenu Markdown
        # Corriger "4 645,50" et "631 €/m²" en "4 645 506,31 €/m²"
        content = re.sub(
            r'4 645,50\s*631\s*€/m²',
            r'**4 645 506,31 €/m²**',
            content
        )
        
        # Corriger les calculs avec nombres coupés
        content = re.sub(
            r'\(4 645\s*506,31\s*€\s*/\s*4 645,50\s*631\s*€/m²\)',
            r'(**4 645 506,31 €** / **4 645 506,31 €/m²**)',
            content
        )
        
        # CORRECTION PRÉALABLE: Corriger les listes de CA mensuels
        # Remplacer les * par des vraies puces Markdown
        content = re.sub(
            r'\*\s+\*\*([^:]+):\*\*\s*([^€]*€[^*]*)',
            r'* **\1:** \2',
            content
        )
        
        # Diviser le SWOT en deux tableaux séparés
        content = self.split_swot_table(content)
        
        # Mieux détecter les sections avec icônes
        content = re.sub(
            r'^(#{1,3})\s*(.*?CONTEXTE.*?)$',
            r'\1 <span class="section-icon">🏢</span> \2',
            content, flags=re.MULTILINE | re.IGNORECASE
        )
        
        content = re.sub(
            r'^(#{1,3})\s*(.*?CIBLES.*?)$',
            r'\1 <span class="section-icon">👥</span> \2',
            content, flags=re.MULTILINE | re.IGNORECASE
        )
        
        content = re.sub(
            r'^(#{1,3})\s*(.*?POTENTIEL.*?)$',
            r'\1 <span class="section-icon">📈</span> \2',
            content, flags=re.MULTILINE | re.IGNORECASE
        )
        
        content = re.sub(
            r'^(#{1,3})\s*(.*?OFFRE.*?)$',
            r'\1 <span class="section-icon">🛍️</span> \2',
            content, flags=re.MULTILINE | re.IGNORECASE
        )
        
        # Traiter les sections numérotées (I., II., III.)
        content = re.sub(
            r'^(#{1,3})\s*([IVX]+\.|[0-9]+\.)\s*(.+)$',
            r'\1 <span class="section-number">\2</span> <span class="section-title">\3</span>',
            content, flags=re.MULTILINE
        )
        
        # Améliorer les actions
        content = re.sub(
            r'^(Action|Proposition|Objectif|Recommandation)\s*:\s*(.+)$',
            r'<div class="action-box"><strong class="action-label">\1:</strong> \2</div>',
            content, flags=re.MULTILINE
        )

        # CORRECTION 1: Détecter et convertir les montants en gras (**montant**)
        # Amélioration pour capturer les grands nombres complets
        content = re.sub(
            r'\*\*(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.]\d{2})?)\s*(€|K€|M€)\*\*',
            r'<span class="metric-highlight">\1 \2</span>',
            content
        )
        
        # CORRECTION 2: Détecter les montants avec espaces et virgules (amélioré)
        # Pattern plus robuste pour éviter de couper les grands nombres
        content = re.sub(
            r'(?<!<span class="metric-highlight">)(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.]\d{2})?)\s*(€|K€|M€)(?!</span>)',
            r'<span class="metric-highlight">\1 \2</span>',
            content
        )
        
        # CORRECTION 2bis: Détecter les montants avec espaces dans les nombres
        # Pattern spécifique pour les nombres avec espaces comme "4 645 506,31"
        content = re.sub(
            r'(?<!<span class="metric-highlight">)(\d{1,3}(?:\s\d{3})*(?:,\d{2})?)\s*(€|K€|M€)(?!</span>)',
            r'<span class="metric-highlight">\1 \2</span>',
            content
        )
        
        # CORRECTION 2ter: Corriger les nombres coupés comme "4 645,50" et "631 €/m²"
        # Détecter et corriger les patterns problématiques
        content = re.sub(
            r'(\d{1,3}(?:\s\d{3})*),\d{2}\s*(\d{3})\s*(€/m²)',
            r'<span class="metric-highlight">\1 \2 \3</span>',
            content
        )
        
        # CORRECTION 2quater: Corriger les calculs avec nombres coupés
        content = re.sub(
            r'(\d{1,3}(?:\s\d{3})*)\s*(\d{3},\d{2})\s*(€)',
            r'<span class="metric-highlight">\1 \2 \3</span>',
            content
        )
        
        # CORRECTION 2quinquies: Correction spécifique pour la rentabilité par m²
        # Corriger "4 645,50" et "631 €/m²" en "4 645 506,31 €/m²"
        content = re.sub(
            r'(\d{1,3}(?:\s\d{3})*),\d{2}\s*(\d{3})\s*(€/m²)',
            r'<span class="metric-highlight">\1 \2,31 \3</span>',
            content
        )
        
        # CORRECTION 2sexies: Correction pour les calculs dans les parenthèses
        content = re.sub(
            r'\((\d{1,3}(?:\s\d{3})*)\s*(\d{3},\d{2})\s*(€)\s*/\s*(\d{1,3}(?:\s\d{3})*),\d{2}\s*(\d{3})\s*(€/m²)\)',
            r'(<span class="metric-highlight">\1 \2 \3</span> / <span class="metric-highlight">\4 \5,31 \6</span>)',
            content
        )
        
        # Chiffres avec unités (habitants, commerces, m², etc.)
        content = re.sub(
            r'(?<!<span class="metric-highlight">)(\d{1,3}(?:[,\.\s]\d{3})*)\s*(habitants?|commerces?|m²|km²)(?!</span>)',
            r'<span class="metric-highlight">\1 \2</span>',
            content
        )
        
        # Pourcentages
        content = re.sub(
            r'(?<!<span class="metric-highlight">)(\d{1,3}(?:[,\.]\d{1,2})?)\s*(%)(?!</span>)',
            r'<span class="metric-highlight">\1\2</span>',
            content
        )
        
        # Ratios et surfaces (ex: 3944€/m²)
        content = re.sub(
            r'(?<!<span class="metric-highlight">)(\d{1,3}(?:[,\.]\d{3})*)\s*(€/m²)(?!</span>)',
            r'<span class="metric-highlight">\1 \2</span>',
            content
        )
        
        # CORRECTION 3: Améliorer le formatage des listes à puces
        # S'assurer que les listes sont bien formatées avec des puces
        content = re.sub(
            r'^\*\s+\*\*([^:]+):\*\*\s*([^€]*€)',
            r'* **\1:** <span class="metric-highlight">\2</span>',
            content, flags=re.MULTILINE
        )
        
        # CORRECTION 4: Corriger le formatage des listes de CA mensuels
        # Convertir les listes avec * en listes Markdown correctes
        content = re.sub(
            r'^\*\s+\*\*([^:]+):\*\*\s*([^€]*€)(.*?)$',
            r'* **\1:** <span class="metric-highlight">\2</span>\3',
            content, flags=re.MULTILINE
        )
        
        # CORRECTION 5: S'assurer que les listes sont bien structurées
        # Remplacer les * par des - pour une meilleure compatibilité
        content = re.sub(
            r'^\*\s+([^:]+):\s*([^€]*€)(.*?)$',
            r'* **\1:** <span class="metric-highlight">\2</span>\3',
            content, flags=re.MULTILINE
        )
        
        # CORRECTION 6: Traitement spécial pour les listes de CA mensuels
        # Détecter et convertir les listes de CA mensuels en vraies listes Markdown
        def convert_monthly_ca_to_list(match):
            text = match.group(0)
            # Remplacer les * par des vraies puces Markdown
            text = re.sub(r'\*\s+\*\*([^:]+):\*\*\s*([^€]*€)(.*?)(?=\*|$)', 
                         r'\n* **\1:** <span class="metric-highlight">\2</span>\3', 
                         text, flags=re.MULTILINE)
            return text
        
        # Appliquer la conversion aux paragraphes contenant des listes de CA mensuels
        content = re.sub(
            r'<p>L\'analyse des flux de chiffre d\'affaires mensuels.*?</p>',
            convert_monthly_ca_to_list,
            content,
            flags=re.DOTALL
        )
        
        # Corriger les problèmes de tabulation dans les listes
        content = re.sub(r'<li>\s*<strong>([^<]+):</strong>\s*</li>', r'<li><strong>\1:</strong></li>', content)
        content = re.sub(r'<li>\s*<strong>([^<]+)</strong>\s*([^<]+)</li>', r'<li><strong>\1</strong> \2</li>', content)
        
        # Nettoyer les espaces multiples et améliorer la lisibilité
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'<p>\s*</p>', '', content)
            
        return content

    def split_swot_table(self, content: str) -> str:
        """Divise le tableau SWOT en deux tableaux séparés pour une meilleure lisibilité."""
        
        # Pattern pour détecter le tableau SWOT complet (générique pour toutes les langues)
        swot_pattern = r'<table>\s*<tr>\s*<th>.*?FORCES.*?</th>\s*<th>.*?FAIBLESSES.*?</th>\s*</tr>.*?</table>'
        
        def replace_swot(match):
            swot_content = match.group(0)
            
            # Extraire les forces et faiblesses (générique)
            forces_weaknesses = re.search(r'<tr>\s*<th>.*?FORCES.*?</th>\s*<th>.*?FAIBLESSES.*?</th>\s*</tr>(.*?)<tr>\s*<th>.*?OPPORTUNITÉS', swot_content, re.DOTALL | re.IGNORECASE)
            
            # Extraire les opportunités et menaces (générique)
            opportunities_threats = re.search(r'<tr>\s*<th>.*?OPPORTUNITÉS.*?</table>', swot_content, re.DOTALL | re.IGNORECASE)
            
            if forces_weaknesses and opportunities_threats:
                # Extraire les titres originaux pour les conserver
                forces_title = re.search(r'<th>(.*?FORCES.*?)</th>', swot_content, re.IGNORECASE)
                faiblesses_title = re.search(r'<th>.*?FORCES.*?</th>\s*<th>(.*?FAIBLESSES.*?)</th>', swot_content, re.IGNORECASE)
                opportunites_title = re.search(r'<th>(.*?OPPORTUNITÉS.*?)</th>', swot_content, re.IGNORECASE)
                menaces_title = re.search(r'<th>.*?OPPORTUNITÉS.*?</th>\s*<th>(.*?MENACES.*?)</th>', swot_content, re.IGNORECASE)
                
                # Nettoyer le contenu des opportunités/menaces
                opp_threats_content = opportunities_threats.group(0)
                opp_threats_content = re.sub(r'<tr>\s*<th>.*?OPPORTUNITÉS.*?</th>\s*<th>.*?MENACES.*?</th>\s*</tr>', '', opp_threats_content, flags=re.IGNORECASE)
                
                # Créer les tableaux avec les titres originaux
                forces_title_text = forces_title.group(1) if forces_title else "FORCES"
                faiblesses_title_text = faiblesses_title.group(1) if faiblesses_title else "FAIBLESSES"
                opportunites_title_text = opportunites_title.group(1) if opportunites_title else "OPPORTUNITÉS"
                menaces_title_text = menaces_title.group(1) if menaces_title else "MENACES"
                
                table1 = f'''<table>
<tr>
<th style="background: linear-gradient(135deg, #0082C3, #003d82); color: white; padding: 0.8cm 0.6cm; font-weight: bold; text-align: left; font-size: 11pt; text-transform: uppercase; letter-spacing: 0.5px; border-right: 2px solid #003d82; border-bottom: 2px solid #003d82;">{forces_title_text}</th>
<th style="background: linear-gradient(135deg, #0082C3, #003d82); color: white; padding: 0.8cm 0.6cm; font-weight: bold; text-align: left; font-size: 11pt; text-transform: uppercase; letter-spacing: 0.5px; border-right: 2px solid #003d82; border-bottom: 2px solid #003d82;">{faiblesses_title_text}</th>
</tr>
{forces_weaknesses.group(1)}
</table>

<p style="margin: 1cm 0;"></p>

<table>
<tr>
<th style="background: linear-gradient(135deg, #0082C3, #003d82); color: white; padding: 0.8cm 0.6cm; font-weight: bold; text-align: left; font-size: 11pt; text-transform: uppercase; letter-spacing: 0.5px; border-right: 2px solid #003d82; border-bottom: 2px solid #003d82;">{opportunites_title_text}</th>
<th style="background: linear-gradient(135deg, #0082C3, #003d82); color: white; padding: 0.8cm 0.6cm; font-weight: bold; text-align: left; font-size: 11pt; text-transform: uppercase; letter-spacing: 0.5px; border-right: 2px solid #003d82; border-bottom: 2px solid #003d82;">{menaces_title_text}</th>
</tr>
{opp_threats_content}'''
                
                return table1
            
            return match.group(0)
        
        # Appliquer la transformation
        content = re.sub(swot_pattern, replace_swot, content, flags=re.DOTALL)
        
        return content
    
    def create_decathlon_css(self) -> str:
        """Crée le CSS Decathlon intégré."""
        
        return f"""
        <style>
        /* ==================== PAGE SETUP ==================== */
        @page {{
            size: A4;
            margin: 15mm 10mm 20mm 10mm;
            
            @top-left {{
                content: "POLITIQUE COMMERCIALE";
                font-family: "Helvetica Neue", Arial, sans-serif;
                font-size: 8pt;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            @top-right {{
                content: "POLCO ANALYZER 3.0";
                font-family: Arial, sans-serif;
                font-size: 9pt;
                color: {COLORS['blue_primary']};
                font-weight: bold;
                padding-bottom: 0.5cm;
            }}
            
            @bottom-center {{
                content: "Page " counter(page);
                font-family: Arial, sans-serif;
                font-size: 8pt;
                color: {COLORS['text_light']};
                padding-top: 0.5cm;
                border-top: 1px solid {COLORS['border_light']};
            }}
            
            @bottom-right {{
                content: "© 2025 Decathlon";
                font-family: Arial, sans-serif;
                font-size: 8pt;
                color: {COLORS['text_light']};
                padding-top: 0.5cm;
            }}
        }}
        
        /* Page couverture sans en-têtes/pieds */
        @page cover {{
            margin: 0;
            @top-left {{ content: none; }}
            @top-right {{ content: none; }}
            @bottom-center {{ content: none; }}
            @bottom-right {{ content: none; }}
        }}
        
        /* ==================== BASE ==================== */
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: {COLORS['text_dark']};
            margin: 0;
            padding: 0;
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
        
        /* ==================== COUVERTURE AMÉLIORÉE ==================== */
        .cover-page {{
            page: cover;
            height: 297mm;
            background: linear-gradient(135deg, {COLORS['blue_primary']} 0%, {COLORS['blue_dark']} 100%);
            color: white !important;
            position: relative;
            padding: 40px;
            overflow: hidden;
        }}
        
        .cover-page::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="20" cy="20" r="2" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="40" r="1.5" fill="rgba(255,255,255,0.08)"/><circle cx="40" cy="80" r="1" fill="rgba(255,255,255,0.06)"/></svg>');
            opacity: 0.3;
        }}
        
        .cover-logo {{
            position: absolute;
            top: 25px;
            left: 25px;
            font-size: 18pt;
            font-weight: bold;
            color: white !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            z-index: 2;
        }}
        
        .cover-main {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            width: 85%;
            z-index: 2;
        }}
        
        .cover-title {{
            font-size: 32pt !important;
            font-weight: bold;
            color: white !important;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 3px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .cover-period {{
            font-size: 16pt !important;
            color: white !important;
            margin-bottom: 30px;
            font-weight: 300;
            opacity: 0.9;
        }}
        
        .dragons-badge {{
            display: none;
        }}
        
        .cover-footer {{
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 12pt;
            color: white !important;
            text-align: center;
        }}
        
        /* ==================== SOMMAIRE ==================== */
        .toc-page {{
            page-break-after: always;
        }}
        
        .toc-title {{
            color: {COLORS['blue_primary']};
            font-size: 32pt;
            font-weight: bold;
            text-align: center;
            margin-bottom: 2cm;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        
        .toc-content {{
            max-width: 80%;
            margin: 0 auto;
        }}
        
        .toc-section-title {{
            color: {COLORS['blue_primary']};
            font-size: 16pt;
            font-weight: bold;
            margin: 1cm 0 0.5cm 0;
            padding: 0.5cm 0;
            border-bottom: 2px solid {COLORS['blue_primary']};
        }}
        
        .toc-subsection {{
            color: {COLORS['text_light']};
            font-size: 12pt;
            margin: 0.3cm 0 0.3cm 1cm;
            padding: 0.2cm 0;
            border-bottom: 1px dotted {COLORS['border_light']};
        }}
        
        /* ==================== HEADERS AMÉLIORÉS ==================== */
        h1 {{
            color: {COLORS['blue_primary']} !important;
            font-size: 16pt;
            font-weight: bold;
            margin: 20px 0 12px 0;
            padding: 12px 15px;
            background: linear-gradient(135deg, rgba(0,130,195,0.1) 0%, rgba(0,130,195,0.05) 100%);
            border-left: 6px solid {COLORS['blue_primary']} !important;
            border-radius: 0 8px 8px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
            page-break-after: avoid;
            box-shadow: 0 2px 4px rgba(0,130,195,0.1);
        }}
        
        h2 {{
            color: {COLORS['green']} !important;
            font-size: 14pt;
            font-weight: bold;
            margin: 18px 0 10px 0;
            padding: 10px 12px;
            background: linear-gradient(90deg, rgba(0,166,81,0.08) 0%, transparent 100%);
            border-left: 4px solid {COLORS['green']} !important;
            border-radius: 0 6px 6px 0;
            page-break-after: avoid;
            position: relative;
        }}
        
        h2::before {{
            content: "►";
            color: {COLORS['green']};
            margin-right: 8px;
            font-size: 12pt;
        }}
        
        h3 {{
            color: {COLORS['orange']} !important;
            font-size: 12pt;
            font-weight: bold;
            margin: 15px 0 8px 0;
            padding: 6px 10px;
            background: linear-gradient(90deg, rgba(255,105,0,0.06) 0%, transparent 100%);
            border-left: 3px solid {COLORS['orange']} !important;
            border-radius: 0 4px 4px 0;
            page-break-after: avoid;
        }}
        
        h4 {{
            color: {COLORS['text_dark']};
            font-size: 11pt;
            font-weight: bold;
            margin: 0.6cm 0 0.3cm 0;
            page-break-after: avoid;
        }}
        
        /* ==================== SECTIONS SPÉCIALES ==================== */
        .section-number {{
            font-size: 24pt;
            font-weight: bold;
            color: {COLORS['blue_primary']};
            opacity: 0.8;
            margin-right: 0.3cm;
        }}
        
        .section-title {{
            font-size: 14pt;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* ==================== MÉTRIQUES ==================== */
        .metric {{
            background: linear-gradient(135deg, {COLORS['blue_primary']}, {COLORS['green']});
            color: white;
            padding: 0.2cm 0.4cm;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12pt;
            margin: 0 0.2cm;
            white-space: nowrap;
        }}
        
        /* ==================== ACTIONS ==================== */
        .action-box {{
            background: linear-gradient(90deg, rgba(255,105,0,0.1) 0%, transparent 100%);
            border-left: 5px solid {COLORS['orange']};
            padding: 0.8cm;
            margin: 0.8cm 0;
            border-radius: 0 8px 8px 0;
            page-break-inside: avoid;
        }}
        
        .action-label {{
            color: {COLORS['orange']};
            font-size: 13pt;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        /* ==================== TABLEAUX ==================== */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1cm 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 2px solid {COLORS['blue_primary']};
        }}
        
        th {{
            background: linear-gradient(135deg, {COLORS['blue_primary']}, {COLORS['blue_dark']});
            color: white;
            padding: 0.8cm 0.6cm;
            font-weight: bold;
            text-align: left;
            font-size: 11pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-right: 2px solid {COLORS['blue_dark']};
            border-bottom: 2px solid {COLORS['blue_dark']};
        }}
        
        th:last-child {{
            border-right: none;
        }}
        
        td {{
            padding: 0.6cm;
            border-bottom: 2px solid {COLORS['border_light']};
            border-right: 2px solid {COLORS['border_light']};
            font-size: 10pt;
            vertical-align: top;
        }}
        
        td:last-child {{
            border-right: none;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:nth-child(even) {{
            background: rgba(0,130,195,0.05);
        }}
        
        tr:hover {{
            background: rgba(0,130,195,0.1);
        }}
        
        /* ==================== LISTES ==================== */
        ul {{
            margin: 0.4cm 0;
            padding-left: 1cm;
            list-style: none;
        }}

        ul li {{
            position: relative;
            padding: 0.1cm 0 0.1cm 0.6cm;
            margin-bottom: 0.15cm;
            line-height: 1.3;
        }}

        ul li::before {{
            content: "▶";
            color: #00529B;
            font-weight: bold;
            position: absolute;
            left: -0.8cm;
            top: 0.1cm;
            font-size: 9pt;
        }}

        ul ul {{
            margin: 0.15cm 0;
        }}

        ul ul li {{
            margin-bottom: 0.1cm;
            font-size: 9pt;
        }}

        ul ul li::before {{
            content: "▸";
            color: #4CAF50;
            font-size: 8pt;
        }}

        ul ul ul {{
            margin: 0.1cm 0;
        }}

        ul ul ul li {{
            margin-bottom: 0.08cm;
            font-size: 8pt;
        }}

        ul ul ul li::before {{
            content: "•";
            color: #FF9800;
            font-size: 7pt;
        }}

        
        /* ==================== NOUVEAUX STYLES COUVERTURE ==================== */
        .cover-logo {{
            position: absolute;
            top: 2cm;
            left: 2cm;
            display: flex;
            align-items: center;
            gap: 1cm;
        }}
        
        .decathlon-logo {{
            font-size: 24pt;
            font-weight: bold;
            color: white;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        
        .dragons-badge {{
            font-size: 20pt;
            background: rgba(255,255,255,0.2);
            padding: 0.3cm 0.6cm;
            border-radius: 15px;
            border: 2px solid rgba(255,255,255,0.3);
        }}
        
        .cover-period {{
            font-size: 16pt;
            font-weight: 300;
            margin: 1cm 0 2cm 0;
            opacity: 0.9;
        }}
        
        .city-silhouette {{
            height: 80px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            margin: 2cm 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36pt;
            opacity: 0.7;
        }}
        
        /* ==================== NOUVEAUX STYLES SOMMAIRE ==================== */
        .toc-header {{
            text-align: center;
            margin-bottom: 2cm;
        }}
        
        .decathlon-logo-small {{
            font-size: 14pt;
            font-weight: bold;
            color: {COLORS['blue_primary']};
            margin-bottom: 0.5cm;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .toc-grid {{
            width: 100%;
            display: table;
        }}
        
        .toc-column-left, .toc-column-right {{
            display: table-cell;
            width: 50%;
            vertical-align: top;
            padding: 0 30px;
        }}
        
        .toc-section {{
            margin-bottom: 30px;
            page-break-inside: avoid;
        }}
        
        .toc-section h3 {{
            color: {COLORS['blue_primary']} !important;
            font-size: 14pt;
            margin-bottom: 10px;
            border-bottom: 2px solid {COLORS['blue_primary']} !important;
            padding-bottom: 5px;
        }}
        
        .toc-section ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .toc-section li {{
            padding: 0.2cm 0 0.2cm 0.8cm;
            border-bottom: 1px dotted {COLORS['border_light']};
            font-size: 11pt;
            margin-left: 0.5cm;
        }}
        
        /* ==================== CARTES D'INFORMATION AMÉLIORÉES ==================== */
        .info-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-left: 4px solid {COLORS['green']};
            padding: 0.8cm;
            margin: 0.8cm 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            page-break-inside: avoid;
            position: relative;
        }}
        
        .info-card:nth-child(even) {{
            border-left-color: {COLORS['blue_primary']};
            background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
        }}
        
        .info-card:nth-child(3n) {{
            border-left-color: {COLORS['orange']};
            background: linear-gradient(135deg, #fff8f0 0%, #ffe6cc 100%);
        }}
        
        .info-icon {{
            font-size: 14pt;
            margin-right: 0.4cm;
            vertical-align: middle;
            display: inline-block;
            width: 20px;
            text-align: center;
        }}
        
        /* Cartes démographiques spéciales */
        .demographic-card {{
            background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
            border-left: 4px solid {COLORS['green']};
            padding: 0.6cm;
            margin: 0.6cm 0;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            page-break-inside: avoid;
        }}
        
        .demographic-card .info-icon {{
            color: {COLORS['green']};
            font-size: 12pt;
        }}
        
        /* ==================== MÉTRIQUES CORRIGÉES ==================== */
        .metric-highlight {{
            color: {COLORS['blue_primary']} !important;
            font-weight: bold !important;
            font-size: 10pt;
            display: inline;
            margin: 0 1px;
            line-height: 1.2;
            background: rgba(0,130,195,0.1);
            padding: 1px 3px;
            border-radius: 3px;
        }}
        
        /* Métriques dans les listes */
        ul li .metric-highlight {{
            color: {COLORS['blue_primary']} !important;
            font-weight: bold !important;
            background: rgba(0,130,195,0.08);
            padding: 1px 2px;
        }}
        
        /* ==================== ICÔNES DE SECTION ==================== */
        .section-icon {{
            font-size: 24pt;
            margin-right: 0.5cm;
            vertical-align: middle;
        }}
        
        /* ==================== UTILITAIRES ==================== */
        .page-break {{
            page-break-after: always;
        }}
        
        .no-break {{
            page-break-inside: avoid;
        }}
        
        /* ==================== RESPONSIVENESS ==================== */
        @media print {{
            body {{ 
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
            
            table, th, td {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
            
            .metric-highlight, .action-box, .info-card, .demographic-card {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
            
            h1, h2, h3 {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
            
            .cover-page {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
        }}
        
        /* Forcer les dégradés pour wkhtmltopdf */
        h1 {{
            background: linear-gradient(135deg, rgba(0,130,195,0.1) 0%, rgba(0,130,195,0.05) 100%) !important;
        }}
        
        h2 {{
            background: linear-gradient(90deg, rgba(0,166,81,0.08) 0%, transparent 100%) !important;
        }}
        
        h3 {{
            background: linear-gradient(90deg, rgba(255,105,0,0.06) 0%, transparent 100%) !important;
        }}
        
        .cover-page {{
            background: linear-gradient(135deg, {COLORS['blue_primary']} 0%, {COLORS['blue_dark']} 100%) !important;
        }}
        
        .info-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
        }}
        
        .info-card:nth-child(even) {{
            background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%) !important;
        }}
        
        .info-card:nth-child(3n) {{
            background: linear-gradient(135deg, #fff8f0 0%, #ffe6cc 100%) !important;
        }}
        
        .demographic-card {{
            background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%) !important;
        }}
        
        th {{
            background: linear-gradient(135deg, {COLORS['blue_primary']}, {COLORS['blue_dark']}) !important;
        }}
        
        /* Fallback pour les navigateurs qui ne supportent pas les dégradés */
        @supports not (background: linear-gradient(0deg, #000, #fff)) {{
            h1 {{
                background-color: rgba(0,130,195,0.1) !important;
            }}
            
            h2 {{
                background-color: rgba(0,166,81,0.08) !important;
            }}
            
            h3 {{
                background-color: rgba(255,105,0,0.06) !important;
            }}
            
            .cover-page {{
                background-color: {COLORS['blue_primary']} !important;
            }}
            
            .info-card {{
                background-color: #f8f9fa !important;
            }}
            
            .info-card:nth-child(even) {{
                background-color: #f0f8ff !important;
            }}
            
            .info-card:nth-child(3n) {{
                background-color: #fff8f0 !important;
            }}
            
            .demographic-card {{
                background-color: #e8f5e8 !important;
            }}
            
            th {{
                background-color: {COLORS['blue_primary']} !important;
            }}
        }}
        </style>
        """
    
    def markdown_to_html(self, markdown_content: str, store_id: str, store_name: str, language: str) -> str:
        """Convertit le Markdown en HTML enrichi."""
        
        # Créer la page de couverture (essayer SVG d'abord)
        cover_html = self.create_cover_image_svg(store_name, language)
        
        # Créer le sommaire
        toc_html = self.extract_toc(markdown_content, language)
        
        # Améliorer le contenu
        enhanced_content = self.enhance_content(markdown_content)
        
        # Conversion basique Markdown vers HTML
        # (ici on fait une conversion simple, vous pouvez utiliser une lib comme markdown si besoin)
        html_content = self.simple_markdown_to_html(enhanced_content)
        
        # Créer le document HTML complet
        full_html = f"""
        <!DOCTYPE html>
        <html lang="{language}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Politique Commerciale - Magasin {store_name}</title>
            {self.create_decathlon_css()}
        </head>
        <body>
            {cover_html}
            {toc_html}
            <div class="content">
                {html_content}
            </div>
        </body>
        </html>
        """
        
        # Nettoyer le HTML final
        full_html = self.clean_html_content(full_html)
        
        return full_html
    
    def simple_markdown_to_html(self, markdown: str) -> str:
        """Convertit le Markdown en HTML en utilisant la librairie markdown."""
        # Utiliser la librairie markdown pour la conversion
        html = self.convert_markdown_to_html(markdown)
        
        # Post-traitement pour les styles spécifiques Decathlon
        html = self.enhance_content(html)
        
        return html
    
    def convert_tables(self, text: str) -> str:
        """Convertit les tableaux Markdown en HTML."""
        lines = text.split('\n')
        result = []
        in_table = False
        is_header = True
        
        for line in lines:
            line = line.strip()
            
            # Détecter les séparateurs de colonnes
            if line.startswith('|--') or line.startswith('| -'):
                continue  # Ignorer les lignes de séparation
                
            # Détecter les lignes de tableau
            if '|' in line and line.count('|') >= 2:
                if not in_table:
                    result.append('<table>')
                    in_table = True
                    is_header = True
                
                # Nettoyer et extraire les cellules
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                
                if is_header:
                    result.append('<tr>')
                    for cell in cells:
                        result.append(f'<th>{cell}</th>')
                    result.append('</tr>')
                    is_header = False
                else:
                    result.append('<tr>')
                    for cell in cells:
                        result.append(f'<td>{cell}</td>')
                    result.append('</tr>')
            else:
                # Ligne non-tableau
                if in_table:
                    result.append('</table>')
                    in_table = False
                    is_header = True
                
                if line:  # Ajouter la ligne si elle n'est pas vide
                    result.append(line)
        
        # Fermer le tableau s'il est encore ouvert
        if in_table:
            result.append('</table>')
        
        return '\n'.join(result)
    
    def convert_markdown_to_html(self, text: str) -> str:
        """Convertit le Markdown en HTML en utilisant la librairie markdown."""
        # Configuration de markdown avec extensions pour les listes et tableaux
        md = markdown.Markdown(
            extensions=[
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.codehilite',
                'markdown.extensions.nl2br',
                'markdown.extensions.sane_lists'  # Gestion améliorée des listes
            ]
        )
        
        # Convertir le Markdown en HTML
        html = md.convert(text)
        
        # Post-traitement pour appliquer les styles Decathlon
        html = self.apply_decathlon_styles(html)
        
        return html
    
    def apply_decathlon_styles(self, html: str) -> str:
        """Applique les styles Decathlon spécifiques au HTML généré."""
        # Appliquer les classes CSS pour les métriques
        html = re.sub(
            r'<strong>([^<]*\d+[^<]*)</strong>',
            r'<span class="metric-highlight">\1</span>',
            html
        )
        
        # Nettoyer les espaces multiples
        html = re.sub(r'\n\s*\n', '\n\n', html)
        
        return html
    
    def clean_html_content(self, html_content: str) -> str:
        """Nettoie le contenu HTML des artefacts et doublons."""
        
        # Supprimer les doublons de métriques
        html_content = re.sub(
            r'<span class="metric-highlight"><span class="metric-highlight">([^<]+)</span></span>',
            r'<span class="metric-highlight">\1</span>',
            html_content
        )
        
        # CORRECTION: Nettoyer les métriques dans les listes
        html_content = re.sub(
            r'<li><strong>([^<]+):</strong>\s*([^<]*€[^<]*)</li>',
            r'<li><strong>\1:</strong> <span class="metric-highlight">\2</span></li>',
            html_content
        )
        
        # Supprimer les balises p vides
        html_content = re.sub(r'<p>\s*</p>', '', html_content)
        
        # Nettoyer les espaces multiples
        html_content = re.sub(r'\s+', ' ', html_content)
        
        # Nettoyer les sauts de ligne multiples
        html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)
        
        # Supprimer les artefacts de traitement
        html_content = re.sub(r'<p></ul></p>', '</ul>', html_content)
        html_content = re.sub(r'<p></ol></p>', '</ol>', html_content)
        
        # Nettoyer les métriques mal formatées
        html_content = re.sub(r'(\d+)\s*\.\s*(\d+)\s*([€%])', r'\1,\2\3', html_content)
        
        # CORRECTION: S'assurer que les listes sont bien formatées
        html_content = re.sub(
            r'<ul>\s*<li>\s*<strong>([^<]+):</strong>\s*([^<]*€[^<]*)</li>',
            r'<ul><li><strong>\1:</strong> <span class="metric-highlight">\2</span></li>',
            html_content
        )
        
        # CORRECTION: Nettoyer les listes mal formatées
        html_content = re.sub(
            r'<p>\s*\*\s+([^:]+):\s*([^€]*€[^<]*)</p>',
            r'<ul><li><strong>\1:</strong> <span class="metric-highlight">\2</span></li></ul>',
            html_content
        )
        
        # CORRECTION: Convertir les listes en paragraphes en vraies listes
        html_content = re.sub(
            r'<p>\s*([^<]*\*\s+[^<]*€[^<]*)</p>',
            r'<ul><li>\1</li></ul>',
            html_content
        )
        
        # CORRECTION: Traitement spécial pour les listes de CA mensuels
        # Détecter les paragraphes contenant des listes de CA mensuels et les convertir
        def fix_monthly_ca_lists(match):
            text = match.group(0)
            # Remplacer le paragraphe par une vraie liste HTML
            text = re.sub(r'<p>L\'analyse des flux de chiffre d\'affaires mensuels.*?:\s*', 
                         r'<p>L\'analyse des flux de chiffre d\'affaires mensuels sur les douze derniers mois révèle une saisonnalité marquée :</p>\n<ul>', 
                         text, flags=re.DOTALL)
            
            # Convertir chaque ligne de CA en élément de liste
            text = re.sub(r'\*\s+\*\*([^:]+):\*\*\s*([^€]*€)(.*?)(?=\*|</p>)', 
                         r'<li><strong>\1:</strong> <span class="metric-highlight">\2</span>\3</li>', 
                         text, flags=re.MULTILINE)
            
            # Fermer la liste
            text = re.sub(r'</p>$', r'</ul>', text)
            return text
        
        html_content = re.sub(
            r'<p>L\'analyse des flux de chiffre d\'affaires mensuels.*?</p>',
            fix_monthly_ca_lists,
            html_content,
            flags=re.DOTALL
        )
        
        return html_content
    
    def debug_html_output(self, html_content: str, store_id: str):
        """Sauvegarde le HTML pour debug."""
        debug_path = os.path.join(self.output_dir, f"debug_{store_id}.html")
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"🔍 HTML de debug sauvé: {debug_path}")
        
        # Ouvrir automatiquement dans le navigateur pour vérification
        try:
            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(debug_path)}")
        except Exception:
            pass  # Ignore si pas de navigateur disponible

    async def generate_pdf_pyppeteer(self, html_content: str, output_path: str, store_id: str = None) -> bool:
        """Génère le PDF avec pyppeteer."""
        
        # Créer fichier HTML temporaire
        temp_html = os.path.join(self.output_dir, "temp_report.html")
        
        # Debug: sauvegarder le HTML
        if store_id:
            self.debug_html_output(html_content, store_id)
        
        try:
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Lancer le navigateur
            browser = await launch()
            page = await browser.newPage()
            
            # Charger le fichier HTML local
            file_url = f"file://{os.path.abspath(temp_html)}"
            await page.goto(file_url, waitUntil='networkidle0')
            
            # Attendre que le contenu soit complètement chargé
            await page.waitFor(2000)
            
            # Générer le PDF avec des options optimisées pour le contenu
            await page.pdf({
                'path': output_path, 
                'format': 'A4',
                'printBackground': True,
                'margin': {
                    'top': '15mm',
                    'right': '10mm', 
                    'bottom': '20mm',
                    'left': '10mm'
                }
            })
            
            await browser.close()
            
            logger.info(f"✅ PDF créé avec pyppeteer: {os.path.basename(output_path)}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Erreur pyppeteer: {e}")
            return False
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_html):
                os.remove(temp_html)
    
    async def process_single_report(self, markdown_path: str) -> bool:
        """Traite un rapport Markdown vers PDF."""
        
        filename = os.path.basename(markdown_path)
        logger.info(f"📄 Traitement: {filename}")
        
        try:
            # Lire le fichier Markdown
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Extraire les infos du magasin
            store_id, store_name = self.extract_store_info(filename, markdown_content)
            
            # Détecter la langue
            language = self.detect_language(markdown_content)
            logger.info(f"🌍 Magasin {store_id} ({store_name}) - Langue: {language}")
            
            # Définir le fichier de sortie
            output_filename = f"POLITIQUE_COMMERCIALE_Magasin_{store_id}.pdf"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Générer le HTML et le PDF avec pyppeteer
            if 'pyppeteer' in self.available_tools:
                html_content = self.markdown_to_html(markdown_content, store_id, store_name, language)
                
                if await self.generate_pdf_pyppeteer(html_content, output_path, store_id):
                    return True
            
            logger.error(f"❌ Échec génération PDF pour {store_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement {filename}: {e}")
            return False
    
    async def process_all_reports(self) -> Dict[str, Any]:
        """Traite tous les rapports disponibles."""
        
        # Trouver tous les fichiers Markdown
        markdown_files = []
        if os.path.exists(self.reports_dir):
            for file in os.listdir(self.reports_dir):
                if file.startswith('POLCO_3_0_DECATHLON_') and file.endswith('.md'):
                    markdown_files.append(os.path.join(self.reports_dir, file))
        
        if not markdown_files:
            logger.error(f"❌ Aucun rapport trouvé dans {self.reports_dir}")
            return {'success': 0, 'failed': 0, 'files': []}
        
        logger.info(f"📊 {len(markdown_files)} rapports à traiter")
        
        # Traiter chaque rapport
        results = {'success': 0, 'failed': 0, 'files': []}
        
        for markdown_path in sorted(markdown_files):
            if await self.process_single_report(markdown_path):
                results['success'] += 1
                filename = os.path.basename(markdown_path).replace('.md', '.pdf')
                results['files'].append(filename.replace('POLCO_3_0_DECATHLON_', 'POLITIQUE_COMMERCIALE_Magasin_'))
            else:
                results['failed'] += 1
        
        return results
    
    async def run(self, store_id: str = None) -> bool:
        """Lance la génération PDF."""
        
        if not self.available_tools:
            logger.error("❌ Aucun outil PDF disponible")
            return False
        
        logger.info("=" * 70)
        logger.info("📄 GÉNÉRATEUR PDF POLCO 3.0 - VERSION PYPETEER")
        logger.info("🎨 Design Decathlon Premium avec pyppeteer")
        logger.info("=" * 70)
        
        if store_id:
            # Traiter un magasin spécifique
            markdown_path = os.path.join(self.reports_dir, f"POLCO_3_0_DECATHLON_{store_id}_Analyse_Sectorielle.md")
            if os.path.exists(markdown_path):
                success = await self.process_single_report(markdown_path)
                logger.info(f"📄 Magasin {store_id}: {'✅ Succès' if success else '❌ Échec'}")
                return success
            else:
                logger.error(f"❌ Rapport introuvable pour magasin {store_id}")
                return False
        else:
            # Traiter tous les rapports
            results = await self.process_all_reports()
            
            # Résumé
            logger.info("\n" + "=" * 70)
            logger.info("📊 RÉSUMÉ GÉNÉRATION PDF")
            logger.info("=" * 70)
            
            if results['success'] > 0:
                logger.info(f"✅ {results['success']} PDFs générés avec succès")
                for filename in results['files']:
                    file_path = os.path.join(self.output_dir, filename)
                    if os.path.exists(file_path):
                        size_kb = os.path.getsize(file_path) // 1024
                        logger.info(f"   📄 {filename} ({size_kb} KB)")
                        
                logger.info(f"\n📁 Dossier de sortie: {self.output_dir}/")
                logger.info(f"🛠️ Outil utilisé: {self.available_tools[0]}")
                logger.info("🎨 Design: Couverture + Sommaire + Style Decathlon")
            
            if results['failed'] > 0:
                logger.error(f"❌ {results['failed']} PDFs ont échoué")
                
            return results['success'] > 0


async def main():
    """Point d'entrée principal."""
    
    import argparse
    parser = argparse.ArgumentParser(description='Générateur PDF POLCO 3.0 Pyppeteer')
    parser.add_argument('store_id', nargs='?', help='ID du magasin spécifique (optionnel)')
    args = parser.parse_args()
    
    generator = PolcoPDFGenerator()
    success = await generator.run(args.store_id)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())