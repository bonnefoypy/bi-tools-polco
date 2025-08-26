#!/usr/bin/env python3
"""
POLCO - Générateur de CSV via AWS Athena
Génère les données magasin depuis AWS Athena et les sauvegarde en CSV
Basé sur le code fourni, adapté pour l'architecture POLCO
"""

import os
import sys
import time
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import List, Dict, Optional, Any
import logging
from pathlib import Path
import subprocess

# Configuration matplotlib pour macOS et multithreading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polco_csv_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Configuration ===
ENV = 'prod'
PROFILE_NAME = 'decathlon-prod'  # Profil pour le compte Decathlon
QUERIES_CONFIG_FILE = 'polco_queries_config.json'
DATA_ROOT_DIR = 'data'

CONFIG = {
    'prod': {'output_location': 's3://prd-dct-wksp-askr/'},
    'pp': {'output_location': 's3://ppd-dct-wksp-askr/'},
    'ppd': {'output_location': 's3://ppd-dct-wksp-askr/'}
}

DATABASE = 'askr'
WORKGROUP = 'cebitools-askr'
REGION = 'eu-west-1'

QUERY_CONFIG = {
    'sleep_time': 10,
    'max_concurrent_queries': 5,
    'retry_attempts': 3,
    'timeout_minutes': 30
}

