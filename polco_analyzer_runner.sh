#!/bin/bash

echo "📊 POLCO ANALYZER - Analyses Sectorielles Détaillées"
echo "========================================================="
echo ""
echo "🎯 Génération d'analyses 64k+ caractères avec 5 processeurs spécialisés"
echo "   🧠 CONTEXTE - Analyse stratégique et SWOT approfondi"
echo "   👥 CIBLES - Segmentation client et comportements détaillés"
echo "   📈 POTENTIEL - Métriques performance et projections"
echo "   🛍️ OFFRE - Classification sports et plans d'action"
echo "   🎯 ACTIONS - Propositions IA avec plans court/moyen/long terme"
echo "   📊 GRAPHIQUES - Visualisations automatiques"
echo ""

# Vérifier les prérequis
if [ ! -f "credentials.json" ]; then
    echo "❌ Fichier credentials.json non trouvé"
    exit 1
fi

echo "✅ Prérequis vérifiés"
echo ""

# Mode d'exécution
echo "🤔 Choisissez le mode d'exécution:"
echo "   1. 📊 ANALYZER COMPLET - Tous les magasins"
echo "   2. 🎯 ANALYZER SPÉCIFIQUE - Un seul magasin"
echo "   3. 🎯 ANALYZER MULTIPLE - Plusieurs magasins (séparés par ;)"
echo ""
read -p "👉 Votre choix (1/2/3): " mode_choice

case $mode_choice in
    1)
        echo ""
        echo "📊 Mode ANALYZER COMPLET sélectionné"
        echo "⏱️ Temps estimé: ~2-4 heures"
        echo ""
        read -p "🚀 Démarrer l'analyse complète ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement ANALYZER COMPLET..."
            python polco_analyzer.py --ultra
        else
            echo "❌ Analyse annulée"
            exit 0
        fi
        ;;
    2)
        echo ""
        echo "🎯 Mode ANALYZER SPÉCIFIQUE sélectionné"
        echo ""
        echo "📋 Magasins avec captation disponibles:"
        python -c "
from google.cloud import firestore
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
try:
    db = firestore.Client(project='polcoaigeneration-ved6')
    docs = list(db.collection('polco_magasins_captation').stream())
    for doc in sorted(docs, key=lambda x: x.id):
        data = doc.to_dict()
        store_id = data.get('store_id', doc.id.replace('store_', ''))
        store_name = data.get('store_name', 'N/A')
        print(f'   • {store_id} - {store_name}')
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
        echo "⏱️ Temps estimé: ~6-8 minutes"
        echo ""
        read -p "🚀 Démarrer l'analyse ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement ANALYZER (MAGASIN $store_id)..."
            python polco_analyzer.py --store-id "$store_id"
        else
            echo "❌ Analyse annulée"
            exit 0
        fi
        ;;
    3)
        echo ""
        echo "🎯 Mode ANALYZER MULTIPLE sélectionné"
        echo ""
        echo "📋 Magasins avec captation disponibles:"
        python -c "
from google.cloud import firestore
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
try:
    db = firestore.Client(project='polcoaigeneration-ved6')
    docs = list(db.collection('polco_magasins_captation').stream())
    for doc in sorted(docs, key=lambda x: x.id):
        data = doc.to_dict()
        store_id = data.get('store_id', doc.id.replace('store_', ''))
        store_name = data.get('store_name', 'N/A')
        print(f'   • {store_id} - {store_name}')
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
        
        # Compter les magasins
        IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
        store_count=${#STORE_ARRAY[@]}
        estimated_time=$((store_count * 7))
        
        echo ""
        echo "🎯 Magasins sélectionnés: $store_count magasins"
        echo "⏱️ Temps estimé: ~$estimated_time minutes"
        echo ""
        read -p "🚀 Démarrer l'analyse ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement ANALYZER MULTIPLE..."
            for store_id in "${STORE_ARRAY[@]}"; do
                store_id=$(echo "$store_id" | xargs)  # Trim whitespace
                echo "🔄 Traitement magasin: $store_id"
                python polco_analyzer.py --store-id "$store_id"
            done
        else
            echo "❌ Analyse annulée"
            exit 0
        fi
        ;;
    *)
        echo "❌ Choix invalide. Sortie."
        exit 1
        ;;
esac

echo ""
echo "✅ ANALYZER terminé !"
echo "🌐 Consultez vos résultats dans Firestore (polco_analyzer_3_0)"
