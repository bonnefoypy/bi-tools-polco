# 📊 Documentation - Générateur CSV POLCO

## 🎯 **Vue d'ensemble**

Le générateur CSV POLCO permet de générer des données magasin depuis AWS Athena et de les sauvegarder en CSV dans le dossier `data/`. Il est intégré dans le menu principal POLCO et peut être utilisé de manière autonome.

## 🚀 **Utilisation via le menu POLCO**

### **Menu 1 - Upload Données avec Génération CSV**

```bash
./polco_menu.sh
# Choisir option 1
# Choisir 'y' pour générer CSV + Upload
# Choisir 'n' pour upload uniquement
```

### **Options disponibles :**

- **Génération CSV + Upload** (recommandé) : Génère les CSV depuis AWS Athena puis les upload vers Firestore
- **Upload uniquement** : Utilise les CSV existants dans `data/`

## 🔧 **Utilisation directe**

### **Génération CSV autonome**

```bash
# Génération complète (tous les magasins)
python polco_csv_generator.py

# Mode test (1 magasin)
python polco_csv_generator.py --test

# Limite de magasins
python polco_csv_generator.py --limit 5

# Magasin spécifique
python polco_csv_generator.py --store-id 1912

# Combinaison d'options
python polco_csv_generator.py --store-id 1912 --query-ids ca_par_sport surface_de_vente
```

### **Upload avec génération CSV**

```bash
# Génération CSV + Upload complet
python polco_data_upload.py --generate-csv

# Génération CSV + Upload pour un magasin
python polco_data_upload.py --generate-csv --store-id 1912

# Génération CSV + Upload en mode test
python polco_data_upload.py --generate-csv --test

# Génération CSV + Upload avec limite
python polco_data_upload.py --generate-csv --limit 3
```

## 📋 **Options disponibles**

### **polco_csv_generator.py**

| Option | Description | Exemple |
|--------|-------------|---------|
| `--test` | Mode test (1 magasin) | `--test` |
| `--limit N` | Limite le nombre de magasins | `--limit 5` |
| `--store-id ID` | Magasin spécifique | `--store-id 1912` |
| `--query-ids` | Requêtes spécifiques | `--query-ids ca_par_sport` |

### **polco_data_upload.py**

| Option | Description | Exemple |
|--------|-------------|---------|
| `--generate-csv` | Génère CSV avant upload | `--generate-csv` |
| `--test` | Mode test (1 magasin) | `--test` |
| `--limit N` | Limite le nombre de magasins | `--limit 5` |
| `--store-id ID` | Magasin spécifique | `--store-id 1912` |

## 📊 **Requêtes disponibles**

Le générateur exécute **14 requêtes** par magasin :

1. **nombre_de_comptes_total_pour_le_magasin** - Comptes magasin J-3
2. **frequence_de_visite_annuelle** - Visites sur 12 mois
3. **nombre_de_transactions_digitales** - Click&Collect, etc.
4. **chiffre_d_affaires_omni_sur_les_12_derniers_mois** - CA omnicanal
5. **chiffre_d_affaires_omni_sur_les_12_derniers_mois_par_mois** - CA mensuel
6. **chiffre_d_affaires_instore_sur_les_12_derniers_mois** - CA Instore
7. **chiffre_d_affaires_instore_sur_les_12_derniers_mois_par_mois** - CA Instore mensuel
8. **classement_national_du_magasin_par_gmv** - Rang national
9. **ca_par_sport** - Performance par sport
10. **repartition_du_ca_par_type_de_marque** - MDD vs autres
11. **surface_de_vente** - m² du magasin
12. **ca_instore_par_m2** - Rentabilité
13. **repartition_des_genres_pour_les_comptes_du_magasin** - Clients par genre
14. **repartition_des_ages_pour_les_comptes_du_magasin** - Clients par âge

## 📁 **Structure des fichiers générés**

```
data/
├── 42/
│   ├── FR_42_nombre_de_comptes_total_pour_le_magasin.csv
│   ├── FR_42_frequence_de_visite_annuelle.csv
│   ├── FR_42_chiffre_d_affaires_omni_sur_les_12_derniers_mois_par_mois.csv
│   ├── FR_42_chiffre_d_affaires_omni_sur_les_12_derniers_mois_par_mois.png
│   └── ...
├── 1912/
│   ├── FR_1912_nombre_de_comptes_total_pour_le_magasin.csv
│   ├── FR_1912_frequence_de_visite_annuelle.csv
│   └── ...
└── ...
```

