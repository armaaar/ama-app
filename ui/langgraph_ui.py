"""
UI components for LangGraph RAG in the Streamlit application.
"""
import json
import os
import streamlit as st
from typing import Optional

from modules.auth.auth_service import User
from modules.file.file_service import FileService
from modules.link.link_service import LinkService
from utils.ai_utils import get_retriever_id
from utils.vectorizer import vectorize
from graph.graph import get_graph


class LangGraphUI:
    """
    UI components for LangGraph RAG.
    """

    def __init__(self, file_service: Optional[FileService] = None, link_service: Optional[LinkService] = None):
        """
        Initialize the LangGraphUI.

        Args:
            file_service: FileService instance for accessing user files
            link_service: LinkService instance for accessing user links
        """
        self.file_service = file_service
        self.link_service = link_service

    def render_langgraph_section(self, current_user: Optional[User] = None) -> None:
        """
        Render the LangGraph RAG section.

        Args:
            current_user: Currently authenticated user
        """

        if not current_user:
            st.warning("You must be logged in to use LangGraph RAG.")
            return

        # Check for API keys
        if "OPENAI_API_KEY" not in os.environ:
            st.warning(
                "⚠️ OpenAI API key is not set in environment variables. Please ask your administrator to configure it.")
            return

        # Intro text explaining what LangGraph RAG is
        st.markdown("""
        ### Advanced Multi-Agent System with LangGraph
        
        This tab leverages an Adaptive RAG architecture that intelligently:

        1. **Routes Queries** - Uses an Agentic workflow to deliver precise answers.
        2. **Validates Information** - Evaluates retrieved documents against the original query for relevance and quality.
        3. **Generates Grounded Responses** - Creates answers based on verified information sources.
        4. **Prevents Hallucinations** - Implements a reflecting agent to ensure response accuracy.
        5. **Ensures Relevance** - Verifies that responses directly address your original question.
        6. **Web Search** - Searches the web for relevant websites if needed to check related spare parts or brands.


        Select specific files and links to include in your vector database.
        """)

        # Initialize session state for tracking run history
        if "langgraph_history" not in st.session_state:
            st.session_state.langgraph_history = []

        # Create two columns for file and link selection
        col1, col2 = st.columns(2)

        selected_files = []
        selected_links = []

        # File selection in the first column
        with col1:
            st.subheader("Select Files")

            if self.file_service and current_user:
                # Get user files
                user_files = self.file_service.get_user_files(
                    current_user.user_id)

                if not user_files:
                    st.info("No files available. Upload files from the sidebar.")
                else:
                    # Create a multiselect for files
                    file_options = {
                        f"{file.name}": file for file in user_files}
                    selected_file_names = st.multiselect(
                        "Choose files to include",
                        options=list(file_options.keys())
                    )

                    # Get the selected file objects
                    selected_files = [file_options[name]
                                      for name in selected_file_names]

                    if selected_files:
                        st.success(
                            f"Selected {len(selected_files)} files for RAG")
            else:
                st.info("File service not available.")

        # Link selection in the second column
        with col2:
            st.subheader("Select Links")

            if self.link_service and current_user:
                # Get user links
                user_links = self.link_service.get_user_links(
                    current_user.user_id)

                if not user_links:
                    st.info("No links available. Add links from the sidebar.")
                else:
                    # Create a multiselect for links
                    link_options = {f"{link.url}": link for link in user_links}
                    selected_link_urls = st.multiselect(
                        "Choose links to include",
                        options=list(link_options.keys())
                    )

                    # Get the selected link objects
                    selected_links = [link_options[url]
                                      for url in selected_link_urls]

                    if selected_links:
                        st.success(
                            f"Selected {len(selected_links)} links for RAG")
            else:
                st.info("Link service not available.")

        # Vector Store Settings
        build_index = st.button("Build Index from Selected Files & Links")

        if build_index:
            if not selected_files and not selected_links:
                st.warning(
                    "Please select at least one file or link to build the index.")
            else:
                with st.spinner("Building vector store from selected resources..."):
                    try:
                        success = vectorize(selected_files, selected_links)
                        if success:
                            st.success(
                                "Vector store initialized successfully!")
                        else:
                            st.error(
                                "Failed to initialize vector store.")
                    except Exception as e:
                        st.error(f"Error initializing vector store: {e}")

        # Query input
        st.subheader("Ask a Question")

        messages = st.container()

        def display_result(item, show_question=True):
            if show_question:
                messages.chat_message("user").write(item["question"])
            if item["answer"].startswith("Error"):
                messages.chat_message("ai").error(item["answer"])
            else:
                messages.chat_message("ai").write(item["answer"])
                for event in item["events"]:
                    messages.chat_message("ai").write(event)

        if len(st.session_state.langgraph_history) > 0:
            for item in st.session_state.langgraph_history:
                display_result(item)

        if prompt := st.chat_input("Ask a Question"):

            messages.chat_message("user").write(prompt)
            if not selected_files and not selected_links:
                messages.chat_message("AI").warning(
                    "You haven't selected any files or links. LangGraph will use default sources or web search.")

            with st.spinner("Processing your query with LangGraph..."):
                # Run the query through LangGraph, passing selected files and links
                retriever_id = get_retriever_id(selected_files, selected_links)
                inputs = {"question": prompt, "retriever_id": retriever_id}
                app = get_graph()
                final_state = app.invoke(inputs)
                result = {
                    "question": prompt,
                    "answer": final_state["generation"],
                    "events": []
                }

                # Store in history
                st.session_state.langgraph_history.append(result)
                display_result(result, False)

        # Option to clear history
        if st.session_state.langgraph_history:
            st.download_button(
                label="Download History",
                key="rag_chat_history_download",
                data=json.dumps(st.session_state.langgraph_history, indent=4),
                file_name="rag_chat_history.json",
                mime="application/json",
            )
            if st.button("Clear History"):
                st.session_state.langgraph_history = []
                st.rerun()
