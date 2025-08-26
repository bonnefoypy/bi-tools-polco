#!/bin/bash

echo "🚀 POLCO FULL PROCESS - Processus Complet Automatique"
echo "====================================================="
echo ""
echo "🎯 Exécution de toutes les étapes dans l'ordre optimal"
echo "   1. 📤 Upload des données magasin"
echo "   2. 🔍 Captation précise"
echo "   3. 📊 Analyses sectorielles 64k+ chars"
echo "   4. 📄 Extraction rapports Markdown"
echo "   5. 📕 Génération PDFs professionnels"
echo ""

# Vérifier les prérequis
if [ ! -f "credentials.json" ]; then
    echo "❌ Fichier credentials.json non trouvé"
    exit 1
fi

if [ ! -f "polco_mag_test - Feuille 1.csv" ]; then
    echo "❌ Fichier CSV des magasins non trouvé"
    exit 1
fi

echo "✅ Prérequis vérifiés"
echo ""

# Mode d'exécution
echo "🤔 Choisissez le scope d'exécution:"
echo "   1. 📊 PROCESSUS COMPLET - Tous les magasins"
echo "   2. 🎯 PROCESSUS SPÉCIFIQUE - Un seul magasin"
echo "   3. 🎯 PROCESSUS MULTIPLE - Plusieurs magasins (séparés par ;)"
echo ""
read -p "👉 Votre choix (1/2/3): " mode_choice

STORE_ARGS=""
ESTIMATED_HOURS=3

case $mode_choice in
    1)
        echo ""
        echo "📊 Mode PROCESSUS COMPLET sélectionné"
        echo "⏱️ Temps estimé: ~3-4 heures"
        echo ""
        echo "⚠️ ATTENTION: Processus très long avec toutes les étapes"
        read -p "🚀 Démarrer le processus complet ? (y/N): " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            echo "❌ Processus annulé"
            exit 0
        fi
        ;;
    2)
        echo ""
        echo "🎯 Mode PROCESSUS SPÉCIFIQUE sélectionné"
        echo ""
        echo "📋 Magasins disponibles:"
        python -c "
import pandas as pd
df = pd.read_csv('polco_mag_test - Feuille 1.csv')
for _, row in df.iterrows():
    print(f'   • {row[\"store_id\"]} - {row[\"store_name\"]}')
"
        echo ""
        read -p "🎯 Entrez l'ID du magasin: " store_id
        
        if [[ -z "$store_id" ]]; then
            echo "❌ Aucun ID saisi. Sortie."
            exit 1
        fi
        
        STORE_ARGS="--store-id $store_id"
        ESTIMATED_HOURS="15-20 minutes"
        
        echo ""
        echo "🎯 Magasin sélectionné: $store_id"
        echo "⏱️ Temps estimé: $ESTIMATED_HOURS"
        echo ""
        read -p "🚀 Démarrer le processus ? (y/N): " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            echo "❌ Processus annulé"
            exit 0
        fi
        ;;
    3)
        echo ""
        echo "🎯 Mode PROCESSUS MULTIPLE sélectionné"
        echo ""
        echo "📋 Magasins disponibles:"
        python -c "
import pandas as pd
df = pd.read_csv('polco_mag_test - Feuille 1.csv')
for _, row in df.iterrows():
    print(f'   • {row[\"store_id\"]} - {row[\"store_name\"]}')
"
        echo ""
        echo "💡 Entrez les IDs séparés par ';' (ex: 42;115;1125)"
        read -p "🎯 IDs des magasins: " store_ids
        
        if [[ -z "$store_ids" ]]; then
            echo "❌ Aucun ID saisi. Sortie."
            exit 1
        fi
        
        # Compter les magasins
        IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
        store_count=${#STORE_ARRAY[@]}
        estimated_minutes=$((store_count * 18))
        
        echo ""
        echo "🎯 Magasins sélectionnés: $store_count magasins"
        echo "⏱️ Temps estimé: ~$estimated_minutes minutes"
        echo ""
        read -p "🚀 Démarrer le processus ? (y/N): " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            echo "❌ Processus annulé"
            exit 0
        fi
        ;;
    *)
        echo "❌ Choix invalide. Sortie."
        exit 1
        ;;
