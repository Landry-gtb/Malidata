# 📚 Dossier de Documents Médicaux

Ce dossier contient les documents PDF utilisés par le pipeline RAG pour la base de connaissances.

## 📋 Structure

```
data/
├── README.md (ce fichier)
├── malaria_guide_oms.pdf
├── symptomes_malaria.pdf
├── prevention_malaria.pdf
└── ...
```

## 📥 Comment Ajouter des Documents

### 1. Télécharger les documents
Téléchargez les guides officiels de l'OMS ou d'autres sources médicales fiables:
- [OMS - Malaria](https://www.who.int/malaria/)
- [CDC - Malaria](https://www.cdc.gov/malaria/)
- [Médecins Sans Frontières](https://www.msf.org/)

### 2. Placer les PDFs
Copiez les fichiers PDF dans ce dossier (`backend/data/`)

### 3. Redémarrer le backend
```bash
docker-compose restart backend
```

Le pipeline détectera automatiquement les nouveaux PDFs et recréera l'index FAISS.

## 📊 Documents Recommandés

Pour une base de connaissances complète, incluez:

1. **Guide de diagnostic**
   - Symptômes de la malaria
   - Facteurs de risque
   - Zones endémiques

2. **Prévention**
   - Mesures de protection
   - Traitement préventif
   - Moustiquaires

3. **Traitement**
   - Médicaments antipaludiques
   - Dosages
   - Effets secondaires

4. **Complications**
   - Malaria grave
   - Signes d'urgence
   - Quand consulter

## ⚙️ Configuration

### Taille des chunks
- **Taille**: 1000 caractères
- **Overlap**: 150 caractères
- Modifiable dans `rag_pipeline.py` ligne 136-140

### Modèle d'embedding
- **Modèle**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Temps de chargement**: ~30 secondes

### Index FAISS
- **Type**: IndexFlatL2 (recherche exhaustive)
- **Localisation**: `/app/storage/faiss_index.idx`
- **Métadonnées**: `/app/storage/faiss_index.idx.meta`

## 🔍 Vérifier l'Index

Pour vérifier que l'index a été créé correctement:

```bash
# Voir les logs du backend
docker-compose logs backend | grep -i "rag\|index"

# Vérifier les fichiers
ls -la backend/storage/
```

## 📈 Optimisation

### Ajouter plus de documents
- Plus de documents = meilleure couverture
- Mais aussi plus de temps d'indexation

### Améliorer la qualité
- Utiliser des documents de haute qualité
- Nettoyer les PDFs (OCR si nécessaire)
- Vérifier que le texte est extractible

### Performance
- L'index est chargé en mémoire au démarrage
- Recherche: ~10-50ms par requête
- Génération Gemini: ~1-3 secondes

## 🐛 Dépannage

### L'index n'est pas créé
```
❌ "Aucun document .pdf trouvé dans le dossier 'data'"
```
**Solution**: Vérifiez que les PDFs sont dans `backend/data/`

### Erreur lors du chargement des PDFs
```
❌ "Erreur lors du chargement du document"
```
**Solution**: 
- Vérifiez que les PDFs ne sont pas corrompus
- Essayez avec un PDF simple d'abord
- Vérifiez les permissions de fichier

### Index trop gros
```
❌ "Erreur mémoire lors de la création de l'index"
```
**Solution**:
- Réduisez la taille des chunks
- Utilisez moins de documents
- Utilisez une machine avec plus de RAM

## 📝 Format des Métadonnées

Chaque chunk stocke:
```json
{
  "source": "chemin/vers/document.pdf",
  "page": 5,
  "chunk_index": 42
}
```

## 🔐 Confidentialité

- Les documents ne sont jamais envoyés à Gemini
- Seuls les chunks pertinents sont utilisés
- Les données patient ne sont jamais dans l'index

---

**Note**: Ce dossier est vide par défaut. Ajoutez vos documents PDF pour activer le pipeline RAG.
