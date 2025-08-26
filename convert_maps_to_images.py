#!/usr/bin/env python3
"""
Script pour convertir les cartes HTML en images PNG
"""

import os
import time
from pathlib import Path

# Import conditionnel pour éviter les erreurs si pas installé
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    print("⚠️ Playwright non disponible")
    HAS_PLAYWRIGHT = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    print("⚠️ Selenium non disponible")
    HAS_SELENIUM = False

def convert_with_playwright(html_file, output_file):
    """Convertit HTML vers PNG avec Playwright"""
    print(f"🎭 Conversion avec Playwright: {html_file}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        # Charger le fichier HTML
        file_url = f"file://{os.path.abspath(html_file)}"
        page.goto(file_url)
        
        # Attendre que la carte soit chargée (plus de temps)
        page.wait_for_timeout(5000)  # 5 secondes
        
        # Attendre que les tiles de la carte soient chargées
        try:
            page.wait_for_selector('.leaflet-tile-loaded', timeout=10000)
        except:
            print("⚠️ Timeout lors de l'attente des tiles, capture quand même")
        
        # Prendre une capture d'écran
        page.screenshot(path=output_file, full_page=True, quality=90)
        browser.close()
        
        print(f"✅ Image générée: {output_file}")
        return True

def convert_with_selenium(html_file, output_file):
    """Convertit HTML vers PNG avec Selenium"""
    print(f"🌐 Conversion avec Selenium: {html_file}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1400,900")
    chrome_options.add_argument("--disable-gpu")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Charger le fichier HTML
        file_url = f"file://{os.path.abspath(html_file)}"
        driver.get(file_url)
        
        # Attendre que la page soit chargée
        time.sleep(8)  # 8 secondes pour laisser le temps aux tiles de se charger
        
        # Prendre une capture d'écran
        driver.save_screenshot(output_file)
        
        print(f"✅ Image générée: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Selenium: {e}")
        return False
    finally:
        if driver:
            driver.quit()

def convert_html_to_png(html_file):
    """Convertit un fichier HTML en PNG"""
    if not os.path.exists(html_file):
        print(f"❌ Fichier HTML non trouvé: {html_file}")
        return False
    
    # Générer le nom du fichier PNG
    base_name = os.path.splitext(html_file)[0]
    png_file = f"{base_name}.png"
    
    # Essayer d'abord Playwright, puis Selenium
    if HAS_PLAYWRIGHT:
        try:
            convert_with_playwright(html_file, png_file)
            return True
        except Exception as e:
            print(f"⚠️ Échec Playwright: {e}")
    
    if HAS_SELENIUM:
        try:
            return convert_with_selenium(html_file, png_file)
        except Exception as e:
            print(f"⚠️ Échec Selenium: {e}")
    
    print(f"❌ Impossible de convertir: {html_file}")
    return False

def main():
    """Convertit tous les fichiers HTML du dossier geo_maps en PNG"""
    
    print("🗺️ Conversion des cartes HTML en images PNG")
    print("=" * 50)
    
    geo_maps_dir = Path("geo_maps")
    
    if not geo_maps_dir.exists():
        print(f"❌ Dossier {geo_maps_dir} non trouvé")
        return
    
    # Trouver tous les fichiers HTML
    html_files = list(geo_maps_dir.glob("*.html"))
    
    if not html_files:
        print("❌ Aucun fichier HTML trouvé dans geo_maps/")
        return
    
    print(f"📁 {len(html_files)} fichiers HTML trouvés")
    
    success_count = 0
    
    for html_file in html_files:
        print(f"\n🔄 Conversion: {html_file.name}")
        
        if convert_html_to_png(html_file):
            success_count += 1
        else:
            print(f"❌ Échec conversion: {html_file.name}")
    
    print("\n" + "=" * 50)
    print(f"✅ Conversion terminée: {success_count}/{len(html_files)} fichiers convertis")
    
    if success_count > 0:
        print(f"📁 Images disponibles dans: {geo_maps_dir.absolute()}")

if __name__ == "__main__":
    main()