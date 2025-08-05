from flask import Flask, render_template, request, jsonify, send_file
import os
import logging
from src.resume_tailor import ResumeTailor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

resume_tailor = None
logger.info("🔧 Initializing ResumeTailor...")
try:
    resume_tailor = ResumeTailor()
    logger.info("✅ ResumeTailor initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize ResumeTailor: {e}")
    import traceback
    logger.error(traceback.format_exc())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tailor', methods=['POST'])
def tailor_resume():
    logger.info("🎯 /tailor endpoint called")
    try:
        data = request.get_json()
        logger.info(f"📥 Received data keys: {list(data.keys()) if data else 'None'}")
        
        # Extract data from request
        job_description = data.get('job_description', '')
        projects_data = data.get('projects', [])
        latex_resume = data.get('latex_resume', '')
        
        logger.info(f"📋 Job description length: {len(job_description)}")
        logger.info(f"📋 Projects count: {len(projects_data)}")
        logger.info(f"📋 LaTeX resume length: {len(latex_resume)}")
        
        if not job_description or not latex_resume:
            logger.error("❌ Missing required data")
            return jsonify({'error': 'Job description and LaTeX resume are required'}), 400
        
        if resume_tailor is None:
            logger.error("❌ ResumeTailor not initialized")
            return jsonify({'error': 'ResumeTailor not initialized'}), 500
        
        # Use the new modular approach
        logger.info("🔧 Calling resume_tailor.tailor_resume...")
        result = resume_tailor.tailor_resume(job_description, latex_resume, projects_data)
        logger.info(f"📊 Result keys: {list(result.keys()) if result else 'None'}")
        logger.info(f"📊 PDF result: {result.get('pdf_result')}")
        
        if result['pdf_result']:
            return jsonify({
                'success': True,
                'keywords': result['keywords'],
                'modified_resume': result['modified_resume'],
                'pdf_path': result['pdf_result']['filename'],
                'is_single_page': result['pdf_result']['is_single_page'],
                'page_count': result['pdf_result']['page_count']
            })
        else:
            return jsonify({'error': 'Failed to compile LaTeX resume'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error in /tailor endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(f'temp/{filename}', as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    # Create temp directory if it doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run in production mode if not in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug) 