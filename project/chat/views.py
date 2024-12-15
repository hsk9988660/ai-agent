from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from .models import KnowledgeBase
from django.contrib.auth import authenticate
from fuzzywuzzy import process
from transformers import pipeline
from docx import Document
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from sentence_transformers import SentenceTransformer, util
import logging

# Load LLM
# Load the LLM pipeline once to avoid reloading it repeatedly
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    qa_model = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")
except Exception as e:
    print(f"Error loading LLM model: {e}")
    qa_model = None

    
class KnowledgeBaseUploadView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        logging.warning(f"Request user: {request.user}")

        # Ensure the user is an admin
        print(f"Request user: {request.user}")  # Add this for debugging

        # if not request.user.is_staff:
        #     return Response({"error": "Only admin users can upload knowledge base files."}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        content = self.extract_content(file)
        if content:
            # Replace existing knowledge base file
            KnowledgeBase.objects.all().delete()
            knowledge_base = KnowledgeBase.objects.create(content=content)
            return Response({"message": "Knowledge base uploaded successfully!", "file_id": knowledge_base.id}, status=status.HTTP_201_CREATED)
        
        return Response({"error": "Invalid file type"}, status=status.HTTP_400_BAD_REQUEST)

    def extract_content(self, file):
        if file.name.endswith('.txt'):
            return file.read().decode('utf-8')
        elif file.name.endswith('.docx'):
            doc = Document(file)
            return " ".join([p.text for p in doc.paragraphs])
        return None

class KnowledgeBaseFileView(APIView):
    def get(self, request):
        """
        Fetches all knowledge base files.
        """
        knowledge_base = KnowledgeBase.objects.all()
        if not knowledge_base:
            return Response({"error": "No knowledge base files found."}, status=status.HTTP_404_NOT_FOUND)

        # Return all files with their ID and preview
        files = [{"id": kb.id, "content_preview": kb.content[:100]} for kb in knowledge_base]
        return Response({"files": files}, status=status.HTTP_200_OK)

    def delete(self, request, pk=None):
        """
        Deletes a specific knowledge base file by ID.
        """
        try:
            knowledge_base = KnowledgeBase.objects.get(pk=pk)
            knowledge_base.delete()
            return Response({"message": f"Knowledge base file with ID {pk} deleted successfully."}, status=status.HTTP_200_OK)
        except KnowledgeBase.DoesNotExist:
            return Response({"error": f"Knowledge base file with ID {pk} not found."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk=None):
        """
        Updates a specific knowledge base file by ID.
        """
        if not pk:
            return Response({"error": "File ID must be provided for update."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        content = self.extract_content(file)
        if not content:
            return Response({"error": "Invalid file type."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            knowledge_base = KnowledgeBase.objects.get(pk=pk)
            knowledge_base.content = content
            knowledge_base.save()
            return Response({"message": f"Knowledge base file with ID {pk} updated successfully."}, status=status.HTTP_200_OK)
        except KnowledgeBase.DoesNotExist:
            return Response({"error": f"Knowledge base file with ID {pk} not found."}, status=status.HTTP_404_NOT_FOUND)

    def extract_content(self, file):
        """
        Extracts content from uploaded .txt or .docx files.
        """
        if file.name.endswith('.txt'):
            return file.read().decode('utf-8')  # Handle text files
        elif file.name.endswith('.docx'):
            doc = Document(file)
            return " ".join([p.text for p in doc.paragraphs])  # Handle Word documents
        return None


class AdminLoginView(APIView):
    """
    Admin login endpoint. Authenticates admin users based on username and password.
    """
    def post(self, request):
        # Extract username and password from the request data
        username = request.data.get('username')
        password = request.data.get('password')

        # Authenticate the user
        user = authenticate(username=username, password=password)

        if user:
            if user.is_staff:  # Ensure the user has admin privileges
                return Response(
                    {"message": "Login successful"},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "You do not have admin privileges"},
                status=status.HTTP_403_FORBIDDEN
            )
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    
class QueryView(APIView):
    """
    Handles user queries using a Retrieval-Augmented Generation (RAG) approach.
    """

    def post(self, request):
        query = request.data.get("query")
        if not query:
            return Response({"error": "No query provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if models are loaded
        if not embedding_model or not qa_model:
            return Response(
                {"response": "Models are unavailable. Please contact the administrator."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Fetch knowledge base content
        knowledge_base = KnowledgeBase.objects.all()
        if not knowledge_base.exists():
            return Response(
                {"response": "The knowledge base is empty. Please contact the admin."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Retrieve the most relevant context
        context = self.retrieve_relevant_context(query, knowledge_base)
        if not context:
            return Response({"response": "I couldn't find enough relevant information for your query."},
                            status=status.HTTP_200_OK)

        # Generate response using the QA model
        response = self.answer_query_with_qa(query, context)
        return Response({"response": response}, status=status.HTTP_200_OK)

    def retrieve_relevant_context(self, query, knowledge_base):
        """
        Retrieves the top N most relevant contexts using sentence embeddings and cosine similarity.
        """
        paragraphs = [kb.content for kb in knowledge_base if kb.content.strip()]  # Filter empty content
        if not paragraphs:
            return None

        # Generate embeddings for the query and all paragraphs
        try:
            query_embedding = embedding_model.encode(query, convert_to_tensor=True)
            paragraph_embeddings = embedding_model.encode(paragraphs, convert_to_tensor=True)

            # Compute cosine similarity
            similarities = util.pytorch_cos_sim(query_embedding, paragraph_embeddings)[0]

            # Sort paragraphs by similarity score
            top_indices = similarities.argsort(descending=True)[:3]  # Retrieve top 3 matches
            top_contexts = [paragraphs[i] for i in top_indices if similarities[i] >= 0.3]  # Threshold = 0.3

            logging.info(f"Top match scores: {[similarities[i].item() for i in top_indices]}")
            return "\n\n".join(top_contexts) if top_contexts else None
        except Exception as e:
            logging.error(f"Error during context retrieval: {e}")
            return None

    def answer_query_with_qa(self, query, context):
        """
        Generates an answer using the QA model based on the retrieved context.
        """
        if not context or len(context.split()) < 10:
            return "I couldn't find enough relevant information for your query."

        try:
            result = qa_model(question=query, context=context)
            answer = result.get("answer", "").strip()

            if answer and len(answer.split()) > 2:  # Validate answer length
                logging.info(f"Generated Answer: {answer}")
                return answer
            else:
                logging.warning("No valid answer generated by the QA model.")
                return "I couldn't find a specific answer to your query. Please try rephrasing it."
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "Sorry, I couldn't process your query at the moment."
            
        
class AdminLogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()  # Deletes the token
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)
