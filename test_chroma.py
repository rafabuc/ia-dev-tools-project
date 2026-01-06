import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from backend.services.embedding_service import EmbeddingService 
'''
client = chromadb.HttpClient(
    host="localhost",
    port=8001,
    ssl=False,
    headers=None,
    settings=Settings(),
    #settings=Settings(chroma_api_impl="rest", chroma_server_v2=True)
    #tenant=DEFAULT_TENANT,
    #database=DEFAULT_DATABASE,
)

print(client.heartbeat())

#collections = client.list_collections() 
#print(collections)

#col = client.get_collection("test")
#print(col)
'''

def execute_search_related_runbooks(error_summary, limit=5):

    try:
        embedding_service = EmbeddingService(host="localhost", port=8001)

        # Query ChromaDB for relevant runbooks using embedding service
        similar_docs = embedding_service.search_similar_documents(
            query=error_summary,
            n_results=limit
        )

        # Transform results to match expected format
        runbooks = []
        for doc in similar_docs:
            metadata = doc.get("metadata", {})
            runbooks.append({
                "title": metadata.get("title", "Unknown"),
                "category": metadata.get("category", "general"),
                "relevance_score": 1.0 - doc.get("distance", 1.0)  # Convert distance to similarity score
            })

        result = {
            "runbooks": runbooks
        }



        stats = embedding_service.get_collection_stats()

        print(f'stats: {stats}')
        
        return result

    except Exception as e:
        print(e)


execute_search_related_runbooks('test')