#!/bin/bash

echo "🗺️ POLCO GEO-PROCESSOR - Cartographie & Géolocalisation"
echo "======================================================"
echo ""
echo "🎯 Génération de cartes enrichies pour l'analyse géographique"
echo "   🗺️ Carte de la concurrence avec zones d'influence"
echo "   🏃 Infrastructures sportives géolocalisées"
echo "   ⏰ Zones isochrones (temps de trajet)"
echo "   📍 Visualisation de la zone de chalandise"
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
echo "   1. 📊 CARTOGRAPHIE COMPLÈTE - Tous les magasins"
echo "   2. 🎯 CARTOGRAPHIE SPÉCIFIQUE - Un seul magasin"
echo "   3. 🎯 CARTOGRAPHIE MULTIPLE - Plusieurs magasins (séparés par ;)"
echo ""
read -p "👉 Votre choix (1/2/3): " mode_choice

case $mode_choice in
    1)
        echo ""
        echo "📊 Mode CARTOGRAPHIE COMPLÈTE sélectionné"
        echo "⏱️ Temps estimé: ~2-3 minutes/magasin"
        echo ""
        read -p "🚀 Démarrer la cartographie complète ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement CARTOGRAPHIE COMPLÈTE..."
            # TODO: Implémenter le traitement de tous les magasins
            echo "🔄 Traitement en cours..."
            python polco_geo_processor.py --store-id 42
            python polco_geo_processor.py --store-id 115
            python polco_geo_processor.py --store-id 1125
        else
            echo "❌ Cartographie annulée"
            exit 0
        fi
        ;;
    2)
        echo ""
        echo "🎯 Mode CARTOGRAPHIE SPÉCIFIQUE sélectionné"
        echo ""
        echo "📋 Magasins avec analyses disponibles:"
        python -c "
from google.cloud import firestore
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
try:
    db = firestore.Client(project='polcoaigeneration-ved6')
    docs = list(db.collection('polco_analyzer_3_0').stream())
    for doc in sorted(docs, key=lambda x: x.id):
        store_id = doc.id.replace('analyzer_3_0_', '')
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
        echo "⏱️ Temps estimé: ~2-3 minutes"
        echo ""
        read -p "🚀 Démarrer la cartographie ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement CARTOGRAPHIE (MAGASIN $store_id)..."
            python polco_geo_processor.py --store-id "$store_id"
        else
            echo "❌ Cartographie annulée"
            exit 0
        fi
        ;;
    3)
        echo ""
        echo "🎯 Mode CARTOGRAPHIE MULTIPLE sélectionné"
        echo ""
        echo "📋 Magasins avec analyses disponibles:"
        python -c "
from google.cloud import firestore
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
try:
    db = firestore.Client(project='polcoaigeneration-ved6')
    docs = list(db.collection('polco_analyzer_3_0').stream())
    for doc in sorted(docs, key=lambda x: x.id):
        store_id = doc.id.replace('analyzer_3_0_', '')
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
        
        # Compter les magasins
        IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
        store_count=${#STORE_ARRAY[@]}
        estimated_time=$((store_count * 3))
        
        echo ""
        echo "🎯 Magasins sélectionnés: $store_count magasins"
        echo "⏱️ Temps estimé: ~$estimated_time minutes"
        echo ""
        read -p "🚀 Démarrer la cartographie ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement CARTOGRAPHIE MULTIPLE..."
            for store_id in "${STORE_ARRAY[@]}"; do
                store_id=$(echo "$store_id" | xargs)  # Trim whitespace
                echo "🔄 Cartographie magasin: $store_id"
                python polco_geo_processor.py --store-id "$store_id"
            done
        else
            echo "❌ Cartographie annulée"
            exit 0
        fi
        ;;
    *)
        echo "❌ Choix invalide. Sortie."
        exit 1
        ;;
esac

echo ""
echo "✅ CARTOGRAPHIE terminée !"
echo "🗺️ Consultez vos cartes dans: geo_maps/"
echo "📁 Ouvrez les fichiers .html dans votre navigateur pour voir les cartes interactives"



