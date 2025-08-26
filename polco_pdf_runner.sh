#!/bin/bash

echo "📕 POLCO PDF - Conversion Professionnelle"
echo "========================================"
echo ""
echo "🎯 Conversion des rapports Markdown vers PDFs professionnels"
echo "   📄 Mise en forme Decathlon haute qualité"
echo "   📊 Graphiques haute définition intégrés"
echo "   🎨 CSS professionnel pour listes et tableaux"
echo ""

# Vérifier les prérequis
if [ ! -f "credentials.json" ]; then
    echo "❌ Fichier credentials.json non trouvé"
    exit 1
fi

# Vérifier pandoc
if ! command -v pandoc &> /dev/null; then
    echo "❌ pandoc non installé"
    echo "💡 Installez avec: brew install pandoc (macOS) ou apt install pandoc (Linux)"
    exit 1
fi

echo "✅ Prérequis vérifiés"
echo ""

# Vérifier les rapports Markdown disponibles
if [ ! -d "reports_polco_3_0" ]; then
    echo "❌ Aucun rapport Markdown disponible"
    echo ""
    echo "💡 Lancez d'abord l'EXTRACTION (option 4 du menu principal)"
    exit 1
fi

MD_COUNT=$(ls -1 reports_polco_3_0/*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$MD_COUNT" -eq 0 ]; then
    echo "❌ Aucun rapport Markdown trouvé dans reports_polco_3_0/"
    exit 1
fi

echo "✅ $MD_COUNT rapports Markdown disponibles"
echo ""

# Mode de génération PDF
echo "🤔 Choisissez le mode de génération PDF:"
echo "   1. 📊 PDF COMPLET - Tous les rapports"
echo "   2. 🎯 PDF SPÉCIFIQUE - Un seul rapport"
echo "   3. 🎯 PDF MULTIPLE - Plusieurs rapports (séparés par ;)"
echo ""
read -p "👉 Votre choix (1/2/3): " mode_choice

case $mode_choice in
    1)
        echo ""
        echo "📊 Mode PDF COMPLET sélectionné"
        echo "⏱️ Temps estimé: ~$((MD_COUNT * 5)) secondes"
        echo ""
        read -p "🚀 Démarrer la génération complète ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement PDF COMPLET..."
            python polco_pdf_generator.py
        else
            echo "❌ Génération annulée"
            exit 0
        fi
        ;;
    2)
        echo ""
        echo "🎯 Mode PDF SPÉCIFIQUE sélectionné"
        echo ""
        echo "📋 Rapports disponibles:"
        for md_file in reports_polco_3_0/POLCO_3_0_DECATHLON_*_Analyse_Sectorielle.md; do
            if [ -f "$md_file" ]; then
                basename=$(basename "$md_file" .md)
                store_id=$(echo "$basename" | sed 's/POLCO_3_0_DECATHLON_\(.*\)_Analyse_Sectorielle/\1/')
                echo "   • $store_id"
            fi
        done
        echo ""
        read -p "🎯 Entrez l'ID du magasin: " store_id
        
        if [[ -z "$store_id" ]]; then
            echo "❌ Aucun ID saisi. Sortie."
            exit 1
        fi
        
        # Vérifier que le fichier existe
        md_file="reports_polco_3_0/POLCO_3_0_DECATHLON_${store_id}_Analyse_Sectorielle.md"
        if [ ! -f "$md_file" ]; then
            echo "❌ Rapport non trouvé: $md_file"
            exit 1
        fi
        
        echo ""
        echo "🎯 Rapport sélectionné: $store_id"
        echo "⏱️ Temps estimé: ~5 secondes"
        echo ""
        read -p "🚀 Démarrer la génération ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement PDF (MAGASIN $store_id)..."
            python polco_pdf_generator.py "$store_id"
        else
            echo "❌ Génération annulée"
            exit 0
        fi
        ;;
    3)
        echo ""
        echo "🎯 Mode PDF MULTIPLE sélectionné"
        echo ""
        echo "📋 Rapports disponibles:"
        for md_file in reports_polco_3_0/POLCO_3_0_DECATHLON_*_Analyse_Sectorielle.md; do
            if [ -f "$md_file" ]; then
                basename=$(basename "$md_file" .md)
                store_id=$(echo "$basename" | sed 's/POLCO_3_0_DECATHLON_\(.*\)_Analyse_Sectorielle/\1/')
                echo "   • $store_id"
            fi
        done
        echo ""
        echo "💡 Entrez les IDs séparés par ';' (ex: 42;115;1125)"
        read -p "🎯 IDs des magasins: " store_ids
        
        if [[ -z "$store_ids" ]]; then
            echo "❌ Aucun ID saisi. Sortie."
            exit 1
        fi
        
        # Compter les rapports
        IFS=';' read -ra STORE_ARRAY <<< "$store_ids"
        store_count=${#STORE_ARRAY[@]}
        
        echo ""
        echo "🎯 Rapports sélectionnés: $store_count rapports"
        echo "⏱️ Temps estimé: ~$((store_count * 5)) secondes"
        echo ""
        read -p "🚀 Démarrer la génération ? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo ""
            echo "🚀 Lancement PDF MULTIPLE..."
            for store_id in "${STORE_ARRAY[@]}"; do
                store_id=$(echo "$store_id" | xargs)  # Trim whitespace
                echo "🔄 Génération PDF: $store_id"
                python polco_pdf_generator.py --store-id "$store_id"
            done
        else
            echo "❌ Génération annulée"
            exit 0
        fi
        ;;
    *)
        echo "❌ Choix invalide. Sortie."
        exit 1
        ;;
esac

echo ""
echo "✅ PDF terminé !"
echo "📁 Consultez vos PDFs dans: pdfs_polco_3_0/"



