"""
LaTeX Processor Module

Handles parsing, modification, and compilation of LaTeX resume content.
"""

import re
import os
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional
from .api_providers import APIManager


class LaTeXProcessor:
    """Handles LaTeX content processing and compilation"""
    
    def __init__(self, api_manager: APIManager):
        self.api_manager = api_manager
    
    def parse_latex_sections(self, latex_resume: str) -> Dict[str, any]:
        """Parse LaTeX resume into sections using marker comments"""
        sections = {}
        
        # Define marker patterns for main sections
        main_marker_patterns = {
            'skills': (r'%----START OF TECHNICAL SKILLS MARKER----(.*?)%----END OF TECHNICAL SKILLS MARKER----', re.DOTALL)
        }
        
        # Parse main sections
        for section_name, (pattern, flags) in main_marker_patterns.items():
            match = re.search(pattern, latex_resume, flags)
            if match:
                sections[section_name] = match.group(1).strip()
            else:
                print(f"Warning: {section_name} marker not found in resume")
        
        # Parse individual experience markers
        experience_matches = re.findall(r'%----START OF EXPERIENCE MARKER----(.*?)%----END OF EXPERIENCE MARKER----', latex_resume, re.DOTALL)
        if experience_matches:
            sections['experiences'] = experience_matches
        else:
            print("Warning: No experience markers found in resume")
        
        # Parse general projects marker
        project_match = re.search(r'%----START OF PROJECTS MARKER----(.*?)%----END OF PROJECTS MARKER----', latex_resume, re.DOTALL)
        if project_match:
            sections['projects'] = project_match.group(1).strip()
        else:
            print("Warning: No projects marker found in resume")
        
        return sections
    
    def replace_sections_in_resume(self, latex_resume: str, sections: Dict[str, any]) -> str:
        """Replace modified sections back into the original LaTeX resume"""
        modified_resume = latex_resume
        
        # Replace skills section
        if 'skills' in sections:
            # Use string replacement instead of regex to avoid escaping issues
            start_marker = '%----START OF TECHNICAL SKILLS MARKER----'
            end_marker = '%----END OF TECHNICAL SKILLS MARKER----'
            
            start_pos = modified_resume.find(start_marker)
            end_pos = modified_resume.find(end_marker)
            
            if start_pos != -1 and end_pos != -1 and end_pos > start_pos:
                # Replace the content between markers
                modified_resume = (
                    modified_resume[:start_pos + len(start_marker)] + '\n' + sections['skills'] + '\n' +
                    modified_resume[end_pos:]
                )
        
        # Replace experience sections
        if 'experiences' in sections:
            # Find all experience markers and replace them one by one
            experience_pattern = r'%----START OF EXPERIENCE MARKER----.*?%----END OF EXPERIENCE MARKER----'
            experience_matches = list(re.finditer(experience_pattern, modified_resume, re.DOTALL))
            
            # Replace from last to first to avoid index shifting issues
            for i in range(len(experience_matches) - 1, -1, -1):
                if i < len(sections['experiences']):
                    match = experience_matches[i]
                    start, end = match.span()
                    modified_resume = (
                        modified_resume[:start] + '\n' +
                        r'%----START OF EXPERIENCE MARKER----' + '\n' + sections['experiences'][i] + r'%----END OF EXPERIENCE MARKER----' + '\n' +
                        modified_resume[end:]
                    )
        
        # Replace projects section
        if 'projects' in sections:
            # Use string replacement instead of regex to avoid escaping issues
            start_marker = '%----START OF PROJECTS MARKER----'
            end_marker = '%----END OF PROJECTS MARKER----'
            
            start_pos = modified_resume.find(start_marker)
            end_pos = modified_resume.find(end_marker)
            
            if start_pos != -1 and end_pos != -1 and end_pos > start_pos:
                # Replace the content between markers
                modified_resume = (
                    modified_resume[:start_pos + len(start_marker)] + '\n' +
                    sections['projects'] + '\n' +
                    modified_resume[end_pos:]
                )
        
        return modified_resume
    
    def compile_latex(self, latex_content: str) -> Optional[Dict]:
        """
        Compile LaTeX to PDF and validate it's 1 page
        """
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write LaTeX content to file
                tex_file = os.path.join(temp_dir, 'resume.tex')
                with open(tex_file, 'w', encoding='utf-8') as f:
                    f.write(latex_content)
                                
                # Try to compile with different approaches
                compilation_success = False
                
                # First attempt: Standard compilation
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', '-output-directory', temp_dir, tex_file],
                    capture_output=True,
                    text=True,
                    cwd=temp_dir
                )
                
                if result.returncode == 0:
                    compilation_success = True
                else:
                    print(f"First compilation attempt failed: {result.stderr}")
                    
                    # Second attempt: Try with lualatex (better font support)
                    result = subprocess.run(
                        ['lualatex', '-interaction=nonstopmode', '-output-directory', temp_dir, tex_file],
                        capture_output=True,
                        text=True,
                        cwd=temp_dir
                    )
                    
                    if result.returncode == 0:
                        compilation_success = True
                    else:
                        print(f"Second compilation attempt failed: {result.stderr}")
                        
                        # Third attempt: Remove problematic packages and try again
                        simplified_content = self._simplify_latex_content(latex_content)
                        with open(tex_file, 'w', encoding='utf-8') as f:
                            f.write(simplified_content)
                        
                        result = subprocess.run(
                            ['pdflatex', '-interaction=nonstopmode', '-output-directory', temp_dir, tex_file],
                            capture_output=True,
                            text=True,
                            cwd=temp_dir
                        )
                        
                        if result.returncode == 0:
                            compilation_success = True
                        else:
                            print(f"Third compilation attempt failed: {result.stderr}")
                
                if not compilation_success:
                    print("All compilation attempts failed")
                    return None
                
                # Check if PDF was created
                pdf_file = os.path.join(temp_dir, 'resume.pdf')
                if not os.path.exists(pdf_file):
                    return None
                
                # Validate PDF page count and return result with status
                page_count = self._get_pdf_page_count(pdf_file)
                is_single_page = page_count == 1
                
                # Copy PDF to temp directory for download
                output_pdf = os.path.join('temp', 'tailored_resume.pdf')
                shutil.copy2(pdf_file, output_pdf)
                
                return {
                    'filename': 'tailored_resume.pdf',
                    'is_single_page': is_single_page,
                    'page_count': page_count
                }
                    
        except Exception as e:
            print(f"Error compiling LaTeX: {e}")
            return None
    
    def _simplify_latex_content(self, latex_content: str) -> str:
        """Simplify LaTeX content by removing problematic packages and commands"""
        # Remove problematic packages
        problematic_packages = [
            r'\\usepackage\{CormorantGaramond\}',
            r'\\usepackage\{charter\}',
            r'\\usepackage\{FiraSans\}',
            r'\\usepackage\{roboto\}',
            r'\\usepackage\{noto-sans\}',
            r'\\usepackage\{sourcesanspro\}',
            r'\\usepackage\{helvet\}',
            r'\\renewcommand\{\\rmdefault\}\{phv\}',
            r'\\input\{glyphtounicode\}'
        ]
        
        for package in problematic_packages:
            latex_content = re.sub(package, '', latex_content)
        
        # Replace custom commands with standard LaTeX
        command_replacements = {
            r'\\resumeItem\{([^}]*)\}': r'\\item \1',
            r'\\resumeSubheading\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}': r'\\textbf{\1} \hfill \2 \\\\ \textit{\3} \hfill \textit{\4}',
            r'\\resumeSubSubheading\{([^}]*)\}\{([^}]*)\}': r'\\textit{\1} \hfill \textit{\2}',
            r'\\resumeProjectHeading\{([^}]*)\}\{([^}]*)\}': r'\\textbf{\1} \hfill \textit{\2}',
            r'\\resumeSubItem\{([^}]*)\}': r'\\item \1',
            r'\\resumeSubHeadingListStart': r'\\begin{itemize}',
            r'\\resumeSubHeadingListEnd': r'\\end{itemize}',
            r'\\resumeItemListStart': r'\\begin{itemize}',
            r'\\resumeItemListEnd': r'\\end{itemize}'
        }
        
        for old_cmd, new_cmd in command_replacements.items():
            latex_content = re.sub(old_cmd, new_cmd, latex_content)
        
        return latex_content
    
    def _get_pdf_page_count(self, pdf_path: str) -> int:
        """Get the number of pages in a PDF"""
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            print(f"Error getting PDF page count: {e}")
            return 0
    
    def _validate_pdf_pages(self, pdf_path: str) -> bool:
        """Check if PDF has exactly 1 page"""
        return self._get_pdf_page_count(pdf_path) == 1 