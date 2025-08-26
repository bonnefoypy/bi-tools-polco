# POLCO v2 - Version Production Simplifiée

## 🎯 Vue d'ensemble

Version production simplifiée de POLCO, focalisée sur un workflow streamliné et des noms de fichiers "prod".

## ✨ Simplifications v2

### 🔧 **Architecture simplifiée**
- ✅ **Mode nominal** - Plus de versions multiples
- ✅ **Noms "prod"** - Scripts avec noms simplifiés  
- ✅ **Menu streamliné** - 6 options claires
- ✅ **Workflow optimisé** - Mode full automatique

### 📁 **Structure des fichiers**

```
v2/
├── polco_menu.sh              # Menu principal simplifié
├── polco_full_process.sh      # Mode full automatique
├── polco_captation_runner.sh  # Captation précise
├── polco_analyzer_runner.sh   # Analyses sectorielles
├── polco_markdown_runner.sh   # Extraction Markdown
├── polco_pdf_runner.sh        # Génération PDF
├── polco_captation.py         # Processeur captation
├── polco_analyzer.py          # Orchestrateur analyses (ex: analyzer_3_0)
├── polco_markdown_extractor.py # Extracteur Markdown (ex: 3_0_markdown)
├── polco_pdf_generator.py     # Générateur PDF (ex: simple_pdf)
├── polco_data_upload.py       # Upload données (ex: data_uploader)
├── polco_*_processor.py       # Processeurs v3 → noms simplifiés
└── prompts/prompt_captation.md # Prompts de captation
```

## 🚀 Utilisation

### **Menu principal**
```bash
./polco_menu.sh
```

### **Options disponibles**

#### **0. 🚀 MODE FULL - Processus complet**
- Exécute toutes les étapes automatiquement
- Support: Tous magasins / Un magasin / Plusieurs magasins
- Temps: 15-20 min/magasin

#### **1. 📤 UPLOAD DONNÉES**  
- Upload data/ → Firestore
- Prérequis pour toutes les analyses

#### **2. 🔍 CAPTATION**
- Google Search précis
- 6 prompts de captation
- GPS + sources officielles
- Temps: ~8-10 min/magasin

#### **3. 📊 ANALYZER**
- 5 processeurs spécialisés
- Rapports 64k+ caractères
- Graphiques automatiques
- Temps: ~6-8 min/magasin

#### **4. 📄 EXTRACTION**
- Rapports Markdown enrichis
- Graphiques intégrés
- Temps: quelques secondes

#### **5. 📕 PDF**
- Conversion professionnelle
- CSS Decathlon
- Haute définition
- Temps: quelques secondes

#### **6. 🗺️ CARTOGRAPHIE** *(NOUVEAU)*
- Cartes concurrence avec zones d'influence
- Infrastructures sportives géolocalisées
- Zones isochrones (temps de trajet)
- Visualisation zone de chalandise
- Temps: ~2-3 min/magasin

## 🎯 Modes d'exécution

### **Pour chaque étape (2-5):**

1. **📊 COMPLET** - Tous les magasins
2. **🎯 SPÉCIFIQUE** - Un seul magasin  
3. **🎯 MULTIPLE** - Plusieurs magasins (séparés par `;`)

### **Exemples d'usage**

#### **Analyser un magasin spécifique**
```bash
./polco_menu.sh
# → 0 (Mode full) → 2 (Spécifique) → 42
```

#### **Analyser plusieurs magasins**
```bash
./polco_menu.sh  
# → 0 (Mode full) → 3 (Multiple) → 42;115;1125
```

#### **Étape par étape**
```bash
./polco_menu.sh → 1  # Upload
./polco_menu.sh → 2  # Captation → 2 → 42
./polco_menu.sh → 3  # Analyzer → 2 → 42  
./polco_menu.sh → 4  # Extraction → 2 → 42
./polco_menu.sh → 5  # PDF → 2 → 42
```

## 📊 Collections Firestore

| Collection | Usage |
|------------|-------|
| `polco_magasins_data` | Données internes uploadées |
| `polco_magasins_captation` | Captation précise |
| `polco_analyzer_3_0` | Analyses sectorielles |

## 📁 Dossiers de sortie

| Dossier | Contenu |
|---------|---------|
| `reports_polco_3_0/` | Rapports Markdown + graphiques |
| `pdfs_polco_3_0/` | PDFs professionnels |
| `analytics_charts/` | Graphiques générés |
| `geo_maps/` | Cartes interactives HTML *(NOUVEAU)* |

## 🔧 Prérequis

- `credentials.json` (lien symbolique vers v1)
- `polco_mag_test - Feuille 1.csv` 
- `polcoFR.txt`
- Python packages (requirements.txt)
- `pandoc` (pour PDFs)

## 🚀 Workflow recommandé

### **Nouveau magasin complet**
```bash
./polco_menu.sh → 0 → 2 → [store_id]
```

### **Batch processing**  
```bash
./polco_menu.sh → 0 → 3 → [id1;id2;id3]
```

### **Mise à jour existante**
```bash
./polco_menu.sh → 3 → 2 → [store_id]  # Re-analyser
./polco_menu.sh → 4 → 2 → [store_id]  # Re-extraire
./polco_menu.sh → 5 → 2 → [store_id]  # Re-générer PDF
```

## 🗺️ **NOUVEAU : Cartographie Géographique**

Le **6ème processeur POLCO** génère des **cartes interactives HTML** pour enrichir l'analyse :

### **Types de Cartes Générées**

1. **🏪 Carte Concurrence**
   - Positionnement géographique de tous les concurrents
   - Zones d'influence par type (Généralistes, Spécialistes, Mode)
   - Distances précises depuis le magasin
   - Zones primaire (0-15km) et secondaire (15-30km)

2. **🏃 Carte Infrastructures Sportives**
   - Géolocalisation des équipements majeurs
   - Stades, salles de sport, piscines
   - Capacités et caractéristiques
   - Projets futurs (Pôle Gymnastique Belletanche)

3. **⏰ Carte Zones Isochrones**
   - Zones de temps de trajet (0-10min, 10-20min, 20-30min)
   - Visualisation de l'accessibilité
   - Zone de chalandise optimisée

### **Utilisation**
```bash
./polco_menu.sh → 6 → 2 → [store_id]
```

Les cartes sont sauvegardées dans `geo_maps/` au format HTML interactif.

## ⚡ Avantages v2

- ✅ **Plus simple** - 1 seul type de données nominal
- ✅ **Plus rapide** - Workflow optimisé  
- ✅ **Plus clair** - Noms "prod" explicites
- ✅ **Plus flexible** - Support multi-magasins avec `;`
- ✅ **Plus robuste** - Mode full automatique
- ✅ **Plus pratique** - Menu unique pour tout
- ✅ **Plus visuel** - Cartes géographiques interactives *(NOUVEAU)*

## 🔄 Migration depuis v1

La v2 utilise les **mêmes collections Firestore** que v1, donc :
- ✅ Données existantes compatibles
- ✅ Pas de re-upload nécessaire
- ✅ Transition en douceur
