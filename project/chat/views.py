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
import torch
import re

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
    
def preprocess_knowledge_base(knowledge_entries):
    """
    Preprocess and split knowledge base content into clean paragraphs.
    """
    paragraphs = []
    for entry in knowledge_entries:
        content = entry.strip()
        # Split paragraphs using double newlines or full stops
        split_content = re.split(r"\n\n|\.\s+", content)
        cleaned_paragraphs = [para.strip() for para in split_content if len(para.strip()) > 20]  # Min length = 20
        paragraphs.extend(cleaned_paragraphs)
    return paragraphs

class QueryView(APIView):
    """
    Handles user queries using Retrieval-Augmented Generation (RAG) approach.
    Combines multiple top contexts for QA model input.
    """

    def post(self, request):
        query = request.data.get("query", "").strip()
        if not query:
            return Response({"error": "No query provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Check models
        if not embedding_model or not qa_model:
            logging.error("Models not loaded.")
            return Response({"response": "Models are unavailable. Please contact the administrator."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Retrieve knowledge base
        knowledge_base = self.get_knowledge_base()
        if not knowledge_base:
            return Response({"response": "The knowledge base is empty. Please contact the admin."},
                            status=status.HTTP_404_NOT_FOUND)

        # Retrieve relevant context
        context = self.retrieve_relevant_context(query, knowledge_base)
        if not context:
            return Response({"response": "I couldn't find enough relevant information for your query."},
                            status=status.HTTP_200_OK)

        # Generate answer
        response = self.answer_query_with_qa(query, context)
        return Response({"response": response}, status=status.HTTP_200_OK)

    def get_knowledge_base(self):
        """
        Fetch and preprocess knowledge base content.
        """
        try:
            knowledge_entries = KnowledgeBase.objects.all()
            paragraphs = [entry.content.strip() for entry in knowledge_entries if entry.content.strip()]
            return self.preprocess_paragraphs(paragraphs)
        except Exception as e:
            logging.error(f"Error fetching knowledge base: {e}")
            return []

    def preprocess_paragraphs(self, content_list):
        """
        Split and clean paragraphs into meaningful chunks.
        """
        paragraphs = []
        for content in content_list:
            split_content = re.split(r"\n\n|\.\s+", content)  # Split at double newlines or full stops
            cleaned = [para.strip() for para in split_content if len(para.strip()) > 20]  # Min length = 20
            paragraphs.extend(cleaned)
        return paragraphs

    def retrieve_relevant_context(self, query, knowledge_base):
        """
        Retrieve the top-3 relevant contexts using semantic similarity.
        """
        try:
            query_embedding = embedding_model.encode(query, convert_to_tensor=True)
            paragraph_embeddings = embedding_model.encode(knowledge_base, convert_to_tensor=True)

            # Compute cosine similarity
            similarities = util.pytorch_cos_sim(query_embedding, paragraph_embeddings)[0]
            top_indices = torch.topk(similarities, k=5).indices  # Top-5 matches

            # Combine top paragraphs
            top_contexts = [knowledge_base[i] for i in top_indices if similarities[i].item() >= 0.2]
            return "\n\n".join(top_contexts) if top_contexts else None
        except Exception as e:
            logging.error(f"Error retrieving context: {e}")
            return None

    def answer_query_with_qa(self, query, context):
        """
        Use the QA model to generate an answer based on retrieved context.
        """
        try:
            logging.info(f"QA Model Input - Query: {query}")
            logging.info(f"QA Model Input - Context: {context}")

            if not context:
                return "No relevant context found."

            result = qa_model(question=query, context=context)
            answer = result.get("answer", "").strip()

            return answer if answer else "I couldn't find a specific answer to your query."
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "Sorry, I couldn't process your query at the moment."
            
        
class AdminLogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()  # Deletes the token
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)
