#!/bin/bash

echo "🔍 POLCO CAPTATION - Recherche Google Avancée"
echo "=============================================="
echo ""
echo "🎯 Collecte exhaustive de données locales précises"
echo "   🔍 6 prompts de captation pour un maximum de détails"
echo "   📊 Requêtes Google Search ciblées par prompt"
echo "   📍 Géolocalisation et coordonnées GPS"
echo "   📅 Données récentes et sources officielles"
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

if [ ! -f "prompts/prompt_captation.md" ]; then
    echo "❌ Fichier des prompts non trouvé"
    exit 1
fi

echo "✅ Tous les prérequis sont présents"
echo ""

# Mode d'exécution
echo "🤔 Choisissez le mode d'exécution:"
echo "   1. 📊 CAPTATION COMPLÈTE - Tous les magasins"
echo "   2. 🎯 CAPTATION SPÉCIFIQUE - Un seul magasin"
echo "   3. 🎯 CAPTATION MULTIPLE - Plusieurs magasins (séparés par ;)"
echo ""
read -p "👉 Votre choix (1/2/3): " mode_choice

case $mode_choice in
    1)
        echo ""
        echo "📊 Mode CAPTATION COMPLÈTE sélectionné"
        echo "⏱️ Temps estimé: ~3-4 heures"
        echo ""
        read -p "🚀 Démarrer la captation complète ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement CAPTATION COMPLÈTE..."
            python polco_captation.py
        else
            echo "❌ Captation annulée"
            exit 0
        fi
        ;;
    2)
        echo ""
        echo "🎯 Mode CAPTATION SPÉCIFIQUE sélectionné"
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
        
        echo ""
        echo "🎯 Magasin sélectionné: $store_id"
        echo "⏱️ Temps estimé: ~8-10 minutes"
        echo ""
        read -p "🚀 Démarrer la captation ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement CAPTATION (MAGASIN $store_id)..."
            python polco_captation.py --store-id "$store_id"
        else
            echo "❌ Captation annulée"
            exit 0
        fi
        ;;
    3)
        echo ""
        echo "🎯 Mode CAPTATION MULTIPLE sélectionné"
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
        estimated_time=$((store_count * 9))
        
        echo ""
        echo "🎯 Magasins sélectionnés: $store_count magasins"
        echo "⏱️ Temps estimé: ~$estimated_time minutes"
        echo ""
        read -p "🚀 Démarrer la captation ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement CAPTATION MULTIPLE..."
            for store_id in "${STORE_ARRAY[@]}"; do
                store_id=$(echo "$store_id" | xargs)  # Trim whitespace
                echo "🔄 Traitement magasin: $store_id"
                python polco_captation.py --store-id "$store_id"
            done
        else
            echo "❌ Captation annulée"
            exit 0
        fi
        ;;
    *)
        echo "❌ Choix invalide. Sortie."
        exit 1
        ;;
esac

echo ""
echo "✅ CAPTATION terminée !"
echo "🌐 Consultez vos résultats dans Firestore (polco_magasins_ultra_enhanced)"
