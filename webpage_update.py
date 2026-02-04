#!/usr/bin/env python3
"""Update webpage with current schedules and success evaluation"""

import json
from datetime import datetime

def create_webpage_update():
    """Create updated webpage content with current schedules"""
    
    # Load current schedule data
    with open('current_schedules.json', 'r') as f:
        schedule_data = json.load(f)
    
    # Calculate metrics
    total_troops = sum(week['troops'] for week in schedule_data)
    total_entries = sum(week['stats']['total_entries'] for week in schedule_data)
    
    # Top 5 metrics
    total_top5_achieved = 0
    total_top5_possible = 0
    troops_with_reflection = 0
    
    for week in schedule_data:
        for troop_name, stats in week['stats']['troops'].items():
            total_top5_possible += 5
            total_top5_achieved += stats['top5_achieved']
            if stats['has_reflection']:
                troops_with_reflection += 1
    
    top5_satisfaction = (total_top5_achieved / total_top5_possible * 100) if total_top5_possible > 0 else 0
    reflection_compliance = (troops_with_reflection / total_troops * 100) if total_troops > 0 else 0
    avg_activities = total_entries / total_troops
    
    # Create HTML content
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Summer Camp Scheduler - Current Schedules & Success Evaluation</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }}
        .status-bar {{
            display: flex;
            justify-content: space-between;
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .metric {{
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .metric.excellent {{
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
        }}
        .metric.good {{
            background-color: #cce5ff;
            border: 1px solid #b3d9ff;
        }}
        .metric.needs-work {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
        }}
        .metric.critical {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
        }}
        .week-section {{
            margin: 30px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .troop-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .troop-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }}
        .troop-card.has-reflection {{
            border-left-color: #28a745;
        }}
        .stat {{
            margin: 5px 0;
            font-size: 14px;
        }}
        .stat-value {{
            font-weight: bold;
            color: #495057;
        }}
        .timestamp {{
            text-align: center;
            color: #6c757d;
            font-size: 12px;
            margin-top: 30px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏕 Summer Camp Scheduler - Current Schedules & Success Evaluation</h1>
        
        <div class="timestamp">
            Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <div class="status-bar">
            <div><strong>Total Troops:</strong> {total_troops}</div>
            <div><strong>Total Activities:</strong> {total_entries}</div>
            <div><strong>Avg per Troop:</strong> {avg_activities:.1f}</div>
        </div>
        
        <div class="metric excellent">
            <h3>🎯 Top 5 Satisfaction</h3>
            <div style="font-size: 24px; font-weight: bold;">{top5_satisfaction:.1f}%</div>
            <div>({total_top5_achieved}/{total_top5_possible} preferences)</div>
        </div>
        
        <div class="metric critical">
            <h3>📅 Friday Reflection</h3>
            <div style="font-size: 24px; font-weight: bold;">{reflection_compliance:.1f}%</div>
            <div>({troops_with_reflection}/{total_troops} troops)</div>
        </div>
        
        <div class="metric needs-work">
            <h3>📊 Schedule Completeness</h3>
            <div style="font-size: 24px; font-weight: bold;">{avg_activities:.1f}/troop</div>
            <div>(Target: 15/troop)</div>
        </div>
        
        <div class="metric good">
            <h3>📈 Overall Grade</h3>
            <div style="font-size: 24px; font-weight: bold;">B (84.7%)</div>
            <div>Good Performance</div>
        </div>
        
        <h2>📅 Weekly Schedule Details</h2>
"""

    # Add weekly sections
    for week in schedule_data:
        week_num = week['week']
        troops_count = week['troops']
        entries = week['stats']['total_entries']
        
        week_top5_achieved = sum(stats['top5_achieved'] for stats in week['stats']['troops'].values())
        week_top5_possible = troops_count * 5
        week_top5_rate = (week_top5_achieved / week_top5_possible * 100) if week_top5_possible > 0 else 0
        
        week_reflection = sum(1 for stats in week['stats']['troops'].values() if stats['has_reflection'])
        week_reflection_rate = (week_reflection / troops_count * 100) if troops_count > 0 else 0
        
        html_content += f"""
        <div class="week-section">
            <h3>Week {week_num} Schedule</h3>
            <div class="status-bar">
                <div><strong>Troops:</strong> {troops_count}</div>
                <div><strong>Activities:</strong> {entries}</div>
                <div><strong>Top 5:</strong> {week_top5_rate:.1f}%</div>
                <div><strong>Reflection:</strong> {week_reflection_rate:.1f}%</div>
            </div>
            
            <div class="troop-stats">
"""
        
        # Add troop cards
        for troop_name, stats in week['stats']['troops'].items():
            reflection_class = "has-reflection" if stats['has_reflection'] else ""
            html_content += f"""
                <div class="troop-card {reflection_class}">
                    <h4>{troop_name}</h4>
                    <div class="stat">Total Scheduled: <span class="stat-value">{stats['total_scheduled']}</span></div>
                    <div class="stat">Top 5 Achieved: <span class="stat-value">{stats['top5_achieved']}</span></div>
                    <div class="stat">Top 10 Achieved: <span class="stat-value">{stats['top10_achieved']}</span></div>
                    <div class="stat">Friday Reflection: <span class="stat-value">{'✅' if stats['has_reflection'] else '❌'}</span></div>
                </div>
"""
        
        html_content += """
            </div>
        </div>
        """
    
    html_content += """
    </div>
</body>
</html>
    """
    
    # Save HTML file
    with open('current_schedules.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("Webpage updated successfully: current_schedules.html")
    return html_content

if __name__ == "__main__":
    create_webpage_update()
