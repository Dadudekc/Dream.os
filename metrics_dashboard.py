#!/usr/bin/env python3
"""
Metrics Dashboard

A Flask-based web dashboard for visualizing code improvement metrics and
tracking changes over time based on the StatefulCursorManager data.
"""

import os
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from flask import Flask, render_template, jsonify, request, send_from_directory
import plotly
import plotly.graph_objs as go
import pandas as pd
from pandas import DataFrame

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules
try:
    from core.StatefulCursorManager import StatefulCursorManager
    from core.system_loader import initialize_system
except ImportError:
    logger.warning("Failed to import StatefulCursorManager. Running in standalone mode.")
    StatefulCursorManager = None
    initialize_system = None

# Constants - define at module level to prevent global usage issues
DASHBOARD_PORT = 5050
MEMORY_DIR = Path("memory")
STATE_FILE = MEMORY_DIR / "cursor_state.json"
STATIC_DIR = Path(__file__).parent / "metrics_dashboard_static"

# Create Flask app
app = Flask(__name__)


class MetricsDataProvider:
    """
    Provides metrics data from the StatefulCursorManager state file.
    Can operate in connected mode (using a live StatefulCursorManager instance)
    or standalone mode (reading directly from the state file).
    """
    
    def __init__(self, state_file_path: Optional[str] = None, cursor_manager=None):
        """
        Initialize the metrics data provider.
        
        Args:
            state_file_path: Path to the cursor state file
            cursor_manager: Optional StatefulCursorManager instance
        """
        self.state_file_path = Path(state_file_path or STATE_FILE)
        self.cursor_manager = cursor_manager
        self.state_data = {}
        self.last_load_time = 0
        
    def load_state_data(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load state data from the state file or cursor manager.
        
        Args:
            force_reload: Force reloading even if recently loaded
            
        Returns:
            Dict[str, Any]: The loaded state data
        """
        # Check if we need to reload (avoid frequent disk reads)
        current_time = datetime.datetime.now().timestamp()
        if not force_reload and current_time - self.last_load_time < 30:
            return self.state_data
            
        try:
            # Try to get state from cursor manager first
            if self.cursor_manager:
                with self.cursor_manager.state_lock:
                    self.state_data = self.cursor_manager.state.copy()
            # Fall back to reading the state file directly
            elif self.state_file_path.exists():
                with open(self.state_file_path, 'r', encoding='utf-8') as f:
                    self.state_data = json.load(f)
            else:
                logger.warning(f"State file not found: {self.state_file_path}")
                self.state_data = {}
                
            self.last_load_time = current_time
            return self.state_data
            
        except Exception as e:
            logger.error(f"Error loading state data: {e}")
            return {}
    
    def get_improvement_history(self) -> List[Dict[str, Any]]:
        """
        Get the improvement history from the state data.
        
        Returns:
            List[Dict[str, Any]]: List of improvement records
        """
        state_data = self.load_state_data()
        return state_data.get("improvement_history", [])
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """
        Get metrics history from the state data.
        
        Returns:
            List[Dict[str, Any]]: List of metrics history records
        """
        state_data = self.load_state_data()
        return state_data.get("metrics_history", [])
    
    def get_module_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get module statistics from the state data.
        
        Returns:
            Dict[str, Dict[str, Any]]: Module statistics
        """
        state_data = self.load_state_data()
        return state_data.get("module_stats", {})
    
    def get_active_improvements(self) -> Dict[str, Dict[str, Any]]:
        """
        Get active improvements from the state data.
        
        Returns:
            Dict[str, Dict[str, Any]]: Active improvements
        """
        state_data = self.load_state_data()
        return state_data.get("active_improvements", {})
    
    def get_module_improvement_history(self, module: str) -> List[Dict[str, Any]]:
        """
        Get improvement history for a specific module.
        
        Args:
            module: Module name
            
        Returns:
            List[Dict[str, Any]]: Module improvement history
        """
        history = self.get_improvement_history()
        return [record for record in history if record.get("module") == module]
    
    def get_metrics_time_series(self, module: str, metric_key: str) -> Tuple[List[str], List[float]]:
        """
        Get a time series of a specific metric for a module.
        
        Args:
            module: Module name
            metric_key: Metric key (e.g., 'complexity', 'coverage_percentage')
            
        Returns:
            Tuple[List[str], List[float]]: Lists of timestamps and values
        """
        metrics_history = self.get_metrics_history()
        timestamps = []
        values = []
        
        for record in metrics_history:
            metrics = record.get("metrics", {})
            if module in metrics and metric_key in metrics[module]:
                timestamps.append(record.get("timestamp", ""))
                values.append(metrics[module][metric_key])
                
        return timestamps, values
    
    def get_top_improvement_candidates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the top improvement candidates based on recent metrics.
        
        Args:
            limit: Maximum number of candidates to return
            
        Returns:
            List[Dict[str, Any]]: Top improvement candidates
        """
        # Try to use cursor manager if available
        if self.cursor_manager:
            try:
                return self.cursor_manager.get_improvement_candidates(limit)
            except Exception as e:
                logger.error(f"Error getting improvement candidates: {e}")
        
        # Calculate candidates manually from state
        candidates = []
        metrics_history = self.get_metrics_history()
        module_stats = self.get_module_stats()
        active_improvements = self.get_active_improvements()
        
        if not metrics_history:
            return []
            
        # Get most recent metrics
        latest_metrics = metrics_history[-1].get("metrics", {})
        
        # Build candidates list
        for module, metrics in latest_metrics.items():
            # Skip modules currently being improved
            if module in active_improvements:
                continue
                
            # Get module stats if available
            stats = module_stats.get(module, {})
            
            # Extract key metrics
            complexity = metrics.get("complexity", 0)
            coverage = metrics.get("coverage_percentage", 0)
            maintainability = metrics.get("maintainability_index", 0)
            
            # Get last improvement time
            last_improved = stats.get("last_improved")
            days_since_improvement = 1000  # Default if never improved
            
            if last_improved:
                try:
                    last_date = datetime.datetime.fromisoformat(last_improved)
                    days_since_improvement = (datetime.datetime.now() - last_date).days
                except ValueError:
                    pass
            
            # Calculate score (simplified version)
            score = (
                complexity * 2 +
                max(0, (100 - coverage)) * 1.5 +
                max(0, (100 - maintainability)) +
                min(days_since_improvement * 0.5, 50)
            )
            
            candidates.append({
                "module": module,
                "score": score,
                "complexity": complexity,
                "coverage": coverage,
                "maintainability": maintainability,
                "days_since_improvement": days_since_improvement
            })
        
        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        return candidates[:limit]


# Initialize dashboard components
def setup_dashboard():
    """Set up the dashboard components."""
    global data_provider
    
    # Create necessary directories
    MEMORY_DIR.mkdir(exist_ok=True)
    STATIC_DIR.mkdir(exist_ok=True)
    
    # Create sample static files if they don't exist
    css_file = STATIC_DIR / "dashboard.css"
    if not css_file.exists():
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write("""
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background-color: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); padding: 20px; margin-bottom: 20px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .chart-container { height: 300px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
            tr:hover { background-color: #f5f5f5; }
            .progress-bar { height: 10px; background-color: #e0e0e0; border-radius: 5px; overflow: hidden; }
            .progress-value { height: 100%; background-color: #4CAF50; }
            """)
    
    # Try to connect to cursor manager
    cursor_manager = None
    if StatefulCursorManager and initialize_system:
        try:
            system = initialize_system("config/system_config.yml")
            cursor_manager = system.get_service("stateful_cursor_manager")
            logger.info("Connected to StatefulCursorManager")
        except Exception as e:
            logger.warning(f"Failed to connect to StatefulCursorManager: {e}")
    
    # Initialize data provider
    data_provider = MetricsDataProvider(STATE_FILE, cursor_manager)
    logger.info("Dashboard setup complete")


# Initialize data provider
data_provider = None
setup_dashboard()


# Flask routes
@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files."""
    return send_from_directory(STATIC_DIR, path)


@app.route('/api/dashboard-summary')
def dashboard_summary():
    """Get summary metrics for the dashboard."""
    state_data = data_provider.load_state_data(force_reload=True)
    
    # Extract key metrics
    improvement_count = len(state_data.get("improvement_history", []))
    metrics_snapshots = len(state_data.get("metrics_history", []))
    module_count = len(state_data.get("module_stats", {}))
    active_count = len(state_data.get("active_improvements", {}))
    
    # Get session info
    last_session_time = state_data.get("last_session_time", "")
    session_count = state_data.get("session_count", 0)
    
    # Format last session time
    last_session = "Never"
    if last_session_time:
        try:
            dt = datetime.datetime.fromisoformat(last_session_time)
            last_session = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            last_session = last_session_time
    
    return jsonify({
        "improvement_count": improvement_count,
        "metrics_snapshots": metrics_snapshots,
        "module_count": module_count,
        "active_improvements": active_count,
        "last_session": last_session,
        "session_count": session_count
    })


@app.route('/api/improvement-history')
def improvement_history():
    """Get improvement history data."""
    history = data_provider.get_improvement_history()
    
    # Process history to extract key metrics
    processed_history = []
    for record in history:
        timestamp = record.get("timestamp", "")
        module = record.get("module", "")
        changes = record.get("changes", {}).get("summary", "")
        metrics_before = record.get("metrics_before", {})
        metrics_after = record.get("metrics_after", {})
        metrics_delta = record.get("metrics_delta", {})
        
        # Format timestamp
        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted_time = timestamp
        
        processed_history.append({
            "timestamp": formatted_time,
            "module": module,
            "changes": changes,
            "metrics_delta": metrics_delta,
            "complexity_before": metrics_before.get("complexity", "N/A"),
            "complexity_after": metrics_after.get("complexity", "N/A"),
            "coverage_before": metrics_before.get("coverage_percentage", "N/A"),
            "coverage_after": metrics_after.get("coverage_percentage", "N/A"),
            "maintainability_before": metrics_before.get("maintainability_index", "N/A"),
            "maintainability_after": metrics_after.get("maintainability_index", "N/A"),
        })
    
    return jsonify(processed_history)


@app.route('/api/module-list')
def module_list():
    """Get list of modules with stats."""
    module_stats = data_provider.get_module_stats()
    metrics_history = data_provider.get_metrics_history()
    
    # Get latest metrics
    latest_metrics = {}
    if metrics_history:
        latest_metrics = metrics_history[-1].get("metrics", {})
    
    # Combine stats and metrics
    modules = []
    for module, stats in module_stats.items():
        metrics = latest_metrics.get(module, {})
        
        # Format last improved date
        last_improved = stats.get("last_improved", "")
        if last_improved:
            try:
                dt = datetime.datetime.fromisoformat(last_improved)
                last_improved = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        modules.append({
            "module": module,
            "improvement_count": stats.get("improvement_count", 0),
            "last_improved": last_improved,
            "complexity": metrics.get("complexity", "N/A"),
            "coverage": metrics.get("coverage_percentage", "N/A"),
            "maintainability": metrics.get("maintainability_index", "N/A"),
        })
    
    # Sort by module name
    modules.sort(key=lambda x: x["module"])
    
    return jsonify(modules)


@app.route('/api/improvement-candidates')
def improvement_candidates():
    """Get improvement candidates."""
    candidates = data_provider.get_top_improvement_candidates(limit=10)
    return jsonify(candidates)


@app.route('/api/module-metrics/<path:module>')
def module_metrics(module):
    """Get detailed metrics for a specific module."""
    # Get module improvement history
    history = data_provider.get_module_improvement_history(module)
    
    # Get metrics time series
    complexity_timestamps, complexity_values = data_provider.get_metrics_time_series(module, "complexity")
    coverage_timestamps, coverage_values = data_provider.get_metrics_time_series(module, "coverage_percentage")
    maintainability_timestamps, maintainability_values = data_provider.get_metrics_time_series(
        module, "maintainability_index")
    
    # Create charts
    complexity_chart = create_time_series_chart(complexity_timestamps, complexity_values, "Complexity")
    coverage_chart = create_time_series_chart(coverage_timestamps, coverage_values, "Coverage (%)")
    maintainability_chart = create_time_series_chart(
        maintainability_timestamps, maintainability_values, "Maintainability Index")
    
    # Get module stats
    module_stats = data_provider.get_module_stats().get(module, {})
    
    return jsonify({
        "module": module,
        "improvement_count": module_stats.get("improvement_count", 0),
        "complexity_delta": module_stats.get("complexity_delta", 0),
        "coverage_delta": module_stats.get("coverage_delta", 0),
        "history": history,
        "complexity_chart": complexity_chart,
        "coverage_chart": coverage_chart,
        "maintainability_chart": maintainability_chart
    })


def create_time_series_chart(timestamps, values, title):
    """Create a time series chart using Plotly."""
    if not timestamps or not values:
        return None
        
    # Create a dataframe
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    # Convert timestamps to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Create the plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['value'],
        mode='lines+markers',
        name=title
    ))
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title='Time',
        yaxis_title='Value',
        hovermode='closest'
    )
    
    # Convert to JSON
    return json.loads(plotly.io.to_json(fig))


@app.route('/templates/dashboard.html')
def dashboard_template():
    """Return the dashboard template."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Code Metrics Dashboard</title>
        <link rel="stylesheet" href="/static/dashboard.css">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Code Metrics Dashboard</h1>
                <div>
                    <button id="refreshButton">Refresh Data</button>
                </div>
            </div>
            
            <div class="card">
                <h2>Summary</h2>
                <div class="metrics-grid">
                    <div class="metric-box">
                        <h3>Improvements</h3>
                        <p id="improvementCount">Loading...</p>
                    </div>
                    <div class="metric-box">
                        <h3>Modules</h3>
                        <p id="moduleCount">Loading...</p>
                    </div>
                    <div class="metric-box">
                        <h3>Metrics Snapshots</h3>
                        <p id="metricsSnapshots">Loading...</p>
                    </div>
                    <div class="metric-box">
                        <h3>Last Session</h3>
                        <p id="lastSession">Loading...</p>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>Top Improvement Candidates</h2>
                <table id="candidatesTable">
                    <thead>
                        <tr>
                            <th>Module</th>
                            <th>Score</th>
                            <th>Complexity</th>
                            <th>Coverage</th>
                            <th>Last Improved</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td colspan="5">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2>Recent Improvements</h2>
                <table id="improvementsTable">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Module</th>
                            <th>Changes</th>
                            <th>Complexity</th>
                            <th>Coverage</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td colspan="5">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2>Module Overview</h2>
                <table id="modulesTable">
                    <thead>
                        <tr>
                            <th>Module</th>
                            <th>Improvements</th>
                            <th>Complexity</th>
                            <th>Coverage</th>
                            <th>Maintainability</th>
                            <th>Last Improved</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td colspan="6">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div id="moduleDetails" class="card" style="display: none;">
                <h2 id="moduleDetailsTitle">Module Details</h2>
                <div class="metrics-grid">
                    <div class="chart-container" id="complexityChart"></div>
                    <div class="chart-container" id="coverageChart"></div>
                    <div class="chart-container" id="maintainabilityChart"></div>
                </div>
                <h3>Improvement History</h3>
                <table id="moduleHistoryTable">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Changes</th>
                            <th>Metrics Delta</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        
        <script>
            // Load dashboard data
            function loadDashboardData() {
                // Load summary data
                axios.get('/api/dashboard-summary')
                    .then(response => {
                        const data = response.data;
                        document.getElementById('improvementCount').textContent = data.improvement_count;
                        document.getElementById('moduleCount').textContent = data.module_count;
                        document.getElementById('metricsSnapshots').textContent = data.metrics_snapshots;
                        document.getElementById('lastSession').textContent = data.last_session;
                    })
                    .catch(error => console.error('Error loading summary:', error));
                
                // Load improvement candidates
                axios.get('/api/improvement-candidates')
                    .then(response => {
                        const candidates = response.data;
                        const tbody = document.querySelector('#candidatesTable tbody');
                        tbody.innerHTML = '';
                        
                        candidates.forEach(candidate => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${candidate.module}</td>
                                <td>${candidate.score.toFixed(2)}</td>
                                <td>${candidate.complexity}</td>
                                <td>${candidate.coverage}%</td>
                                <td>${candidate.days_since_improvement} days ago</td>
                            `;
                            tbody.appendChild(row);
                        });
                    })
                    .catch(error => console.error('Error loading candidates:', error));
                
                // Load recent improvements
                axios.get('/api/improvement-history')
                    .then(response => {
                        const history = response.data;
                        const tbody = document.querySelector('#improvementsTable tbody');
                        tbody.innerHTML = '';
                        
                        // Get the 10 most recent improvements
                        const recentHistory = history.slice(-10).reverse();
                        
                        recentHistory.forEach(record => {
                            const complexityDelta = record.metrics_delta.complexity || 0;
                            const coverageDelta = record.metrics_delta.coverage_percentage || 0;
                            
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${record.timestamp}</td>
                                <td>${record.module}</td>
                                <td>${record.changes}</td>
                                <td>${complexityDelta >= 0 ? '+' : ''}${complexityDelta}</td>
                                <td>${coverageDelta >= 0 ? '+' : ''}${coverageDelta}%</td>
                            `;
                            tbody.appendChild(row);
                        });
                    })
                    .catch(error => console.error('Error loading improvements:', error));
                
                // Load module list
                axios.get('/api/module-list')
                    .then(response => {
                        const modules = response.data;
                        const tbody = document.querySelector('#modulesTable tbody');
                        tbody.innerHTML = '';
                        
                        modules.forEach(module => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td><a href="#" class="module-link" data-module="${module.module}">${module.module}</a></td>
                                <td>${module.improvement_count}</td>
                                <td>${module.complexity}</td>
                                <td>${module.coverage}%</td>
                                <td>${module.maintainability}</td>
                                <td>${module.last_improved}</td>
                            `;
                            tbody.appendChild(row);
                        });
                        
                        // Add click handlers for module links
                        document.querySelectorAll('.module-link').forEach(link => {
                            link.addEventListener('click', event => {
                                event.preventDefault();
                                const module = event.target.getAttribute('data-module');
                                loadModuleDetails(module);
                            });
                        });
                    })
                    .catch(error => console.error('Error loading modules:', error));
            }
            
            // Load module details
            function loadModuleDetails(module) {
                // Show the module details section
                document.getElementById('moduleDetails').style.display = 'block';
                document.getElementById('moduleDetailsTitle').textContent = `Module Details: ${module}`;
                
                // Load module metrics
                axios.get(`/api/module-metrics/${encodeURIComponent(module)}`)
                    .then(response => {
                        const data = response.data;
                        
                        // Render charts if available
                        if (data.complexity_chart) {
                            Plotly.newPlot('complexityChart', data.complexity_chart.data, data.complexity_chart.layout);
                        }
                        
                        if (data.coverage_chart) {
                            Plotly.newPlot('coverageChart', data.coverage_chart.data, data.coverage_chart.layout);
                        }
                        
                        if (data.maintainability_chart) {
                            Plotly.newPlot('maintainabilityChart', data.maintainability_chart.data, data.maintainability_chart.layout);
                        }
                        
                        // Render history table
                        const tbody = document.querySelector('#moduleHistoryTable tbody');
                        tbody.innerHTML = '';
                        
                        data.history.forEach(record => {
                            const row = document.createElement('tr');
                            
                            // Format metrics delta
                            const deltaItems = [];
                            for (const [key, value] of Object.entries(record.metrics_delta || {})) {
                                if (value !== 0) {
                                    deltaItems.push(`${key}: ${value >= 0 ? '+' : ''}${value}`);
                                }
                            }
                            
                            const timestamp = record.timestamp;
                            row.innerHTML = `
                                <td>${timestamp}</td>
                                <td>${record.changes?.summary || ''}</td>
                                <td>${deltaItems.join(', ')}</td>
                            `;
                            tbody.appendChild(row);
                        });
                    })
                    .catch(error => console.error('Error loading module details:', error));
            }
            
            // Add event listener for refresh button
            document.getElementById('refreshButton').addEventListener('click', loadDashboardData);
            
            // Load data on page load
            document.addEventListener('DOMContentLoaded', loadDashboardData);
        </script>
    </body>
    </html>
    """


def main():
    """Main entry point for the dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run the metrics dashboard')
    parser.add_argument('--port', type=int, default=DASHBOARD_PORT,
                        help=f'Port to run the dashboard on (default: {DASHBOARD_PORT})')
    parser.add_argument('--state-file', type=str, default=str(STATE_FILE),
                        help=f'Path to the state file (default: {STATE_FILE})')
    
    args = parser.parse_args()
    
    global data_provider, STATE_FILE
    STATE_FILE = Path(args.state_file)
    data_provider = MetricsDataProvider(STATE_FILE)
    
    print(f"Starting dashboard on http://localhost:{args.port}")
    app.run(host='0.0.0.0', port=args.port, debug=True)


if __name__ == "__main__":
    main() 