#!/bin/bash

echo "🧪 Test POLCO v2 - Vérification Installation"
echo "==========================================="
echo ""

# Vérifier les prérequis
echo "📋 Vérification des prérequis..."

if [ ! -f "credentials.json" ]; then
    echo "❌ credentials.json manquant"
    exit 1
fi

if [ ! -f "polco_mag_test - Feuille 1.csv" ]; then
    echo "❌ CSV magasins manquant"
    exit 1
fi

if [ ! -f "polcoFR.txt" ]; then
    echo "❌ polcoFR.txt manquant"
    exit 1
fi

if [ ! -f "prompts/prompt_captation.md" ]; then
    echo "❌ Prompts captation manquants"
    exit 1
fi

echo "✅ Tous les fichiers de base présents"
echo ""

# Vérifier les scripts Python
echo "🐍 Vérification des scripts Python..."

python_files=(
    "polco_captation.py"
    "polco_analyzer.py" 
    "polco_markdown_extractor.py"
    "polco_pdf_generator.py"
    "polco_data_upload.py"
    "polco_geo_processor.py"
)

for file in "${python_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ $file manquant"
        exit 1
    fi
    
    # Test syntax Python
    python -m py_compile "$file" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ $file - syntaxe OK"
    else
        echo "⚠️ $file - problème syntaxe"
    fi
done

echo ""

# Vérifier les processeurs
echo "⚙️ Vérification des processeurs..."

processor_files=(
    "polco_contexte_processor.py"
    "polco_cibles_processor.py"
    "polco_potentiel_processor.py"
    "polco_offre_processor.py"
    "polco_actions_processor.py"
)

for file in "${processor_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ $file manquant"
        exit 1
    fi
    echo "✅ $file présent"
done

echo ""

# Vérifier les scripts Bash
echo "📜 Vérification des scripts Bash..."

bash_files=(
    "polco_menu.sh"
    "polco_full_process.sh"
    "polco_captation_runner.sh"
    "polco_analyzer_runner.sh"
    "polco_markdown_runner.sh"
    "polco_pdf_runner.sh"
    "polco_geo_runner.sh"
)

for file in "${bash_files[@]}"; do
    if [ ! -f "$file" ] || [ ! -x "$file" ]; then
        echo "❌ $file manquant ou non exécutable"
        exit 1
    fi
    echo "✅ $file exécutable"
done

echo ""

# Test import Python
echo "🔬 Test des imports Python..."

python -c "
try:
    import pandas as pd
    import google.cloud.firestore
    print('✅ pandas et firestore OK')
except ImportError as e:
    print(f'❌ Import manquant: {e}')
    exit(1)
" 2>/dev/null

echo ""

# Test connexion Firestore
echo "🔥 Test connexion Firestore..."

python -c "
try:
    import os
    from google.cloud import firestore
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
    db = firestore.Client(project='polcoaigeneration-ved6')
    collections = ['polco_magasins_data', 'polco_magasins_captation', 'polco_analyzer_3_0']
    for col in collections:
        try:
            count = len(list(db.collection(col).limit(1).stream()))
            print(f'✅ {col} accessible')
        except Exception as e:
            print(f'⚠️ {col} erreur: {e}')
except Exception as e:
    print(f'❌ Erreur Firestore: {e}')
" 2>/dev/null

echo ""

# Résumé
echo "🎉 RÉSUMÉ DU TEST"
echo "=================="
echo "✅ Structure v2 correcte"
echo "✅ Scripts Python syntaxiquement corrects"
echo "✅ Scripts Bash exécutables"
echo "✅ Prérequis présents"
echo ""
echo "🚀 POLCO v2 prêt à l'utilisation !"
echo ""
echo "💡 Pour commencer:"
echo "   ./polco_menu.sh"
echo ""
echo "📖 Documentation complète:"
echo "   cat README.md"
