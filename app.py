"""
Main entry point for the Streamlit AMA application.
"""
import torch
from modules.auth.auth_ui import AuthUI
from modules.auth.auth_service import AuthService
from modules.feedback.feedback_service import FeedbackService
from modules.feedback.feedback_ui import FeedbackUI
from ui.langgraph_ui import LangGraphUI
from ui.conventional_ui import ConventionalUI
from modules.link.link_ui import LinkUI
from modules.file.file_ui import FileUI
from modules.link.link_service import LinkService
from modules.file.file_service import FileService
from config.config import APP_TITLE, APP_ICON, APP_LAYOUT
import os
import streamlit as st


torch.classes.__path__ = []


def setup_page_config():
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout=APP_LAYOUT
    )


def setup_environment_variables():
    """Check for required environment variables."""
    # Check for OpenAI API key
    if "OPENAI_API_KEY" not in os.environ:
        st.sidebar.warning(
            "⚠️ OPENAI_API_KEY not set in environment. Some AI features may not work.")

    # Check for Tavily API key
    if "TAVILY_API_KEY" not in os.environ:
        st.sidebar.warning(
            "⚠️ TAVILY_API_KEY not set in environment. Web search functionality will be limited.")


def main():
    """Main application function."""
    setup_page_config()

    # Initialize services
    auth_service = AuthService()
    file_service = FileService()
    link_service = LinkService()
    feedback_service = FeedbackService()

    # Initialize UI components
    auth_ui = AuthUI(auth_service)
    file_ui = FileUI(file_service)
    link_ui = LinkUI(link_service)
    feedback_ui = FeedbackUI(feedback_service, auth_service)
    conventional_ui = ConventionalUI(file_service, link_service)
    langgraph_ui = LangGraphUI(file_service, link_service)

    # Check if user is authenticated
    if not auth_ui.is_authenticated():
        # Show login page
        auth_ui.render_login_page()
        return

    # Get current user
    current_user = auth_ui.get_current_user()
    is_admin = auth_ui.is_current_user_admin()

    # Setup environment variables
    setup_environment_variables()

    # Main page title
    st.title("AMA")
    st.write("### Artificial Maintenance Agent")
    st.write("""#### How to Use This Application

1. **Upload Content** - Add files and links through the sidebar panel on the left handside.

2. **Save Your Content** - Click "Upload Selected Files" or "Add Link" to save content to the database.

3. **Select Sources** - In both "One AI" and "Agents AI" tabs, select your files and/or links from the dropdown menu.

4. **Build Index** - Click "Build Index" to vectorize your content. This step is mandatory before interacting with your files or links.

5. **Ask Questions** - Enter your questions to receive answers from your documents. You can compare responses by asking the same question in both AI interfaces.

6. **Manage Sources** - Use the "Source Management" tab to view or delete your uploaded content if needed.

7. **Download History** - Export your conversation history using the download button in each AI tab.

8. **Provide Feedback** - Share your experience in the "Feedback" section, which is mandatory after using the application.""")

    # Sidebar for user info, logout, file upload, and link management
    with st.sidebar:
        # Show user info and logout button
        auth_ui.render_user_info()
        auth_ui.render_logout_button()

        # File upload section
        st.header("Upload Files")
        st.write(
            "Upload PDF files containing information you'd like to query, then click the 'Upload Selected Files' button.")
        if current_user:
            with st.form(key="file_upload_form"):
                uploaded_files = st.file_uploader("Select files", accept_multiple_files=True,
                                                  help="First select your files, then click 'Upload Selected Files' to process them")
                replace_existing = st.checkbox(
                    "Replace existing files", value=False)
                submit_button = st.form_submit_button("Upload Selected Files")

                if submit_button and uploaded_files:
                    for uploaded_file in uploaded_files:
                        # Get existing files to check for duplicates
                        existing_files = file_service.get_user_files(
                            current_user.user_id)
                        duplicate = any(
                            f.name == uploaded_file.name for f in existing_files)

                        # Handle duplicates based on user preference
                        if duplicate and not replace_existing:
                            st.warning(
                                f"File '{uploaded_file.name}' already exists. Select 'Replace existing files' option to overwrite.")
                            continue
                        elif duplicate and replace_existing:
                            # Delete existing file with the same name
                            for existing_file in existing_files:
                                if existing_file.name == uploaded_file.name:
                                    file_service.delete_file(existing_file.id)
                                    st.info(
                                        f"Replacing existing file: {uploaded_file.name}")
                                    break

                        # Add file to service
                        file_model = file_service.add_file(
                            file=uploaded_file.getbuffer(),
                            filename=uploaded_file.name,
                            file_type=uploaded_file.type,
                            user_id=current_user.user_id
                        )

                        if file_model:
                            st.success(f"Uploaded: {uploaded_file.name}")
                        else:
                            st.error(f"Failed to upload: {uploaded_file.name}")
        else:
            st.warning("Please log in to upload files")

        # Show link management
        st.header("Add Links")
        st.write(
            "Add website URLs containing information you'd like to query, then click the 'Add Link' button.")

        link_ui.render_add_link_section(current_user)

    # Tabs for different sections
    conventional, langgraphTab, sourceManagementTab, feedbackTab = st.tabs(
        ["One AI", "Agents AI", "Source Management", "Feedback"])

    with conventional:
        conventional_ui.render_query_section(current_user)

    with langgraphTab:
        langgraph_ui.render_langgraph_section(current_user)

    with sourceManagementTab:
        file_ui.render_file_management(current_user)
        link_ui.render_link_management(current_user)

    with feedbackTab:
        feedback_ui.render_feedback_form(current_user, is_admin)

    # Footer
    st.markdown("---")
    st.caption("AMA © 2025")


if __name__ == "__main__":
    main()
