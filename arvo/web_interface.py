"""
User-friendly web interface for Arvo deployment system.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import time
from pathlib import Path
from arvo.simple_deploy import deploy

app = Flask(__name__)

# Store deployment history
deployments = {}

@app.route('/')
def index():
    """Main deployment interface."""
    return render_template('index.html')

@app.route('/deploy', methods=['POST'])
def deploy_app():
    """Handle deployment request."""
    try:
        data = request.get_json()
        instructions = data.get('instructions', '')
        repo_url = data.get('repo_url', '')
        region = data.get('region', 'us-west-2')
        
        if not instructions or not repo_url:
            return jsonify({
                'status': 'error',
                'message': 'Instructions and repository URL are required'
            }), 400
        
        # Generate deployment ID
        deployment_id = f"d-{int(time.time())}-{hash(repo_url) % 10000:04x}"
        
        # Store deployment info
        deployments[deployment_id] = {
            'id': deployment_id,
            'instructions': instructions,
            'repo_url': repo_url,
            'region': region,
            'status': 'starting',
            'start_time': time.time(),
            'logs': []
        }
        
        # Start deployment in background
        import threading
        thread = threading.Thread(target=run_deployment, args=(deployment_id, instructions, repo_url, region))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'deployment_id': deployment_id,
            'message': 'Deployment started successfully'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def run_deployment(deployment_id, instructions, repo_url, region):
    """Run deployment in background thread."""
    try:
        deployments[deployment_id]['status'] = 'running'
        deployments[deployment_id]['logs'].append(f"Starting deployment: {instructions}")
        
        # Run the actual deployment
        result = deploy(instructions, repo_url, region)
        
        # Update deployment status
        deployments[deployment_id]['status'] = result['status']
        deployments[deployment_id]['end_time'] = time.time()
        deployments[deployment_id]['result'] = result
        
        if result['status'] == 'success':
            deployments[deployment_id]['logs'].append(f"✅ Deployment successful!")
            deployments[deployment_id]['logs'].append(f"🌐 Application URL: {result['application_url']}")
        else:
            deployments[deployment_id]['logs'].append(f"❌ Deployment failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        deployments[deployment_id]['status'] = 'failed'
        deployments[deployment_id]['logs'].append(f"❌ Deployment error: {str(e)}")

@app.route('/status/<deployment_id>')
def get_status(deployment_id):
    """Get deployment status."""
    if deployment_id not in deployments:
        return jsonify({'status': 'error', 'message': 'Deployment not found'}), 404
    
    deployment = deployments[deployment_id]
    return jsonify({
        'id': deployment_id,
        'status': deployment['status'],
        'instructions': deployment['instructions'],
        'repo_url': deployment['repo_url'],
        'region': deployment['region'],
        'logs': deployment['logs'],
        'start_time': deployment['start_time'],
        'end_time': deployment.get('end_time'),
        'result': deployment.get('result')
    })

@app.route('/deployments')
def list_deployments():
    """List all deployments."""
    return jsonify({
        'deployments': [
            {
                'id': dep_id,
                'instructions': dep['instructions'],
                'repo_url': dep['repo_url'],
                'status': dep['status'],
                'start_time': dep['start_time']
            }
            for dep_id, dep in deployments.items()
        ]
    })

@app.route('/logs/<deployment_id>')
def get_logs(deployment_id):
    """Get deployment logs."""
    if deployment_id not in deployments:
        return jsonify({'status': 'error', 'message': 'Deployment not found'}), 404
    
    return jsonify({
        'deployment_id': deployment_id,
        'logs': deployments[deployment_id]['logs']
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Create static directory if it doesn't exist
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
