#!/bin/bash

# Resume Screening System Runner Script
echo "Resume Screening System"
echo "======================="

# Ensure virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Virtual environment not activated. Activating venv..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Error: venv directory not found. Please run: python -m venv venv"
        exit 1
    fi
fi

# Check if required python packages are installed
if ! python -c "import crewai, langchain_core" &> /dev/null; then
    echo "Installing required packages..."
    pip install -r requirements.txt
fi

# Define files
RESUME="resumes/example_resume.txt"
JOB_DESC="job_descriptions/senior_ml_engineer.txt"

# Make sure directories exist
mkdir -p resumes job_descriptions

# Check if files exist
if [ ! -f "$RESUME" ]; then
    echo "Error: Example resume not found at $RESUME"
    exit 1
fi

if [ ! -f "$JOB_DESC" ]; then
    echo "Error: Job description not found at $JOB_DESC"
    exit 1
fi

# Parse command line arguments
MODE=""
PROVIDER=""
OUTPUT=""
REPORTS_DIR=""
COMPARE=""
LIST_REPORTS=false

# Display usage
function show_help {
    echo "Usage: ./run.sh [options]"
    echo "Options:"
    echo "  --parse-only          Only parse the resume without running full analysis"
    echo "  --openai              Use OpenAI as the LLM provider"
    echo "  --ollama              Use Ollama as the LLM provider"
    echo "  --output FILE         Specify output file for results"
    echo "  --reports-dir DIR     Specify custom directory for reports (default: ./reports)"
    echo "  --compare KEYWORD     Compare candidates for jobs matching a keyword"
    echo "  --list-reports        List all available reports"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh --parse-only             # Only parse the resume"
    echo "  ./run.sh --openai                 # Run full analysis with OpenAI"
    echo "  ./run.sh --ollama                 # Run full analysis with Ollama"
    echo "  ./run.sh --output results.json    # Save results to specific file"
    echo "  ./run.sh --compare \"Machine Learning\"  # Compare candidates for ML jobs"
    echo "  ./run.sh --list-reports           # List all available reports"
}

# Process arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --parse-only) MODE="parse-only" ;;
        --openai) PROVIDER="openai" ;;
        --ollama) PROVIDER="ollama" ;;
        --output) OUTPUT="$2"; shift ;;
        --reports-dir) REPORTS_DIR="$2"; shift ;;
        --compare) COMPARE="$2"; shift ;;
        --list-reports) LIST_REPORTS=true ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

# Make sure reports directory exists
if [ -n "$REPORTS_DIR" ]; then
    mkdir -p "$REPORTS_DIR"
else
    mkdir -p reports
fi

# Build command
CMD="python main.py"

# Add common options
if [ -n "$REPORTS_DIR" ]; then
    CMD="$CMD --reports-dir $REPORTS_DIR"
fi

# Handle different modes
if [ "$LIST_REPORTS" = true ]; then
    # List reports mode
    CMD="$CMD --list-reports"
elif [ -n "$COMPARE" ]; then
    # Compare mode
    CMD="$CMD --compare \"$COMPARE\""
elif [ "$MODE" = "parse-only" ]; then
    # Parse-only mode
    CMD="$CMD --resume $RESUME --job_description $JOB_DESC --parse_only"
    if [ -n "$OUTPUT" ]; then
        CMD="$CMD --output $OUTPUT"
    fi
else
    # Regular analysis mode
    CMD="$CMD --resume $RESUME --job_description $JOB_DESC"
    if [ -n "$PROVIDER" ]; then
        CMD="$CMD --provider $PROVIDER"
    fi
    if [ -n "$OUTPUT" ]; then
        CMD="$CMD --output $OUTPUT"
    fi
fi

# Skip API checks for list-reports and compare mode
if [ "$LIST_REPORTS" != true ] && [ -z "$COMPARE" ]; then
    # Check if using OpenAI and OPENAI_API_KEY is not set
    if [ "$PROVIDER" = "openai" ] && [ -z "$OPENAI_API_KEY" ]; then
        if [ -f ".env" ]; then
            source .env
        fi
        
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "Warning: OPENAI_API_KEY not set. Please set it in .env file or export it."
            echo "Continuing, but analysis will likely fail..."
        fi
    fi

    # Check if using Ollama and server is running
    if [ "$PROVIDER" = "ollama" ]; then
        # Simple check if Ollama server is running (may not be perfect)
        if ! curl --silent --head --fail http://localhost:11434/api/version > /dev/null; then
            echo "Warning: Ollama server does not appear to be running."
            echo "Please start Ollama with 'ollama serve' in another terminal."
            echo "Continuing, but analysis will likely fail..."
        fi
    fi
fi

# Run the command
echo ""
echo "Running: $CMD"
echo "---------------------"
eval $CMD

# Clean exit
exit 0 