class PolcoCSVGenerator:
    """Générateur de CSV POLCO via AWS Athena."""
    
    def __init__(self):
        """Initialise le générateur CSV."""
        self.athena_client = None
        self.session = None
        self.stats = {
            'total_stores': 0,
            'processed_stores': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'start_time': None,
            'errors': []
        }
        
        logger.info("🚀 Initialisation du générateur CSV POLCO")
    
    def check_aws_credentials(self) -> bool:
        """Vérifie et configure les credentials AWS."""
        try:
            # Vérifier si awsume est disponible
            result = subprocess.run(['which', 'awsume'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("❌ awsume non trouvé. Veuillez l'installer.")
                return False
            
            # Vérifier si on est connecté
            result = subprocess.run(['aws', 'sts', 'get-caller-identity'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("⚠️ Pas connecté à AWS. Tentative de connexion...")
                self._connect_aws()
            
            logger.info("✅ Credentials AWS vérifiés")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur vérification AWS: {e}")
            return False
    
    def _connect_aws(self) -> bool:
        """Tente de se connecter à AWS via SSO."""
        try:
            logger.info("🔐 Connexion AWS SSO...")
            
            # Login SSO
            result = subprocess.run([
                'aws-sso-util', 'login', 
                'https://decathlon.awsapps.com/start/', 
                'eu-west-1'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Échec login SSO: {result.stderr}")
                return False
            
            # Connexion via SSO Decathlon
            logger.info("🔐 Connexion AWS SSO Decathlon...")
            
            # Login SSO
            result = subprocess.run([
                'aws-sso-util', 'login', 
                'https://decathlon.awsapps.com/start/', 
                'eu-west-1'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Échec login SSO: {result.stderr}")
                return False
            
            # Assume le rôle Decathlon
            result = subprocess.run([
                'awsume', 'decathlon-prod'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Échec assume rôle: {result.stderr}")
                return False
            
            logger.info("✅ Connexion AWS Decathlon réussie")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion AWS: {e}")
            return False
    
    def init_athena(self) -> bool:
        """Initialise la connexion Athena."""
        try:
            import boto3
            
            self.session = boto3.Session(profile_name=PROFILE_NAME, region_name=REGION)
            self.athena_client = self.session.client('athena')
            
            logger.info(f"✅ Athena initialisé avec le profil: {PROFILE_NAME}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Athena: {e}")
            return False
    
    def load_queries_config(self) -> Dict[str, Any]:
        """Charge la configuration des requêtes."""
        try:
            if not os.path.exists(QUERIES_CONFIG_FILE):
                logger.error(f"❌ Fichier {QUERIES_CONFIG_FILE} non trouvé")
                return {"queries": [], "store_groups": {}}
            
            with open(QUERIES_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"✅ Configuration chargée depuis {QUERIES_CONFIG_FILE}")
                return config
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement configuration: {e}")
            return {"queries": [], "store_groups": {}}
    
    def get_store_ids(self, store_group: str = "@priority_stores") -> List[str]:
        """Récupère la liste des magasins depuis le CSV principal."""
        try:
            csv_path = "polco_mag_test - Feuille 1.csv"
            
            if not os.path.exists(csv_path):
                logger.error(f"❌ Fichier {csv_path} non trouvé")
                return []
            
            df = pd.read_csv(csv_path)
            store_ids = df['store_id'].astype(str).tolist()
            
            logger.info(f"✅ {len(store_ids)} magasins chargés depuis {csv_path}")
            return store_ids
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture magasins: {e}")
            return []
    
    def run_athena_query(self, query: str) -> str:
        """Lance une requête Athena."""
        response = self.athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': DATABASE},
            ResultConfiguration={'OutputLocation': CONFIG[ENV]['output_location']},
            WorkGroup=WORKGROUP
        )
        return response['QueryExecutionId']
    
    def wait_for_query(self, query_execution_id: str) -> str:
        """Attend la fin d'une requête Athena."""
        start_time = time.time()
        timeout_seconds = QUERY_CONFIG['timeout_minutes'] * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                state = response['QueryExecution']['Status']['State']
                
                if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    return state
                    
                time.sleep(QUERY_CONFIG['sleep_time'])
                
            except Exception as e:
                logger.error(f"❌ Erreur attente requête {query_execution_id}: {e}")
                return 'FAILED'
        
        logger.warning(f"⚠️ Timeout pour la requête {query_execution_id}")
        return 'TIMEOUT'
    
    def get_query_results(self, query_execution_id: str) -> Optional[pd.DataFrame]:
        """Récupère les résultats d'une requête Athena."""
        try:
            paginator = self.athena_client.get_paginator('get_query_results')
            results_iter = paginator.paginate(QueryExecutionId=query_execution_id)
            
            rows, columns = [], []
            
            for i, results_page in enumerate(results_iter):
                result_set = results_page['ResultSet']
                
                if i == 0:
                    columns = [col['Label'] for col in result_set['ResultSetMetadata']['ColumnInfo']]
                    data_rows = result_set['Rows'][1:] if len(result_set['Rows']) > 1 else []
                else:
                    data_rows = result_set['Rows']
                
                for row in data_rows:
                    rows.append([col.get('VarCharValue') for col in row['Data']])
            
            if not rows:
                return pd.DataFrame(columns=columns)
            
            return pd.DataFrame(rows, columns=columns)
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération résultats {query_execution_id}: {e}")
            return None
    
    def create_and_save_plot(self, df: pd.DataFrame, file_path: Path):
        """Crée et sauvegarde un graphique linéaire."""
        try:
            known_id_cols = ['mois', 'store_id', 'currency', 'store_name', 'date']
            metric_col = next((col for col in df.columns if col not in known_id_cols), None)
            
            if not metric_col:
                logger.warning(f"⚠️ Impossible de trouver la colonne de métrique pour {file_path.name}")
                return
            
            df_plot = df.copy()
            df_plot['mois'] = pd.to_datetime(df_plot['mois'])
            df_plot = df_plot.sort_values('mois')
            df_plot[metric_col] = pd.to_numeric(df_plot[metric_col], errors='coerce')
            df_plot.dropna(subset=[metric_col], inplace=True)
            
            if df_plot.empty:
                logger.warning(f"⚠️ Aucune donnée numérique valide pour {file_path.name}")
                return
            
            store_id = df_plot['store_id'].iloc[0]
            plt.figure(figsize=(16, 8))
            sns.set_theme(style="whitegrid")
            
            plot_title = f"{metric_col.replace('_', ' ').title()} par mois pour le magasin {store_id}"
            ax = sns.lineplot(data=df_plot, x='mois', y=metric_col, marker='o', color='royalblue', linewidth=2)
            
            plt.title(plot_title, fontsize=18, weight='bold')
            plt.ylabel(metric_col.replace('_', ' ').title(), fontsize=14)
            plt.xlabel("Mois", fontsize=14)
            
            ax.get_yaxis().set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda x, p: f'{x:,.0f}'.replace(',', ' '))
            )
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            plot_path = file_path.with_suffix('.png')
            plt.savefig(plot_path, dpi=100)
            plt.close()
            
            logger.info(f"📊 Graphique sauvegardé : {plot_path}")
            
        except Exception as e:
            logger.error(f"❌ Erreur création graphique {file_path.name}: {e}")
    
    def process_single_query(self, store_id: str, query_config: Dict[str, Any], progress_counter) -> Optional[pd.DataFrame]:
        """Traite une requête pour un magasin."""
        query_id_str = query_config.get('id', 'unknown')
        
        for attempt in range(QUERY_CONFIG['retry_attempts']):
            try:
                logger.info(f"🔍 Traitement store {store_id} - requête '{query_id_str}' (tentative {attempt + 1})")
                
                sql_template = query_config['sql_template']
                parameters = query_config.get('parameters', {})
                default_params = {"date_offset": -3}
                final_params = {**default_params, **parameters}
                
                format_params = {
                    'store_id': store_id,
                    'business_unit_id': f"7-{store_id}-{store_id}",
                    **final_params
                }
                
                query = sql_template.format(**format_params)
                query_execution_id = self.run_athena_query(query)
                state = self.wait_for_query(query_execution_id)
                
                if state == 'SUCCEEDED':
                    df = self.get_query_results(query_execution_id)
                    
                    if df is not None and not df.empty:
                        # Sauvegarder le CSV
                        store_path = Path(DATA_ROOT_DIR) / str(store_id)
                        store_path.mkdir(parents=True, exist_ok=True)
                        
                        base_filename = query_config.get('output_filename', query_id_str)
                        output_filename = f"FR_{store_id}_{base_filename}.csv"
                        file_path = store_path / output_filename
                        
                        df.to_csv(file_path, index=False)
                        logger.info(f"💾 CSV sauvegardé : {file_path}")
                        
                        # Créer un graphique si c'est une requête mensuelle
                        if "_monthly" in query_id_str or "par_mois" in query_id_str:
                            self.create_and_save_plot(df, file_path)
                        
                        progress_counter.increment_completed()
                        return df
                    else:
                        logger.warning(f"⚠️ Aucune donnée pour store {store_id} - requête {query_id_str}")
                else:
                    response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                    error_message = response['QueryExecution']['Status'].get('StateChangeReason', 'Raison inconnue')
                    logger.error(f"❌ Requête échouée store {store_id} (état: {state}). Raison: {error_message}")
                    
            except Exception as e:
                logger.error(f"❌ Erreur traitement store {store_id} (tentative {attempt + 1}): {e}")
            
            if attempt < QUERY_CONFIG['retry_attempts'] - 1:
                time.sleep(5)
        
        progress_counter.increment_failed()
        logger.error(f"❌ Échec définitif store {store_id} après {QUERY_CONFIG['retry_attempts']} tentatives")
        return None
    
    def run_queries_for_store(self, store_id: str, queries_config: List[Dict[str, Any]]) -> bool:
        """Exécute toutes les requêtes pour un magasin."""
        logger.info(f"🏪 Démarrage génération CSV pour magasin {store_id}")
        
        progress_counter = ProgressCounter(len(queries_config))
        all_dfs = []
        
        with ThreadPoolExecutor(max_workers=QUERY_CONFIG['max_concurrent_queries']) as executor:
            future_to_query = {
                executor.submit(self.process_single_query, store_id, query_config, progress_counter): query_config
                for query_config in queries_config
            }
            
            for future in as_completed(future_to_query):
                try:
                    result_df = future.result()
                    if result_df is not None:
                        all_dfs.append(result_df)
                except Exception as e:
                    query_config = future_to_query[future]
                    logger.error(f"❌ Exception non gérée pour store {store_id} - requête {query_config.get('id')}: {e}")
                    progress_counter.increment_failed()
        
        success_rate = progress_counter.completed / len(queries_config) * 100
        logger.info(f"✅ Magasin {store_id}: {progress_counter.completed}/{len(queries_config)} requêtes réussies ({success_rate:.1f}%)")
        
        return success_rate > 50  # Considérer comme réussi si plus de 50% des requêtes passent
    
    def run(self, limit: Optional[int] = None, test_mode: bool = False, store_id: Optional[str] = None, query_ids: Optional[List[str]] = None) -> bool:
        """Lance la génération CSV avec les mêmes options que les autres modules POLCO."""
        logger.info("🚀 Démarrage génération CSV POLCO")
        logger.info("=" * 80)
        
        self.stats['start_time'] = time.time()
        
        # Vérifications
        if not self.check_aws_credentials():
            return False
        
        if not self.init_athena():
            return False
        
        # Charger la configuration
        config = self.load_queries_config()
        queries_to_run = [
            q for q in config.get('queries', [])
            if not query_ids or q.get('id') in query_ids
        ]
        
        if not queries_to_run:
            logger.error("❌ Aucune requête à exécuter")
            return False
        
        # Déterminer les magasins à traiter
        all_store_ids = self.get_store_ids()
        
        if store_id:
            # Mode magasin spécifique
            if store_id in all_store_ids:
                store_ids = [store_id]
                logger.info(f"🎯 Mode magasin spécifique: {store_id}")
            else:
                logger.error(f"❌ Magasin ID '{store_id}' non trouvé")
                logger.info("📋 Magasins disponibles:")
                for sid in all_store_ids[:10]:  # Afficher les 10 premiers
                    logger.info(f"   • {sid}")
                if len(all_store_ids) > 10:
                    logger.info(f"   ... et {len(all_store_ids) - 10} autres")
                return False
        elif test_mode or limit:
            # Mode test ou limite
            n = limit if limit else 1
            store_ids = all_store_ids[:n]
            logger.info(f"🧪 Mode test activé: traitement de {len(store_ids)} magasin(s)")
        else:
            # Mode complet
            store_ids = all_store_ids
            logger.info("🚀 Mode complet: traitement de tous les magasins")
        
        self.stats['total_stores'] = len(store_ids)
        
        logger.info(f"📊 {len(store_ids)} magasins à traiter")
        logger.info(f"📋 {len(queries_to_run)} requêtes par magasin")
        logger.info(f"⏱️ Temps estimé: {len(store_ids) * len(queries_to_run) * 2:.0f} minutes")
        logger.info("")
        
        # Traiter chaque magasin
        for index, store_id in enumerate(store_ids):
            try:
                logger.info(f"🏪 [{index + 1}/{len(store_ids)}] Magasin {store_id}")
                
                success = self.run_queries_for_store(store_id, queries_to_run)
                
                if success:
                    self.stats['processed_stores'] += 1
                else:
                    self.stats['errors'].append(f"Échec magasin {store_id}")
                
            except KeyboardInterrupt:
                logger.info("\n⏹️ Génération interrompue par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur traitement magasin {store_id}: {e}")
                self.stats['errors'].append(str(e))
        
        # Rapport final
        end_time = time.time()
        duration = (end_time - self.stats['start_time']) / 60
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 POLCO CSV GENERATOR - RAPPORT FINAL")
        logger.info("=" * 80)
        logger.info(f"⏱️ Durée totale: {duration:.1f} minutes")
        logger.info(f"🏪 Magasins traités: {self.stats['processed_stores']}/{self.stats['total_stores']}")
        logger.info(f"✅ Requêtes réussies: {self.stats['successful_queries']}")
        logger.info(f"❌ Requêtes échouées: {self.stats['failed_queries']}")
        logger.info(f"📁 Données sauvegardées dans: {DATA_ROOT_DIR}/")
        logger.info("")
        logger.info("🎉 Génération CSV terminée !")
        
        return self.stats['processed_stores'] > 0
    
    def generate_csv_for_stores(self, store_ids: List[str], query_ids: Optional[List[str]] = None) -> bool:
        """Méthode legacy pour compatibilité."""
        return self.run(store_id=store_ids[0] if len(store_ids) == 1 else None, query_ids=query_ids)


class ProgressCounter:
    """Compteur de progression thread-safe."""
    
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.failed = 0
        self.lock = threading.Lock()
    
    def increment_completed(self):
        with self.lock:
            self.completed += 1
            logger.info(f"📈 Progrès: {self.completed}/{self.total} requêtes terminées")
    
    def increment_failed(self):
        with self.lock:
            self.failed += 1
            logger.warning(f"⚠️ Échecs: {self.failed}/{self.total} requêtes échouées")


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='POLCO CSV Generator - AWS Athena')
    parser.add_argument('--test', action='store_true', help='Mode test (1 magasin)')
    parser.add_argument('--limit', type=int, help='Nombre de magasins à traiter')
    parser.add_argument('--store-id', type=str, help='Traiter uniquement le magasin avec cet ID')
    parser.add_argument('--query-ids', nargs='+', help='IDs des requêtes spécifiques à exécuter')
    
    args = parser.parse_args()
    
    generator = PolcoCSVGenerator()
    
    try:
        success = generator.run(
            limit=args.limit,
            test_mode=args.test,
            store_id=args.store_id,
            query_ids=args.query_ids
        )
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Processus interrompu")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
