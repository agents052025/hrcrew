"""
Main script for the Resume Screening System
"""

import os
import json
import argparse
import datetime
from dotenv import load_dotenv
from agents import ResumeScreeningAgents
from document_parsers import parse_resume
from config import LLMConfig
from analysis_manager import AnalysisManager

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Resume Screening System")
    parser.add_argument("--resume", type=str,
                      help="Path to the resume file (PDF, DOCX, HTML, TXT)")
    parser.add_argument("--job_description", type=str,
                      help="Path to job description file or raw text")
    parser.add_argument("--config", type=str, default="config.yaml",
                      help="Path to configuration file (default: config.yaml)")
    parser.add_argument("--provider", type=str, choices=["openai", "ollama"],
                      help="Override LLM provider from config")
    parser.add_argument("--parse_only", action="store_true",
                      help="Only parse the resume without running the full analysis")
    parser.add_argument("--output", type=str,
                      help="Path to save analysis results (default: reports/[name]_[timestamp].json)")
    parser.add_argument("--reports-dir", type=str, default="reports",
                      help="Directory to store reports (default: reports)")
    parser.add_argument("--compare", type=str,
                      help="Compare candidate reports for a job (provide job keyword)")
    parser.add_argument("--list-reports", action="store_true",
                      help="List all available reports")
    args = parser.parse_args()
    
    # Initialize analysis manager
    analysis_manager = AnalysisManager(args.reports_dir)
    
    # Load environment variables
    load_dotenv()
    
    # List reports mode
    if args.list_reports:
        reports = analysis_manager.list_reports()
        if not reports:
            print("No reports found.")
            return
            
        print(f"\nFound {len(reports)} reports:")
        for path in reports:
            try:
                report = analysis_manager.load_report(path)
                name = report.get("candidate_name", "Unknown")
                date = report.get("timestamp", "Unknown")
                print(f"- {os.path.basename(path)}: {name} ({date})")
            except Exception as e:
                print(f"- {os.path.basename(path)}: Error: {str(e)}")
        return
    
    # Compare mode
    if args.compare:
        print(f"\nComparing candidates for job: {args.compare}")
        comparison = analysis_manager.generate_comparison_report(args.compare)
        
        if "error" in comparison:
            print(f"Error: {comparison['error']}")
            return
            
        # Print comparison results
        print("\n" + "=" * 50)
        print("CANDIDATE COMPARISON")
        print("=" * 50)
        
        # Print rankings
        print("\nRankings by match score:")
        for i, (name, score) in enumerate(comparison["scoring"]["ordered_ranking"], 1):
            print(f"{i}. {name}: {score}/100")
        
        # Print skill comparison
        print("\nSkill comparison:")
        for skill, candidates in comparison["skill_comparison"].items():
            print(f"- {skill}: {', '.join(candidates)}")
        
        # Ask if user wants to save comparison
        save_path = os.path.join(args.reports_dir, f"comparison_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)
        print(f"\nComparison saved to: {save_path}")
        return
    
    # Regular mode requires resume and job description
    if not args.resume or not args.job_description:
        parser.print_help()
        return
    
    # Check if API keys are set
    if "OPENAI_API_KEY" not in os.environ and args.provider != "ollama":
        print("WARNING: OPENAI_API_KEY not found in environment variables.")
        print("If using OpenAI, make sure to set this in your .env file.")
    
    if "BRAVE_API_KEY" not in os.environ:
        print("WARNING: BRAVE_API_KEY not found in environment variables.")
        print("Web search functionality will be limited.")
    
    # Check if resume file exists
    if not os.path.exists(args.resume):
        print(f"Error: Resume file not found at {args.resume}")
        return
    
    # Get job description from file or use raw text
    job_description = args.job_description
    if os.path.exists(job_description):
        with open(job_description, 'r', encoding='utf-8') as f:
            job_description = f.read()
    
    print(f"\n{'=' * 50}")
    print(f"RESUME SCREENING SYSTEM")
    print(f"{'=' * 50}")
    print(f"Resume: {args.resume}")
    print(f"Configuration: {args.config}")
    
    # Step 1: Parse resume
    print("\n[1] PARSING RESUME...")
    parsed_resume = parse_resume(args.resume)
    
    if "error" in parsed_resume:
        print(f"Error parsing resume: {parsed_resume['error']}")
        return
    
    # Display basic resume info
    print(f"\nCandidate: {parsed_resume['name']}")
    print(f"Contact: {parsed_resume['contact_information'].get('email', 'N/A')}")
    print(f"Skills found: {len(parsed_resume['skills'])}")
    print(f"- {', '.join(parsed_resume['skills'][:5])}{'...' if len(parsed_resume['skills']) > 5 else ''}")
    print(f"Work Experience: {len(parsed_resume['work_experience'])} positions")
    
    # If parse_only flag is set, print the parsed resume as JSON and exit
    if args.parse_only:
        print("\nParsed Resume (JSON):")
        # Remove full_text to make output cleaner
        if "full_text" in parsed_resume:
            parsed_resume_display = parsed_resume.copy()
            del parsed_resume_display["full_text"]
            print(json.dumps(parsed_resume_display, indent=2))
        else:
            print(json.dumps(parsed_resume, indent=2))
            
        # Save parsed resume if requested
        if args.output:
            output_path = analysis_manager.save_report("parse_only", parsed_resume, job_description, args.output)
            print(f"\nParsed resume saved to: {output_path}")
        return
    
    # Step 2: Initialize agents
    print("\n[2] INITIALIZING AGENT SYSTEM...")
    try:
        # Override LLM provider if specified
        if args.provider:
            config = LLMConfig.from_yaml(args.config)
            config.provider = args.provider
            print(f"Using LLM provider: {config.provider}")
        
        # Initialize agent system
        agents = ResumeScreeningAgents()
        print("Agent system initialized successfully.")
        
        # Create the crew
        print("\n[3] CREATING AGENT CREW...")
        crew = agents.create_crew(args.resume, job_description)
        print("Created crew with the following agents:")
        for agent in agents.create_agents():
            print(f"- {agent.role}")
        
        # Run the analysis
        print("\n[4] RUNNING ANALYSIS...")
        print("This may take several minutes depending on your LLM provider and the complexity of the resume...")
        result = crew.kickoff()
        
        # Print the results
        print("\n" + "=" * 50)
        print("ANALYSIS COMPLETE")
        print("=" * 50)
        print(result)
        
        # Save results
        output_path = analysis_manager.save_report(result, parsed_resume, job_description, args.output)
        print(f"\nAnalysis results saved to: {output_path}")
        
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 