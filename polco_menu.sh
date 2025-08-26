#!/bin/bash

echo "🚀 POLCO - Système d'Analyse Retail Decathlon"
echo "============================================="
echo ""
echo "🎯 Version Production - Mode nominal"
echo ""

# Vérifier les prérequis
if [ ! -f "credentials.json" ]; then
    echo "❌ Fichier credentials.json non trouvé"
    exit 1
fi

echo "✅ Prérequis vérifiés"
echo ""

# Menu principal
echo "🤔 Choisissez votre action :"
echo ""
echo "0. 🚀 MODE FULL - Processus complet automatique"
echo "   ✅ Toutes les étapes dans l'ordre optimal"
echo "   ⏱️ Temps: ~10-15 min/magasin"
echo ""
echo "1. 📤 UPLOAD DONNÉES - Génération CSV + Upload Firestore"
echo "   ✅ Génération CSV depuis AWS Athena"
echo "   ✅ Upload toutes les données magasin vers Firestore"
echo "   ⏱️ Temps: ~10-15 min (génération) + ~1-2 min (upload)"
echo ""
echo "2. 🔍 CAPTATION - Recherche Google précise"
echo "   ✅ 6 prompts de captation + Google Search"
echo "   ✅ Géolocalisation et sources officielles"
echo "   ⏱️ Temps: ~8-10 min/magasin"
echo ""
echo "3. 📊 ANALYZER - Analyses sectorielles 64k+ chars"
echo "   ✅ 5 processeurs spécialisés + graphiques"
echo "   ✅ Rapports ultra-détaillés"
echo "   ⏱️ Temps: ~6-8 min/magasin"
echo ""
echo "4. 📄 EXTRACTION - Rapports Markdown"
echo "   ✅ Génération rapports .md enrichis"
echo "   ✅ Graphiques intégrés"
echo "   ⏱️ Temps: ~quelques secondes"
echo ""
echo "5. 📕 PDF - Conversion professionnelle"
echo "   ✅ PDFs avec mise en forme Decathlon"
echo "   ✅ Graphiques haute définition"
echo "   ⏱️ Temps: ~quelques secondes"
echo ""
echo "6. 🗺️ CARTOGRAPHIE - Visualisations géographiques"
echo "   ✅ Cartes concurrence avec zones d'influence"
echo "   ✅ Infrastructures sportives géolocalisées"
echo "   ✅ Zones isochrones (temps de trajet)"
echo "   ⏱️ Temps: ~2-3 min/magasin"
echo ""

read -p "👉 Votre choix (0/1/2/3/4/5/6): " choice

case $choice in
    0)
        echo ""
        echo "🚀 MODE FULL sélectionné - Processus complet"
        ./polco_full_process.sh
        ;;
    1)
        echo ""
        echo "📤 Lancement UPLOAD des données avec génération CSV..."
        echo "🤔 Voulez-vous générer les CSV depuis AWS Athena ?"
        echo "   y) Oui - Générer CSV + Upload (recommandé)"
        echo "   n) Non - Upload uniquement (données existantes)"
        read -p "👉 Votre choix (y/n): " generate_csv_choice
        
        if [[ $generate_csv_choice =~ ^[Yy]$ ]]; then
            echo ""
            echo "📊 Options de génération CSV :"
            echo "   1) Mode test (1 magasin)"
            echo "   2) Magasin spécifique"
            echo "   3) Limite de magasins"
            echo "   4) Tous les magasins (complet)"
            read -p "👉 Votre choix (1/2/3/4): " csv_option
            
            case $csv_option in
                1)
                    echo "🧪 Mode test - Génération CSV + Upload..."
                    python polco_data_upload.py --generate-csv --test
                    ;;
                2)
                    read -p "👉 ID du magasin (ex: 1912): " store_id
                    echo "🎯 Magasin $store_id - Génération CSV + Upload..."
                    python polco_data_upload.py --generate-csv --store-id $store_id
                    ;;
                3)
                    read -p "👉 Nombre de magasins (ex: 5): " limit
                    echo "📊 Limite $limit magasins - Génération CSV + Upload..."
                    python polco_data_upload.py --generate-csv --limit $limit
                    ;;
                4)
                    echo "🚀 Tous les magasins - Génération CSV + Upload..."
                    python polco_data_upload.py --generate-csv
                    ;;
                *)
                    echo "❌ Choix invalide. Mode complet par défaut."
                    python polco_data_upload.py --generate-csv
                    ;;
            esac
        else
            echo "📤 Upload uniquement..."
            python polco_data_upload.py
        fi
        ;;
    2)
        echo ""
        echo "🔍 Lancement CAPTATION précise..."
        ./polco_captation_runner.sh
        ;;
    3)
        echo ""
        echo "📊 Lancement ANALYZER sectoriels..."
        ./polco_analyzer_runner.sh
        ;;
    4)
        echo ""
        echo "📄 Lancement EXTRACTION Markdown..."
        ./polco_markdown_runner.sh
        ;;
    5)
        echo ""
        echo "📕 Lancement GÉNÉRATION PDF..."
        ./polco_pdf_runner.sh
        ;;
    6)
        echo ""
        echo "🗺️ Lancement CARTOGRAPHIE géographique..."
        ./polco_geo_runner.sh
        ;;
    *)
        echo "❌ Choix invalide. Veuillez choisir 0, 1, 2, 3, 4, 5 ou 6."
        exit 1
        ;;
esac

echo ""
echo "🎉 Terminé ! Consultez vos résultats sur Firestore :"
echo "🌐 https://console.cloud.google.com/firestore/data?project=polcoaigeneration-ved6"
