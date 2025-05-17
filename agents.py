from crewai import Agent, Task, Crew, Process
from crewai_tools import BraveSearchTool
from typing import Optional, List
import os
from dotenv import load_dotenv
from config import LLMConfig

class ResumeScreeningAgents:
    def __init__(self):
        load_dotenv()

        
        # Configure Brave Search
        brave_api_key = os.getenv("BRAVE_API_KEY", "")
        if not brave_api_key:
            raise ValueError("BRAVE_API_KEY not found in environment variables (.env)")
        os.environ["BRAVE_SEARCH_API_KEY"] = brave_api_key  # Set the environment variable that LangChain expects

        # Load LLM config from YAML
        try:
            self.llm_config = LLMConfig.from_yaml()
        except Exception as e:
            raise RuntimeError(f"Failed to load LLM config: {e}")
        
        # Initialize agent attributes
        self.document_processor: Optional[Agent] = None
        self.resume_analyzer: Optional[Agent] = None
        self.job_analyzer: Optional[Agent] = None
        self.researcher: Optional[Agent] = None
        self.matcher: Optional[Agent] = None
        self.report_generator: Optional[Agent] = None
        self.feedback_processor: Optional[FeedbackProcessorAgent] = None #Type hint for specific agent
        
    def _get_llm(self, agent_name: str):
        """Return a LangChain LLM instance based on config for the agent."""
        config = self.llm_config.for_agent(agent_name)
        if config.provider == "openai":
            from langchain_openai import ChatOpenAI
            api_key = config.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env or config.yaml")
            return ChatOpenAI(
                api_key=api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        elif config.provider == "ollama":
            from langchain_ollama import OllamaLLM
            # Only pass supported arguments: model, base_url, temperature
            return OllamaLLM(
                model=config.model_name,
                base_url=config.server_url,
                temperature=config.temperature
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
        
    def create_agents(self):
        """Create all necessary agents for resume screening"""
        
        # Tools initialization
        brave_search = BraveSearchTool(n_results=3) # Limit search results
        
        # 1. Document processor agent
        self.document_processor = Agent(
            role="Document Processing Specialist",
            goal="Extract and structure information from resumes in various formats (PDF, DOCX, HTML, TXT)",
            backstory="""You are an expert in processing resumes in various formats.
            Your strength lies in identifying and extracting key information while
            maintaining the context and relationships between different elements.
            You handle PDF, DOCX, HTML, and TXT formats with equal expertise.""",
            allow_delegation=False,
            llm=self._get_llm("document_processor")
        )
        
        # 2. Resume/Skills analyzer agent
        self.resume_analyzer = Agent(
            role="Resume Analyzer",
            goal="Analyze candidate experience and skills with focus on years in similar positions",
            backstory="""You are a technical expert who can evaluate the depth and
            breadth of technical skills. You understand both current and emerging
            technologies, and can assess a candidate's technical capabilities.
            You excel at determining how long a candidate has worked in relevant positions
            and classifying their experience by categories.""",
            tools=[brave_search],
            allow_delegation=True,
            llm=self._get_llm("skills_analyzer")
        )
        
        # 3. Job description analyzer agent
        self.job_analyzer = Agent(
            role="Job Requirements Analyzer",
            goal="Identify key requirements and prioritize them based on importance",
            backstory="""You are specialized in understanding job descriptions and
            extracting the core requirements. You can distinguish between mandatory
            and preferred skills, and identify critical metrics like minimum years
            of experience or necessary qualifications. You understand what employers
            are really looking for in candidates.""",
            allow_delegation=True,
            llm=self._get_llm("job_analyzer")
        )
        
        # 4. Researcher agent
        self.researcher = Agent(
            role="Candidate Researcher",
            goal="Find additional information about candidates from public sources",
            backstory="""You are a skilled researcher who can find and verify
            professional information from various online sources. You know how to
            validate claims and discover additional context about a candidate's
            experience. You analyze GitHub profiles, social media, technical blogs,
            and professional networks to build a comprehensive picture.""",
            tools=[brave_search],
            allow_delegation=True,
            llm=self._get_llm("researcher")
        )
        
        # 5. Matcher/Evaluator agent
        self.matcher = Agent(
            role="Matching Specialist",
            goal="Calculate match scores between candidates and job requirements",
            backstory="""You are an expert at evaluating how well candidates match
            job requirements. You can weigh different factors appropriately, with
            special attention to years of relevant experience. You create accurate 
            algorithms to determine the best fit and can rank candidates objectively.
            You synthesize information from multiple sources to make well-rounded
            hiring recommendations.""",
            allow_delegation=True,
            llm=self._get_llm("evaluator")
        )
        
        # 6. Report generator agent
        self.report_generator = Agent(
            role="Report Generator",
            goal="Create comprehensive, readable reports on candidate suitability",
            backstory="""You transform complex data into actionable insights and 
            recommendations. You create clear, structured reports that highlight
            key findings about candidates. You excel at visualizing data and
            presenting information in an accessible format. Your reports help
            recruiters and hiring managers make informed decisions quickly.""",
            allow_delegation=False,
            llm=self._get_llm("report_generator")
        )
        
        # 7. Feedback processor agent
        self.feedback_processor = FeedbackProcessorAgent(self._get_llm("feedback_processor"))
        
        return [
            self.document_processor,
            self.resume_analyzer,
            self.job_analyzer,
            self.researcher,
            self.matcher,
            self.report_generator,
            self.feedback_processor
        ]

    def create_tasks(self, resume_path: str, job_description: str, agents_list: List[Agent]): # Renamed agents to agents_list for clarity
        """Create tasks for resume screening"""
        # Validate resume file exists
        if not os.path.exists(resume_path):
            raise FileNotFoundError(f"Resume file not found at: {resume_path}")
            
        # Unpack agents for clarity - assuming agents_list is in the order they were created
        doc_processor_agent, resume_analyzer_agent, job_analyzer_agent, \
        researcher_agent, matcher_agent, report_generator_agent, \
        _ = agents_list # feedback_processor_agent not directly used in these default tasks
        
        return [
            # Task 1: Process the resume document
            Task(
                description=f"""Process the resume at {resume_path}.
                Extract key information including:
                - Personal information (name, contact details)
                - Technical skills and proficiency levels
                - Work experience and responsibilities
                - Education and certifications
                - Projects and achievements
                
                If it's a PDF, use PyMuPDF concepts.
                If it's a DOCX, use python-docx concepts.
                If it's HTML, use BeautifulSoup concepts.
                If it's TXT, use standard text processing.
                
                Format the output as a structured JSON object with clear hierarchical organization.""",
                agent=doc_processor_agent,
                expected_output="A structured JSON object containing all relevant information from the resume."
            ),
            
            # Task 2: Analyze the job description
            Task(
                description=f"""Analyze the following job description:
                {job_description}
                
                Extract and classify requirements as:
                1. Mandatory skills/qualifications
                2. Preferred/nice-to-have skills
                3. Experience requirements (with minimum years if specified)
                4. Education requirements
                5. Soft skills and personal attributes
                
                Prioritize the requirements based on their importance and prominence in the description.
                Format your output as a structured JSON with clear categorization and priority levels.""",
                agent=job_analyzer_agent,
                expected_output="A structured JSON object containing categorized and prioritized job requirements."
            ),
            
            # Task 3: Analyze the candidate's skills and experience
            Task(
                description="""Analyze the technical skills and experience extracted from the resume.
                For each skill mentioned:
                - Validate the skill against current industry standards
                - Assess the depth of experience
                - Check for relevant certifications
                - Look for practical applications in projects
                
                Calculate the total years of experience in relevant positions.
                Classify the experience by categories (e.g., frontend, backend, DevOps).
                Identify the candidate's areas of specialization.
                
                Provide a detailed analysis with confidence scores for each skill assessment.""",
                agent=resume_analyzer_agent,
                expected_output="A detailed analysis of skills with confidence scores and experience metrics."
            ),
            
            # Task 4: Research the candidate
            Task(
                description="""Research and verify the candidate's background:
                - Verify listed companies and positions
                - Look for public work (GitHub, technical blogs, etc.)
                - Find additional projects or contributions
                - Check for relevant industry presence
                - Look for social media profiles that might provide additional insights
                
                Focus on professional information that validates or enhances what's in the resume.
                Compile findings into a comprehensive report, clearly distinguishing between
                verified information and potential matches that need confirmation.""",
                agent=researcher_agent,
                expected_output="A comprehensive report on the candidate's online presence and additional information."
            ),
            
            # Task 5: Calculate match score and evaluate
            Task(
                description="""Analyze all gathered information and calculate a match score:
                1. Compare the candidate's skills and experience against the job requirements
                2. Weigh mandatory requirements more heavily than preferred ones
                3. Give special attention to years of experience in relevant positions
                4. Consider certifications, education, and project experience
                5. Factor in insights from online research
                
                Provide a final evaluation including:
                1. Overall match score (0-100)
                2. Sub-scores for different requirement categories
                3. Key strengths
                4. Potential areas of concern
                5. Hiring recommendation
                6. Suggested interview focus areas
                
                ВАЖЛИВО: У кінці відповіді окремим рядком напиши: Total Match Score: NN, де NN — реальне число від 0 до 100, яке ти розрахував на основі аналізу. Не використовуй XX, не залишай це поле порожнім, обов'язково підстав реальне число.
                IMPORTANT: At the end of your answer, write a separate line: Total Match Score: NN, where NN is a real number from 0 to 100 that you calculated. Do NOT use XX, do NOT leave it blank, always provide a real number.
                Example:
                ...
                Total Match Score: 87
                """,
                agent=matcher_agent,
                expected_output="A detailed match evaluation with scores, strengths, concerns, and recommendations."
            ),
            
            # Task 6: Generate comprehensive report
            Task(
                description="""Generate a comprehensive report based on all previous analyses:
                1. Executive summary with key findings and recommendation
                2. Candidate profile overview
                3. Skills assessment visualization
                4. Experience timeline
                5. Match analysis with detailed scoring
                6. Online presence summary
                7. Areas for further exploration in interviews
                8. Final recommendation
                
                Format the report in a clean, professional structure with clear sections.
                Use markdown formatting for better readability.
                
                ВАЖЛИВО: Використовуй реальні результати попередніх агентів (аналіз навичок, досвіду, job description, оцінку matcher) для формування звіту. Не описуй процес, а генеруй реальний звіт з оцінками та числовим Total Match Score. У кінці звіту окремим рядком напиши: Total Match Score: XX (де XX — число від 0 до 100, яке ти розрахував у попередньому кроці).
                """,
                agent=report_generator_agent,
                expected_output="A comprehensive, well-structured final report in markdown format."
            ),
            
            # Task 7: Request feedback (simulated for CLI, real for UI)
            # This task is more of a placeholder for the CLI flow. 
            # The actual feedback processing is handled by FeedbackProcessorAgent
            # when feedback is submitted through the UI.
            Task(
                description="""This is a placeholder task for the CLI. 
                In the UI, user feedback is processed separately by the FeedbackProcessorAgent.
                For CLI runs, this task simply notes that feedback would be collected in an interactive scenario.""",
                agent=self.feedback_processor, # Assign to an agent, even if it's just a note
                expected_output="A note indicating that feedback processing is typically handled via UI or a dedicated interactive step."
            )
        ]

    def create_crew(self, resume_path: Optional[str] = None, job_description: Optional[str] = None, 
                      agents: Optional[List[Agent]] = None, tasks: Optional[List[Task]] = None, 
                      process: Process = Process.sequential, verbose: bool = True):
        """Create and configure the crew for resume screening or other tasks"""
        
        # If agents and tasks are not provided, create default screening crew
        if agents is None or tasks is None:
            if resume_path is None or job_description is None:
                raise ValueError("Resume path and job description are required for default screening crew.")
            
            created_agents = self.create_agents()
            created_tasks = self.create_tasks(resume_path, job_description, created_agents)
        else:
            created_agents = agents
            created_tasks = tasks
            
        crew = Crew(
            agents=created_agents,
            tasks=created_tasks,
            process=process,
            verbose=verbose
        )
        
        return crew

class FeedbackProcessorAgent(Agent):
    def __init__(self, llm):
        super().__init__(
            role="Feedback Processor",
            goal="Collect and process user feedback to improve system accuracy",
            backstory="""You help the system learn from its successes and mistakes.
                        You analyze feedback from users to identify patterns and opportunities
                        for improvement. You understand how to interpret subjective assessments
                        and translate them into actionable adjustments to the system's algorithms
                        and processes.""",
            llm=llm,
            allow_delegation=False,
            # verbose=True # Uncomment for detailed logging during development
        )

    def process_feedback_task(self, feedback_data: str, original_report: str) -> Task:
        return Task(
            description=f"""Analyze the following user feedback regarding a candidate report:
            User Feedback: {feedback_data}
            Original Report Snippet: {original_report[:1000]}...

            Identify key areas of concern or praise in the feedback.
            Suggest specific, actionable improvements for the resume analysis process, 
            the report generation, or the matching algorithm based on this feedback.
            Consider if the feedback points to issues with specific agent performance or data extraction.
            """,
            agent=self,
            expected_output="A structured analysis of the feedback, including: \n1. Summary of feedback points. \n2. Identified patterns or recurring issues. \n3. Actionable suggestions for system improvement (e.g., adjustments to specific agent prompts, parsing logic, or scoring weights). \n4. Potential impact of implementing the suggested improvements." 
        ) 