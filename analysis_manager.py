"""
Analysis Manager for handling resume analysis reports and comparisons.
"""

import os
import json
import glob
import datetime
from typing import List, Dict, Any, Optional, Tuple

class AnalysisManager:
    """Manager for resume analysis reports"""
    
    def __init__(self, reports_dir: str = "reports"):
        """Initialize with reports directory"""
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
    
    def save_report(self, result: Any, parsed_resume: Dict, job_description: str, 
                   output_path: Optional[str] = None) -> str:
        """Save analysis results to a JSON file"""
        # Format timestamp for filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use provided output path or generate default filename
        if output_path:
            # Ensure it has .json extension
            if not output_path.endswith('.json'):
                output_path += '.json'
        else:
            candidate_name = parsed_resume.get('name', 'unknown').replace(' ', '_').lower()
            output_path = os.path.join(self.reports_dir, f"{candidate_name}_{timestamp}.json")
        
        # Prepare data to save
        data = {
            "timestamp": timestamp,
            "candidate_name": parsed_resume.get('name'),
            "parsed_resume": {k: v for k, v in parsed_resume.items() if k != 'full_text'},
            "job_description": job_description,
            "analysis_result": str(result)
        }
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return output_path
    
    def load_report(self, file_path: str) -> Dict:
        """Load an analysis report from a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load report {file_path}: {str(e)}")
    
    def list_reports(self) -> List[str]:
        """List all report files in the reports directory"""
        return glob.glob(os.path.join(self.reports_dir, "*.json"))
    
    def get_reports_for_job(self, job_keyword: str) -> List[str]:
        """Find reports that match a specific job keyword"""
        matching_reports = []
        for report_path in self.list_reports():
            try:
                report = self.load_report(report_path)
                if job_keyword.lower() in report.get("job_description", "").lower():
                    matching_reports.append(report_path)
            except Exception:
                # Skip invalid reports
                continue
        return matching_reports
    
    def get_candidate_match_scores(self, report_paths: List[str]) -> List[Tuple[str, int, str]]:
        """
        Extract match scores from multiple reports
        Returns: List of (candidate_name, score, report_path) tuples
        """
        results = []
        
        for path in report_paths:
            try:
                report = self.load_report(path)
                name = report.get("candidate_name", "Unknown")
                
                # Try to extract match score from analysis result
                analysis = report.get("analysis_result", "")
                
                # Look for patterns like "Score: 85/100" or "Match: 85%"
                import re
                score_match = re.search(r'(\d{1,3})(?:\s*)?\/(?:\s*)?100|(?:score|match)(?:\s*)?:(?:\s*)?(\d{1,3})', 
                                      analysis, re.IGNORECASE)
                
                score = 0
                if score_match:
                    matched_score = score_match.group(1) or score_match.group(2)
                    try:
                        score = int(matched_score)
                    except ValueError:
                        pass
                
                results.append((name, score, path))
            except Exception:
                # Skip invalid reports
                continue
        
        # Sort by score (highest first)
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def compare_candidates(self, report_paths: List[str]) -> Dict:
        """
        Compare multiple candidates from their analysis reports
        Returns a structured comparison
        """
        comparison = {
            "job_description": "",
            "candidates": [],
            "scoring": {
                "highest_match": {"name": "", "score": 0},
                "ordered_ranking": []
            },
            "skill_comparison": {},
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Process each report
        for path in report_paths:
            try:
                report = self.load_report(path)
                
                # Save job description (should be same for all if comparing for same job)
                if not comparison["job_description"]:
                    comparison["job_description"] = report.get("job_description", "")
                
                name = report.get("candidate_name", "Unknown")
                
                # Extract skills
                skills = report.get("parsed_resume", {}).get("skills", [])
                
                # Extract match score using regex
                analysis = report.get("analysis_result", "")
                import re
                score_match = re.search(r'(\d{1,3})(?:\s*)?\/(?:\s*)?100|(?:score|match)(?:\s*)?:(?:\s*)?(\d{1,3})', 
                                      analysis, re.IGNORECASE)
                
                score = 0
                if score_match:
                    matched_score = score_match.group(1) or score_match.group(2)
                    try:
                        score = int(matched_score)
                    except ValueError:
                        pass
                
                # Add to candidates list
                candidate_info = {
                    "name": name,
                    "match_score": score,
                    "skills": skills,
                    "report_path": path
                }
                comparison["candidates"].append(candidate_info)
                
                # Add skills to skill comparison
                for skill in skills:
                    if skill not in comparison["skill_comparison"]:
                        comparison["skill_comparison"][skill] = []
                    comparison["skill_comparison"][skill].append(name)
                
                # Update highest match if applicable
                if score > comparison["scoring"]["highest_match"]["score"]:
                    comparison["scoring"]["highest_match"] = {"name": name, "score": score}
            
            except Exception as e:
                print(f"Error processing report {path}: {str(e)}")
                continue
        
        # Create ordered ranking
        comparison["scoring"]["ordered_ranking"] = sorted(
            [(c["name"], c["match_score"]) for c in comparison["candidates"]],
            key=lambda x: x[1],
            reverse=True
        )
        
        return comparison
    
    def generate_comparison_report(self, job_keyword: str) -> Dict:
        """
        Generate a comparison report for candidates matching a job keyword
        """
        matching_reports = self.get_reports_for_job(job_keyword)
        if not matching_reports:
            return {"error": f"No reports found matching keyword: {job_keyword}"}
        
        return self.compare_candidates(matching_reports)

def save_results(result, parsed_resume, job_description, output_path=None, reports_dir="reports"):
    """Save analysis results to a JSON file (helper function)"""
    manager = AnalysisManager(reports_dir)
    return manager.save_report(result, parsed_resume, job_description, output_path) 