esac

echo ""
echo "🚀 DÉMARRAGE DU PROCESSUS COMPLET..."
echo "====================================="

# Étape 1: Upload des données
echo ""
echo "📤 ÉTAPE 1/5: Upload des données magasin"
echo "----------------------------------------"
python polco_data_upload.py
if [ $? -ne 0 ]; then
    echo "❌ Échec étape 1 (Upload données)"
    exit 1
fi
echo "✅ Étape 1 terminée"

# Étape 2: Captation
echo ""
echo "🔍 ÉTAPE 2/5: Captation précise"
echo "------------------------------------"
if [[ $mode_choice -eq 1 ]]; then
    python polco_captation.py
elif [[ $mode_choice -eq 2 ]]; then
    python polco_captation.py $STORE_ARGS
else
    # Mode multiple
    IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
    for store_id in "${STORE_ARRAY[@]}"; do
        store_id=$(echo "$store_id" | xargs)
        echo "🔄 Captation magasin: $store_id"
        python polco_captation.py --store-id "$store_id"
    done
fi
if [ $? -ne 0 ]; then
    echo "❌ Échec étape 2 (Captation)"
    exit 1
fi
echo "✅ Étape 2 terminée"

# Étape 3: Analyzer
echo ""
echo "📊 ÉTAPE 3/5: Analyses sectorielles"
echo "----------------------------------"
if [[ $mode_choice -eq 1 ]]; then
    python polco_analyzer.py
elif [[ $mode_choice -eq 2 ]]; then
    python polco_analyzer.py $STORE_ARGS
else
    # Mode multiple
    IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
    for store_id in "${STORE_ARRAY[@]}"; do
        store_id=$(echo "$store_id" | xargs)
        echo "🔄 Analyse magasin: $store_id"
        python polco_analyzer.py --store-id "$store_id"
    done
fi
if [ $? -ne 0 ]; then
    echo "❌ Échec étape 3 (Analyzer)"
    exit 1
fi
echo "✅ Étape 3 terminée"

# Étape 4: Extraction Markdown
echo ""
echo "📄 ÉTAPE 4/5: Extraction rapports Markdown"
echo "------------------------------------------"
if [[ $mode_choice -eq 1 ]]; then
    python polco_markdown_extractor.py
elif [[ $mode_choice -eq 2 ]]; then
    python polco_markdown_extractor.py $STORE_ARGS
else
    # Mode multiple
    IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
    for store_id in "${STORE_ARRAY[@]}"; do
        store_id=$(echo "$store_id" | xargs)
        echo "🔄 Extraction magasin: $store_id"
        python polco_markdown_extractor.py --store-id "$store_id"
    done
fi
if [ $? -ne 0 ]; then
    echo "❌ Échec étape 4 (Extraction Markdown)"
    exit 1
fi
echo "✅ Étape 4 terminée"

# Étape 5: Génération PDF
echo ""
echo "📕 ÉTAPE 5/5: Génération PDFs professionnels"
echo "--------------------------------------------"
if [[ $mode_choice -eq 1 ]]; then
    python polco_pdf_generator.py
elif [[ $mode_choice -eq 2 ]]; then
    python polco_pdf_generator.py $STORE_ARGS
else
    # Mode multiple
    IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
    for store_id in "${STORE_ARRAY[@]}"; do
        store_id=$(echo "$store_id" | xargs)
        echo "🔄 PDF magasin: $store_id"
        python polco_pdf_generator.py --store-id "$store_id"
    done
fi
if [ $? -ne 0 ]; then
    echo "❌ Échec étape 5 (Génération PDF)"
    exit 1
fi
echo "✅ Étape 5 terminée"

echo ""
echo "🎉 PROCESSUS COMPLET TERMINÉ AVEC SUCCÈS !"
echo "=========================================="
echo ""
echo "📊 Résultats disponibles:"
echo "   🌐 Firestore: https://console.cloud.google.com/firestore/data?project=polcoaigeneration-ved6"
echo "   📄 Rapports Markdown: reports_polco_3_0/"
echo "   📕 PDFs professionnels: pdfs_polco_3_0/"
echo ""
echo "🎯 Toutes les analyses sont prêtes pour consultation !"