## ⚡ **Performance**

### **Temps estimés :**

- **1 magasin** : ~28 minutes (14 requêtes × 2 min)
- **5 magasins** : ~2h20 (5 × 28 min)
- **Tous les magasins** : ~15h (34 magasins)

### **Optimisations :**

- **Exécution concurrente** : 5 requêtes en parallèle
- **Retry automatique** : 3 tentatives par requête
- **Gestion d'erreurs** : Continue en cas d'échec partiel
- **Graphiques automatiques** : Génération pour les données mensuelles

## 🔐 **Prérequis AWS**

### **Installation des outils :**

```bash
# Installation
pip install aws-sso-util
pip install awsume

# Connexion (première utilisation)
aws-sso-util login https://decathlon.awsapps.com/start/ eu-west-1
awsume ddarchitec-infra-pr
```

### **Vérification :**

```bash
# Test des prérequis
python test_csv_generation.py
```

## 🛠️ **Configuration**

### **Fichier de configuration :**

`polco_queries_config.json` - Contient toutes les requêtes SQL et leurs paramètres

### **Variables d'environnement :**

- `PROFILE_NAME` : Profil AWS (`ddarchitec-infra-pr`)
- `DATABASE` : Base de données Athena (`askr`)
- `WORKGROUP` : Groupe de travail (`cebitools-askr`)

## 📈 **Exemples d'utilisation**

### **Scénario 1 : Test rapide**

```bash
# Générer CSV pour 1 magasin en mode test
python polco_csv_generator.py --test

# Résultat : data/42/ avec 14 CSV + graphiques
```

### **Scénario 2 : Magasin spécifique**

```bash
# Générer CSV pour le magasin 1912
python polco_csv_generator.py --store-id 1912

# Résultat : data/1912/ avec 14 CSV + graphiques
```

### **Scénario 3 : Série de magasins**

```bash
# Générer CSV pour 5 magasins
python polco_csv_generator.py --limit 5

# Résultat : data/42/, data/6/, data/554/, data/66/, data/26/
```

### **Scénario 4 : Requêtes spécifiques**

```bash
# Générer seulement CA et surface pour magasin 1912
python polco_csv_generator.py --store-id 1912 --query-ids ca_par_sport surface_de_vente

# Résultat : data/1912/ avec 2 CSV seulement
```

### **Scénario 5 : Intégration complète**

```bash
# Génération CSV + Upload pour magasin 1912
python polco_data_upload.py --generate-csv --store-id 1912

# Résultat : CSV générés + upload vers Firestore
```

## 🔍 **Dépannage**

### **Erreurs courantes :**

1. **"awsume non trouvé"**
   ```bash
   pip install awsume
   ```

2. **"Profil AWS non trouvé"**
   ```bash
   aws-sso-util login https://decathlon.awsapps.com/start/ eu-west-1
   awsume ddarchitec-infra-pr
   ```

3. **"Magasin ID non trouvé"**
   - Vérifier l'ID dans `polco_mag_test - Feuille 1.csv`
   - Utiliser `python polco_csv_generator.py --store-id 9999` pour voir les magasins disponibles

4. **"Timeout requête"**
   - Augmenter `timeout_minutes` dans le code
   - Vérifier la connexion AWS

### **Logs :**

- **polco_csv_generator.log** : Logs du générateur CSV
- **polco_data_upload.log** : Logs de l'upload

## 🎯 **Bonnes pratiques**

1. **Commencez par un test** : Utilisez `--test` pour vérifier la configuration
2. **Magasin par magasin** : Utilisez `--store-id` pour les tests spécifiques
3. **Surveillez les logs** : Vérifiez les fichiers de log en cas de problème
4. **Sauvegardez les données** : Les CSV sont sauvegardés dans `data/`
5. **Vérifiez Firestore** : Les données sont uploadées vers la collection `polco_magasins_data`

## 📞 **Support**

En cas de problème :

1. Vérifiez les prérequis : `python test_csv_generation.py`
2. Consultez les logs : `polco_csv_generator.log`
3. Testez avec un magasin : `--store-id 1912 --test`
4. Vérifiez la connexion AWS : `aws sts get-caller-identity`
