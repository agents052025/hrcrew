"""
Streamlit web interface for the Resume Screening System
"""

import os
import time
import tempfile
import streamlit as st
from datetime import datetime
from config import LLMConfig
from agents import ResumeScreeningAgents
from document_parsers import parse_resume
import yaml

# Page configuration
st.set_page_config(
    page_title="Resume Screening System",
    page_icon="📄",
    layout="wide"
)

# --- Helper functions ---

def get_models_from_config(provider_name: str, config_data: dict) -> list[str]:
    """Extracts a list of model names for a given provider from config data."""
    models = []
    llm_section = config_data.get("llm", {})
    
    # General provider section
    provider_specific_config = llm_section.get(provider_name.lower())
    if provider_specific_config and "model_name" in provider_specific_config:
        # This usually holds the *default* model for the provider, might not be a list
        # but we can add it if it's a simple string.
        # For now, let's assume agent_specific is the primary source for multiple models.
        pass

    # Agent-specific configurations might list different models
    agent_specific = llm_section.get("agent_specific", {})
    for agent_config in agent_specific.values():
        if agent_config.get("provider") == provider_name.lower() and "model_name" in agent_config:
            models.append(agent_config["model_name"])
            
    # Add the main provider model if defined and not already in the list from agents
    if provider_specific_config and "model_name" in provider_specific_config:
        main_provider_model = provider_specific_config["model_name"]
        if main_provider_model not in models:
            models.append(main_provider_model)
            
    # Add known common models if no models are found, as a fallback.
    # This part can be refined or removed if config.yaml is expected to be exhaustive.
    if not models:
        if provider_name.lower() == "openai":
            models.extend(["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"])
        elif provider_name.lower() == "ollama":
            models.extend(["llama2", "mistral", "llama3"]) # Add more common ollama models

    return list(set(models)) # Return unique models

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp directory and return the path"""
    try:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def update_config_file(config):
    """Update the config.yaml file with new settings"""
    try:
        # Read existing config to preserve other settings
        if os.path.exists("config.yaml"):
            with open("config.yaml", "r") as f:
                existing_config = yaml.safe_load(f)
        else:
            existing_config = {"llm": {}}
        
        # Update relevant parts
        llm_config = existing_config.get("llm", {})
        llm_config["provider"] = config["provider"]
        
        if config["provider"] == "openai":
            if "openai" not in llm_config:
                llm_config["openai"] = {}
            llm_config["openai"]["model_name"] = config["model_name"]
            llm_config["openai"]["temperature"] = config["temperature"]
        elif config["provider"] == "ollama":
            if "ollama" not in llm_config:
                llm_config["ollama"] = {}
            llm_config["ollama"]["server_url"] = config["server_url"]
            llm_config["ollama"]["model_name"] = config["model_name"]
            llm_config["ollama"]["temperature"] = config["temperature"]
        
        existing_config["llm"] = llm_config
        
        # Write updated config
        with open("config.yaml", "w") as f:
            yaml.dump(existing_config, f, default_flow_style=False)
            
        return True
    except Exception as e:
        st.error(f"Error updating config: {e}")
        return False

# --- Main App ---

def main():
    st.title("Resume Screening System")
    
    # Load config.yaml to get model lists and current defaults
    raw_config = {}
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r") as f:
            raw_config = yaml.safe_load(f)
    
    llm_settings_from_config = raw_config.get("llm", {})
    
    # --- Sidebar for LLM Configuration ---
    st.sidebar.title("LLM Configuration")
    
    # Determine default provider from config or use a fallback
    default_provider_from_config = llm_settings_from_config.get("provider", "OpenAI").capitalize()
    
    llm_provider = st.sidebar.selectbox(
        "Select LLM Provider", 
        ["OpenAI", "Ollama"], # Keep this simple, or also derive from config keys
        index=["OpenAI", "Ollama"].index(default_provider_from_config) if default_provider_from_config in ["OpenAI", "Ollama"] else 0
    )
    
    openai_models = get_models_from_config("openai", raw_config)
    ollama_models = get_models_from_config("ollama", raw_config)

    # Determine default model for the selected/default provider
    default_model_for_provider = ""
    if llm_provider == "OpenAI":
        provider_config = llm_settings_from_config.get("openai", {})
        default_model_for_provider = provider_config.get("model_name", "gpt-3.5-turbo")
    else: # Ollama
        provider_config = llm_settings_from_config.get("ollama", {})
        default_model_for_provider = provider_config.get("model_name", "mistral")
        
    if llm_provider == "OpenAI":
        # OpenAI settings
        api_key = st.sidebar.text_input(
            "OpenAI API Key", 
            type="password",
            help="Enter your OpenAI API key. This will be saved to .env file, not in config.yaml."
        )
        model_name = st.sidebar.selectbox(
            "Model", 
            openai_models,
            index=openai_models.index(default_model_for_provider) if default_model_for_provider in openai_models else 0
        )
        server_url = None
    else:  # Ollama
        # Ollama settings
        api_key = None
        server_url = st.sidebar.text_input(
            "Ollama Server URL", 
            value=llm_settings_from_config.get("ollama", {}).get("server_url", "http://localhost:11434")
        )
        model_name = st.sidebar.selectbox(
            "Model", 
            ollama_models,
            index=ollama_models.index(default_model_for_provider) if default_model_for_provider in ollama_models else 0
        )
    
    default_temp = llm_settings_from_config.get(llm_provider.lower(), {}).get("temperature", 0.7)

    temperature = st.sidebar.slider(
        "Temperature", 
        min_value=0.0, 
        max_value=1.0, 
        value=default_temp,
        step=0.1
    )
    
    if st.sidebar.button("Save Configuration"):
        # Save API key to .env if provided
        if api_key:
            env_path = ".env"
            env_text = ""
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    env_text = f.read()
                
                # Update or add OPENAI_API_KEY
                if "OPENAI_API_KEY=" in env_text:
                    env_lines = env_text.split("\n")
                    updated_lines = []
                    for line in env_lines:
                        if line.startswith("OPENAI_API_KEY="):
                            updated_lines.append(f"OPENAI_API_KEY={api_key}")
                        else:
                            updated_lines.append(line)
                    env_text = "\n".join(updated_lines)
                else:
                    env_text += f"\nOPENAI_API_KEY={api_key}"
                
                with open(env_path, "w") as f:
                    f.write(env_text)
            else:
                with open(env_path, "w") as f:
                    f.write(f"OPENAI_API_KEY={api_key}")
        
        # Update config.yaml
        config = {
            "provider": llm_provider.lower(),
            "model_name": model_name,
            "temperature": temperature,
            "server_url": server_url
        }
        
        if update_config_file(config):
            st.sidebar.success("Configuration saved successfully!")
    
    # --- Main content ---
    # File upload area
    upload_col1, upload_col2 = st.columns(2)
    
    with upload_col1:
        resume_file = st.file_uploader(
            "Upload Resume", 
            type=["pdf", "docx", "html", "txt"],
            help="Upload a resume file in PDF, DOCX, HTML, or TXT format."
        )
    
    with upload_col2:
        job_description = st.text_area(
            "Job Description",
            placeholder="Paste the job description here...",
            height=200
        )
    
    if st.button("Analyze", disabled=not (resume_file and job_description)):
        if resume_file and job_description:
            # Show processing status
            with st.status("Processing your request...", expanded=True) as status:
                st.write(f"Analysis in progress with {llm_provider} ({model_name})...")
                
                # Save uploaded resume to temp file
                resume_path = save_uploaded_file(resume_file)
                if not resume_path:
                    st.error("Failed to save resume file.")
                    return
                
                # Step 1: Parse resume
                st.write("Step 1: Parsing resume...")
                parsed_resume = parse_resume(resume_path)
                if "error" in parsed_resume:
                    st.error(f"Error parsing resume: {parsed_resume['error']}")
                    return
                
                # Display basic resume info
                st.write(f"✅ Parsed resume for: {parsed_resume['name']}")
                st.write(f"Found {len(parsed_resume['skills'])} skills and {len(parsed_resume['work_experience'])} work experiences")
                
                # Step 2: Initialize agents and run analysis
                st.write("Step 2: Starting agent analysis...")
                
                # Make it seem like we're making progress
                progress_bar = st.progress(0)
                for i in range(10):
                    # Simulate work
                    progress_bar.progress(i * 10)
                    time.sleep(0.5)  # Simulating work
                
                try:
                    # Initialize agent system
                    agents = ResumeScreeningAgents()
                    crew = agents.create_crew(resume_path, job_description)
                    
                    # Run the crew
                    st.write("Step 3: Running agent crew (this may take a while)...")
                    result = crew.kickoff()
                    
                    # Update status
                    status.update(label="Analysis complete!", state="complete", expanded=False)
                
                except Exception as e:
                    st.error(f"Error running analysis: {str(e)}")
                    status.update(label="Analysis failed", state="error")
                    return
            
            # Display results
            st.success("Analysis complete! Here are the results:")
            
            # Tabs for different sections of the report
            tab1, tab2, tab3, tab4 = st.tabs([
                "Match Score", 
                "Skills Analysis", 
                "Experience", 
                "Online Presence"
            ])
            
            with tab1:
                st.header("Overall Match")
                # Simple placeholder visualization
                if hasattr(result, 'raw'):
                    match_text = result.raw
                else:
                    match_text = str(result)
                
                # --- END DEBUG ---
                
                # Try to find match score in text
                import re
                match_score = 0
                # Updated regex to be more flexible with table formats and whitespace
                score_match = re.search(r"Total Match Score\s*(?:\|[^|\n]*\|)?[^0-9]*(\d{1,3})", match_text, re.IGNORECASE)
                if score_match:
                    # The score will be in group 1 of this new regex
                    matched_score_str = score_match.group(1)
                    try:
                        match_score = int(matched_score_str)
                    except ValueError:
                        # Fallback if conversion fails, though group(1) should be digits
                        match_score = 0 
                else:
                    # Fallback if "Total Match Score ... number" is not found, try the old regex as a last resort
                    # for formats like "Score: XX" or "XX/100"
                    legacy_score_match = re.search(r'(\d{1,3})(?:\s*)?\/(?:\s*)?100|(?:score|match)(?:\s*)?:(?:\s*)?(\d{1,3})', match_text, re.IGNORECASE)
                    if legacy_score_match:
                        matched_score_str = legacy_score_match.group(1) or legacy_score_match.group(2)
                        if matched_score_str:
                            try:
                                match_score = int(matched_score_str)
                            except ValueError:
                                match_score = 0
                
                # Display match score
                st.metric("Match Score", f"{match_score}/100")
                st.markdown(match_text)
            
            with tab2:
                st.header("Skills Analysis")
                if "skills" in parsed_resume:
                    st.write("Skills detected from resume:")
                    skills_list = parsed_resume["skills"]
                    st.write(", ".join(skills_list))
                else:
                    st.write("No skills information available")
            
            with tab3:
                st.header("Experience Assessment")
                if "work_experience" in parsed_resume and parsed_resume["work_experience"]:
                    for exp in parsed_resume["work_experience"]:
                        st.markdown(f"**{exp.get('position', 'Position')}** at **{exp.get('company', 'Company')}**")
                        st.markdown(f"*{exp.get('dates', 'Dates not specified')}*")
                        st.markdown(exp.get('description', ''))
                        st.markdown("---")
                else:
                    st.write("No experience information available")
            
            with tab4:
                st.header("Online Presence & Additional Data")
                st.markdown(match_text)  # We'll use the full result for now
            
            # Feedback section
            st.header("Provide Feedback")
            feedback_rating = st.slider("Rate the accuracy of this analysis (1=Poor, 5=Excellent)", 1, 5, 3)
            feedback_text = st.text_area("Additional feedback (e.g., what was missed, what was good?)")
            
            if st.button("Submit Feedback"):
                if feedback_text:
                    with st.spinner("Processing your feedback..."):
                        try:
                            # Assuming 'agents' is the ResumeScreeningAgents instance
                            # and 'result' is the output from the main crew.kickoff()
                            feedback_agent = agents.feedback_processor # Get the agent instance
                            
                            # Create the feedback processing task
                            # We need the original report for context
                            original_report_str = str(result) 
                            
                            feedback_task = feedback_agent.process_feedback_task(
                                feedback_data=f"Rating: {feedback_rating}/5. Comments: {feedback_text}",
                                original_report=original_report_str
                            )
                            
                            # Create a new crew for just this task
                            feedback_crew = agents.create_crew(
                                agents=[feedback_agent],
                                tasks=[feedback_task],
                                verbose=False # Keep this less verbose for UI
                            )
                            
                            feedback_analysis_result = feedback_crew.kickoff()
                            
                            st.success("Feedback submitted and processed!")
                            st.markdown("**Feedback Analysis:**")
                            st.markdown(feedback_analysis_result)

                            # Optionally, save this feedback analysis
                            feedback_save_path = os.path.join("reports", f"feedback_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                            with open(feedback_save_path, 'w', encoding='utf-8') as f:
                                f.write(f"Original Report:\n{original_report_str}\n\n")
                                f.write(f"User Feedback (Rating: {feedback_rating}/5):\n{feedback_text}\n\n")
                                f.write(f"Feedback Analysis:\n{feedback_analysis_result}")
                            st.info(f"Feedback analysis saved to {feedback_save_path}")
                            
                        except Exception as e:
                            st.error(f"Error processing feedback: {e}")
                else:
                    st.warning("Please provide some textual feedback.")


if __name__ == "__main__":
    main() 