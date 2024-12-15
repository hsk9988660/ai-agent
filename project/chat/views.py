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
import logging
# Load LLM
# Load the LLM pipeline once to avoid reloading it repeatedly
try:
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
    Handles user queries and provides specific answers based on relevant context.
    """

    def post(self, request):
        query = request.data.get("query")
        if not query:
            return Response({"error": "No query provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch knowledge base content
        knowledge_base = KnowledgeBase.objects.first()
        if not knowledge_base:
            return Response({"response": "The knowledge base is empty. Please contact the admin."}, 
                            status=status.HTTP_404_NOT_FOUND)

        # Find the most relevant context
        relevant_context = self.find_relevant_context(query, knowledge_base.content)
        if not relevant_context or len(relevant_context.split()) < 20:  # Ensure the context is valid
            return Response({"response": "I couldn't find enough relevant information for your query."},
                            status=status.HTTP_200_OK)

        # Generate response using the QA model
        response = self.answer_query_with_qa(query, relevant_context)
        return Response({"response": response}, status=status.HTTP_200_OK)

    def find_relevant_context(self, query, knowledge_content):
        """
        Splits knowledge content into paragraphs and finds the most relevant one.
        Combines strict keyword search with fuzzy matching.
        """
        paragraphs = knowledge_content.split("\n\n")  # Split content into paragraphs
        query_keywords = query.lower().split()

        # Step 1: Prioritize exact keyword matches (improved logic)
        for paragraph in paragraphs:
            if all(keyword in paragraph.lower() for keyword in query_keywords[:2]):  # Top keywords must appear
                logging.debug("Keyword-based match found.")
                return paragraph

        # Step 2: Fallback to fuzzy matching if no exact keyword match
        match, score = process.extractOne(query, paragraphs)
        logging.debug(f"Fuzzy match score: {score}")
        if score >= 70 and match.strip():  # Higher threshold to ensure quality
            return match

        return None  # Return None if no suitable context is found


    def answer_query_with_qa(self, query, context):
        """
        Generates an answer using the QA model based on the relevant context.
        """
        if not qa_model:
            return "The QA model is currently unavailable. Please contact the administrator."

        logging.debug(f"Question: {query}")
        logging.debug(f"Context: {context}")

        # Validate the context before sending it to the model
        if not context or len(context.split()) < 20:  # Ensure context has enough words
            return "Sorry, I couldn't find enough relevant information for your query."

        try:
            # Clear and strict prompt for the QA model
            result = qa_model(question=query, context=context)
            answer = result.get("answer", "").strip()

            return answer if answer else "I couldn't find an answer for your query."
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "Sorry, I couldn't process your query at the moment."
            
        
class AdminLogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()  # Deletes the token
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)
