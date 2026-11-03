
#!/usr/bin/env bash

# ============================================================
# AFROFANS — BUILD RENDER
# Django + PostgreSQL + Stripe + LiveKit
# ============================================================

set -o errexit

echo "Installation des dépendances AfroFans..."
pip install -r requirements.txt

echo "Vérification Django..."
python manage.py check

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "Application des migrations..."
python manage.py migrate --noinput

echo "Build AfroFans terminé avec succès."
