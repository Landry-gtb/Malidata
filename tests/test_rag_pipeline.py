import asyncio
import os
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).parent))

from rag_pipeline import RAGPipeline


async def test_rag_pipeline():
    """Tester le pipeline RAG"""
    
    print("\n" + "="*60)
    print("🧪 TEST RAG PIPELINE")
    print("="*60 + "\n")
    
    try:
        # 1. Initialiser le pipeline
        print("1️⃣  Initialisation du pipeline RAG...")
        pipeline = RAGPipeline()
        print("✅ Pipeline créé\n")
        
        # 2. Initialiser (charger/créer index)
        print("2️⃣  Initialisation de l'index FAISS...")
        await pipeline.initialize()
        print("✅ Index initialisé\n")
        
        # 3. Afficher les stats
        print("3️⃣  Statistiques du pipeline:")
        stats = pipeline.get_stats()
        for key, value in stats.items():
            print(f"   - {key}: {value}")
        print()
        
        # 4. Tester generate_response (message d'accueil)
        print("4️⃣  Test message d'accueil...")
        response = await pipeline.generate_response(
            query="Message d'accueil initial",
            conversation_history=[],
            user_info={}
        )
        print(f"   Réponse: {response['answer'][:100]}...")
        print(f"   Confidence: {response['confidence']}\n")
        
        # 5. Tester generate_response (question feeling)
        print("5️⃣  Test question feeling...")
        response = await pipeline.generate_response(
            query="Remercier Jean et demander comment il se sent",
            conversation_history=[],
            user_info={"pseudonyme": "Jean"}
        )
        print(f"   Réponse: {response['answer'][:100]}...")
        print(f"   Confidence: {response['confidence']}\n")
        
        # 6. Tester generate_response (fin questionnaire)
        print("6️⃣  Test fin questionnaire...")
        response = await pipeline.generate_response(
            query="Fin du questionnaire médical",
            conversation_history=[],
            user_info={}
        )
        print(f"   Réponse: {response['answer'][:100]}...")
        print(f"   Needs Report: {response['needs_report']}\n")
        
        # 7. Tester analyze_symptoms_for_report
        print("7️⃣  Test analyse symptômes pour rapport...")
        user_info = {
            "pseudonyme": "Jean",
            "age": "35",
            "sexe": "M",
            "telephone": "+33612345678"
        }
        responses = [
            {"role": "user", "content": "J'ai de la fièvre depuis 3 jours"},
            {"role": "user", "content": "Oui, j'ai des frissons"},
            {"role": "user", "content": "Oui, maux de tête intenses"},
            {"role": "user", "content": "Oui, nausées"},
            {"role": "user", "content": "Oui, j'ai voyagé en Afrique"},
            {"role": "user", "content": "Non, pas de traitement préventif"},
            {"role": "user", "content": "Oui, très fatigué"}
        ]
        
        analysis = await pipeline.analyze_symptoms_for_report(user_info, responses)
        print(f"   Résumé: {analysis.get('resume_symptomes', 'N/A')[:100]}...")
        print(f"   Niveau urgence: {analysis.get('niveau_urgence', 'N/A')}")
        print(f"   Facteurs risque: {analysis.get('facteurs_risque', [])}\n")
        
        print("="*60)
        print("✅ TOUS LES TESTS SONT PASSÉS!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_rag_pipeline())
