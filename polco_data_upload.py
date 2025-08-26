#!/usr/bin/env python3
"""
POLCO - Uploader de Données Magasin vers Firestore
Upload toutes les données magasin (data/ + store_data/) vers Firestore
"""

import os
import sys
import csv
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Configuration
PROJECT_ID = "polcoaigeneration-ved6"
COLLECTION_NAME = "polco_magasins_data"

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polco_data_upload.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PolcoDataUploader:
    """Uploader de données magasin vers Firestore."""
    
    def __init__(self):
        """Initialise l'uploader."""
        self.project_id = PROJECT_ID
        self.collection_name = COLLECTION_NAME
        self.db = None
        self.store_names = {}  # Cache pour les noms de magasins
        self.stats = {
            'stores_processed': 0,
            'stores_success': 0,
            'stores_failed': 0,
            'total_csv_files': 0,
            'total_md_files': 0,
            'start_time': None,
            'errors': []
        }
        
        logger.info("🚀 Initialisation de l'uploader de données magasin")
    
    def load_store_names(self) -> bool:
        """Charge les noms des magasins depuis le CSV principal."""
        csv_path = "polco_mag_test - Feuille 1.csv"
        
        if not os.path.exists(csv_path):
            logger.warning(f"⚠️ CSV principal {csv_path} non trouvé, noms de magasins non disponibles")
            return False
        
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    store_id = row.get('store_id', '').strip()
                    store_name = row.get('store_name', '').strip()
                    
                    if store_id and store_name:
                        self.store_names[store_id] = store_name
            
            logger.info(f"✅ {len(self.store_names)} noms de magasins chargés depuis {csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture CSV principal: {e}")
            return False
    
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
    
    def read_csv_file(self, csv_path: str) -> Optional[List[Dict]]:
        """Lit un fichier CSV et retourne les données."""
        try:
            data = []
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            return data
        except Exception as e:
            logger.warning(f"⚠️ Erreur lecture CSV {csv_path}: {e}")
            return None
    
    def read_txt_file(self, txt_path: str) -> Optional[str]:
        """Lit un fichier TXT et retourne le contenu."""
        try:
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"⚠️ Erreur lecture TXT {txt_path}: {e}")
            return None
    
    def read_md_file(self, md_path: str) -> Optional[str]:
        """Lit un fichier MD et retourne le contenu."""
        try:
            with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"⚠️ Erreur lecture MD {md_path}: {e}")
            return None
    
    def process_store_data_folder(self, store_id: str) -> Dict[str, Any]:
        """Traite le dossier data/[store_id] et retourne les données structurées."""
        
        data_folder = f"data/{store_id}"
        store_data = {
            'store_id': store_id,
            'internal_data': {},
            'csv_files': {},
            'synthesis_file': None,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        if not os.path.exists(data_folder):
            logger.warning(f"⚠️ Dossier {data_folder} non trouvé")
            return store_data
        
        # Lister tous les fichiers
        files = os.listdir(data_folder)
        csv_files = [f for f in files if f.endswith('.csv')]
        txt_files = [f for f in files if f.endswith('.txt')]
        
        logger.info(f"📂 Magasin {store_id}: {len(csv_files)} CSV, {len(txt_files)} TXT")
        
        # Traiter le fichier de synthèse
        synthesis_file = f"FR_{store_id}_synthese_complete.txt"
        if synthesis_file in txt_files:
            synthesis_path = os.path.join(data_folder, synthesis_file)
            content = self.read_txt_file(synthesis_path)
            if content:
                store_data['synthesis_file'] = {
                    'filename': synthesis_file,
                    'content': content,
                    'size_chars': len(content)
                }
                logger.info(f"✅ Synthèse {store_id}: {len(content)} caractères")
        
        # Traiter les fichiers CSV
        for csv_file in csv_files:
            csv_path = os.path.join(data_folder, csv_file)
            csv_data = self.read_csv_file(csv_path)
            
            if csv_data is not None:
                # Extraire le nom logique du fichier (sans préfixe FR_XX_)
                logical_name = csv_file.replace(f"FR_{store_id}_", "").replace(".csv", "")
                
                store_data['csv_files'][logical_name] = {
                    'filename': csv_file,
                    'data': csv_data,
                    'row_count': len(csv_data),
                    'columns': list(csv_data[0].keys()) if csv_data else []
                }
                self.stats['total_csv_files'] += 1
                
                logger.debug(f"✅ CSV {logical_name}: {len(csv_data)} lignes")
        
        return store_data
    
    def process_store_captation_folder(self, store_id: str) -> Dict[str, Any]:
        """Traite le dossier data/[store_id] et retourne les données de captation."""
        
        captation_folder = f"data/{store_id}"
        captation_data = {
            'store_id': store_id,
            'captation_results': {},
            'md_files': {}
        }
        
        if not os.path.exists(captation_folder):
            logger.warning(f"⚠️ Dossier captation {captation_folder} non trouvé")
            return captation_data
        
        # Lister tous les fichiers MD
        files = os.listdir(captation_folder)
        md_files = [f for f in files if f.endswith('.md')]
        
        logger.info(f"📂 Captation {store_id}: {len(md_files)} fichiers MD")
        
        # Traiter chaque fichier MD
        for md_file in md_files:
            md_path = os.path.join(captation_folder, md_file)
            content = self.read_md_file(md_path)
            
            if content:
                logical_name = md_file.replace(".md", "")
                captation_data['md_files'][logical_name] = {
                    'filename': md_file,
                    'content': content,
                    'size_chars': len(content)
                }
                self.stats['total_md_files'] += 1
                
                logger.debug(f"✅ MD {logical_name}: {len(content)} caractères")
        
        return captation_data
    
    def upload_store_to_firestore(self, store_id: str, store_data: Dict[str, Any], 
                                  captation_data: Dict[str, Any]) -> bool:
        """Upload les données d'un magasin vers Firestore."""
        
        try:
            # Obtenir le nom du magasin depuis le cache
            store_name = self.store_names.get(store_id, f"Store_{store_id}")
            
            # Fusionner les données internes et de captation
            complete_store_data = {
                'store_id': store_id,
                'store_name': store_name,  # Ajout du nom du magasin
                'upload_timestamp': datetime.now().isoformat(),
                'data_sources': {
                    'internal_data': store_data,
                    'captation_data': captation_data
                },
                'metadata': {
                    'csv_files_count': len(store_data.get('csv_files', {})),
                    'md_files_count': len(captation_data.get('md_files', {})),
                    'has_synthesis': store_data.get('synthesis_file') is not None,
                    'processing_version': '1.0_complete_data'
                }
            }
            
            # Sauvegarder dans Firestore
            doc_ref = self.db.collection(self.collection_name).document(f"store_{store_id}")
            doc_ref.set(complete_store_data)
            
            logger.info(f"✅ Magasin {store_id} uploadé vers Firestore")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur upload magasin {store_id}: {e}")
            self.stats['errors'].append(f"Store {store_id}: {str(e)}")
            return False
    
    def process_all_stores(self) -> bool:
        """Traite tous les magasins disponibles."""
        
        data_folders = []
        if os.path.exists("data"):
            data_folders = [d for d in os.listdir("data") if os.path.isdir(f"data/{d}")]
        
        if not data_folders:
            logger.error("❌ Aucun dossier magasin trouvé dans data/")
            return False
        
        logger.info(f"📊 {len(data_folders)} magasins trouvés à traiter")
        
        for i, store_id in enumerate(sorted(data_folders), 1):
            logger.info(f"🏪 [{i}/{len(data_folders)}] Traitement magasin {store_id}...")
            
            self.stats['stores_processed'] += 1
            
            # Traiter les données internes
            store_data = self.process_store_data_folder(store_id)
            
            # Traiter les données de captation
            captation_data = self.process_store_captation_folder(store_id)
            
            # Upload vers Firestore
            success = self.upload_store_to_firestore(store_id, store_data, captation_data)
            
            if success:
                self.stats['stores_success'] += 1
            else:
                self.stats['stores_failed'] += 1
        
        return True
    
    def generate_csv_data(self, limit: Optional[int] = None, test_mode: bool = False, store_id: Optional[str] = None) -> bool:
        """Génère les données CSV depuis AWS Athena."""
        try:
            from polco_csv_generator import PolcoCSVGenerator
            
            logger.info("📊 Lancement génération CSV depuis AWS Athena...")
            
            generator = PolcoCSVGenerator()
            
            logger.info(f"📊 Génération CSV...")
            
            success = generator.run(
                limit=limit,
                test_mode=test_mode,
                store_id=store_id
            )
            
            if success:
                logger.info("✅ Génération CSV terminée avec succès")
            else:
                logger.warning("⚠️ Génération CSV partiellement échouée")
            
            return success
            
        except ImportError:
            logger.error("❌ Module polco_csv_generator non trouvé")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur génération CSV: {e}")
            return False
    
    def run(self, generate_csv: bool = False, limit: Optional[int] = None, test_mode: bool = False, store_id: Optional[str] = None) -> bool:
        """Lance l'upload complet."""
        self.stats['start_time'] = datetime.now()
        
        logger.info("=" * 70)
        logger.info("📤 UPLOADER DE DONNÉES MAGASIN POLCO")
        logger.info("📊 Upload data/ + store_data/ vers Firestore")
        logger.info("=" * 70)
        
        # Vérifications
        if not self.check_credentials():
            return False
        
        if not self.init_firestore():
            return False
        
        # Charger les noms de magasins
        self.load_store_names()
        
        # Génération CSV si demandée
        if generate_csv:
            logger.info("📊 Génération des CSV depuis AWS Athena...")
            if not self.generate_csv_data(limit=limit, test_mode=test_mode, store_id=store_id):
                logger.warning("⚠️ Échec génération CSV, continuation avec les données existantes")
        
        # Upload
        success = self.process_all_stores()
        
        # Résumé final
        logger.info("\\n" + "=" * 70)
        logger.info("📊 UPLOAD TERMINÉ")
        logger.info("=" * 70)
        
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        logger.info(f"⏱️ Durée: {duration:.1f} secondes")
        logger.info(f"🏪 Magasins traités: {self.stats['stores_processed']}")
        logger.info(f"✅ Magasins réussis: {self.stats['stores_success']}")
        logger.info(f"❌ Magasins échoués: {self.stats['stores_failed']}")
        logger.info(f"📄 Fichiers CSV traités: {self.stats['total_csv_files']}")
        logger.info(f"📝 Fichiers MD traités: {self.stats['total_md_files']}")
        logger.info(f"🗄️ Collection: {self.collection_name}")
        
        if self.stats['errors']:
            logger.warning(f"⚠️ {len(self.stats['errors'])} erreurs (voir logs)")
        
        if self.stats['stores_success'] > 0:
            logger.info("\\n🎉 Upload réussi ! Données disponibles dans Firestore.")
            return True
        else:
            logger.error("\\n❌ Aucun magasin uploadé")
            return False


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='POLCO Data Uploader')
    parser.add_argument('--generate-csv', action='store_true', help='Générer les CSV depuis AWS Athena avant upload')
    parser.add_argument('--test', action='store_true', help='Mode test (1 magasin)')
    parser.add_argument('--limit', type=int, help='Nombre de magasins à traiter')
    parser.add_argument('--store-id', type=str, help='Traiter uniquement le magasin avec cet ID')
    
    args = parser.parse_args()
    
    try:
        uploader = PolcoDataUploader()
        success = uploader.run(
            generate_csv=args.generate_csv,
            limit=args.limit,
            test_mode=args.test,
            store_id=args.store_id
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\\n⏹️ Upload interrompu par l'utilisateur")
        return 1
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
