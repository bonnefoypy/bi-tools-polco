#!/bin/bash

echo "📄 POLCO EXTRACTION - Rapports Markdown Détaillés"
echo "======================================================="
echo ""
echo "🎯 Extraction des analyses sectorielles vers rapports Markdown enrichis"
echo "   📊 Rapports 64k+ caractères avec graphiques intégrés"
echo "   🎯 5 sections spécialisées + visualisations"
echo "   📈 Métriques détaillées et plans d'action"
echo ""

# Vérifier les prérequis
if [ ! -f "credentials.json" ]; then
    echo "❌ Fichier credentials.json non trouvé"
    exit 1
fi

echo "✅ Prérequis vérifiés"
echo ""

# Vérifier les analyses disponibles
ANALYSIS_COUNT=$(python -c "
from google.cloud import firestore
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
try:
    db = firestore.Client(project='polcoaigeneration-ved6')
    count = len(list(db.collection('polco_analyzer_3_0').stream()))
    print(count)
except:
    print(0)
" 2>/dev/null)

if [ "$ANALYSIS_COUNT" -eq 0 ]; then
    echo "❌ Aucune analyse disponible pour extraction"
    echo ""
    echo "💡 Lancez d'abord l'ANALYZER (option 3 du menu principal)"
    exit 1
fi

echo "✅ $ANALYSIS_COUNT analyses disponibles pour extraction"
echo ""

# Mode d'extraction
echo "🤔 Choisissez le mode d'extraction:"
echo "   1. 📊 EXTRACTION COMPLÈTE - Tous les magasins"
echo "   2. 🎯 EXTRACTION SPÉCIFIQUE - Un seul magasin"
echo "   3. 🎯 EXTRACTION MULTIPLE - Plusieurs magasins (séparés par ;)"
echo ""
read -p "👉 Votre choix (1/2/3): " mode_choice

case $mode_choice in
    1)
        echo ""
        echo "📊 Mode EXTRACTION COMPLÈTE sélectionné"
        echo "⏱️ Temps estimé: ~quelques secondes"
        echo ""
        read -p "🚀 Démarrer l'extraction complète ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement EXTRACTION COMPLÈTE..."
            python polco_markdown_extractor.py
        else
            echo "❌ Extraction annulée"
            exit 0
        fi
        ;;
    2)
        echo ""
        echo "🎯 Mode EXTRACTION SPÉCIFIQUE sélectionné"
        echo ""
        echo "📋 Analyses disponibles:"
        python -c "
from google.cloud import firestore
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
try:
    db = firestore.Client(project='polcoaigeneration-ved6')
    docs = list(db.collection('polco_analyzer_3_0').stream())
    for doc in sorted(docs, key=lambda x: x.id):
        data = doc.to_dict()
        store_id = data.get('store_id', doc.id.replace('analyzer_3_0_', ''))
        print(f'   • {store_id}')
except Exception as e:
    print(f'❌ Erreur: {e}')
"
        echo ""
        read -p "🎯 Entrez l'ID du magasin: " store_id
        
        if [[ -z "$store_id" ]]; then
            echo "❌ Aucun ID saisi. Sortie."
            exit 1
        fi
        
        echo ""
        echo "🎯 Magasin sélectionné: $store_id"
        echo "⏱️ Temps estimé: ~quelques secondes"
        echo ""
        read -p "🚀 Démarrer l'extraction ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement EXTRACTION (MAGASIN $store_id)..."
            python polco_markdown_extractor.py --store-id "$store_id"
        else
            echo "❌ Extraction annulée"
            exit 0
        fi
        ;;
    3)
        echo ""
        echo "🎯 Mode EXTRACTION MULTIPLE sélectionné"
        echo ""
        echo "📋 Analyses disponibles:"
        python -c "
from google.cloud import firestore
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
try:
    db = firestore.Client(project='polcoaigeneration-ved6')
    docs = list(db.collection('polco_analyzer_3_0').stream())
    for doc in sorted(docs, key=lambda x: x.id):
        data = doc.to_dict()
        store_id = data.get('store_id', doc.id.replace('analyzer_3_0_', ''))
        print(f'   • {store_id}')
except Exception as e:
    print(f'❌ Erreur: {e}')
"
        echo ""
        echo "💡 Entrez les IDs séparés par ';' (ex: 42;115;1125)"
        read -p "🎯 IDs des magasins: " store_ids
        
        if [[ -z "$store_ids" ]]; then
            echo "❌ Aucun ID saisi. Sortie."
            exit 1
        fi
        
        echo ""
        echo "🎯 Extractions multiples sélectionnées"
        echo "⏱️ Temps estimé: ~quelques secondes"
        echo ""
        read -p "🚀 Démarrer l'extraction ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement EXTRACTION MULTIPLE..."
            IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
            for store_id in "${STORE_ARRAY[@]}"; do
                store_id=$(echo "$store_id" | xargs)  # Trim whitespace
                echo "🔄 Extraction magasin: $store_id"
                python polco_markdown_extractor.py --store-id "$store_id"
            done
        else
            echo "❌ Extraction annulée"
            exit 0
        fi
        ;;
    *)
        echo "❌ Choix invalide. Sortie."
        exit 1
        ;;
esac

echo ""
echo "✅ EXTRACTION terminée !"
echo "📁 Consultez vos rapports dans: reports_polco_3_0/"
