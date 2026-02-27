import requests
import json
import os
import io
import zipfile
import time
import math

TOKEN = os.getenv('ACCESS_TOKEN')
USERNAME = "Azekhiel"
SKIP_REPOS = ['Azekhiel/VN'] 
BLACKLIST_FOLDERS = ['venv', 'env', '.env', 'node_modules', '.git', '__pycache__', 'vendor', 'dist', 'build']

EXT_MAP = {
    '.go': 'Go',
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.c': 'C',
    '.cpp': 'C++',
    '.rpy': "Ren'Py",
    '.java': 'Java',
    '.vhd': 'VHDL',
    '.sol': 'Solidity',
    '.sh': 'Shell'
}

LANG_COLORS = {
    "Python": "#3572A5", "Go": "#00ADD8", "C": "#555555", "C++": "#f34b7d",
    "JavaScript": "#f1e05a", "Ren'Py": "#ff7f7f", "Java": "#b07219",
    "VHDL": "#adb2cb", "TypeScript": "#2b7489", "Solidity": "#AA6746",
    "Shell": "#89e051"
}

def get_stats():
    headers = {'Authorization': f'token {TOKEN}'}
    stats = {}
    total_loc = 0
    
    print("Starting GitHub Scan")
    repos_res = requests.get(f"https://api.github.com/user/repos?per_page=100", headers=headers)
    if repos_res.status_code != 200:
        print("Error fetching repos. Check token.")
        return None

    for repo in repos_res.json():
        repo_name = repo['full_name']
        if repo.get('fork') or repo_name in SKIP_REPOS:
            continue

        print(f"Analyzing: {repo_name}")
        zip_url = f"https://api.github.com/repos/{repo_name}/zipball"
        time.sleep(1)
        
        zip_res = requests.get(zip_url, headers=headers)
        if zip_res.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(zip_res.content)) as z:
                for file_info in z.infolist():
                    if any(folder in file_info.filename for folder in BLACKLIST_FOLDERS) or file_info.is_dir():
                        continue
                    
                    ext = os.path.splitext(file_info.filename)[1].lower()
                    
                    if ext == '.h' or ext in EXT_MAP:
                        try:
                            with z.open(file_info) as f:
                                content = f.read().decode('utf-8', errors='ignore')
                                
                                if ext == '.h':
                                    cpp_indicators = ['class ', 'template<', 'public:', 'private:', 'namespace ', 'iostream']
                                    lang = "C++" if any(x in content for x in cpp_indicators) else "C"
                                else:
                                    lang = EXT_MAP[ext]
                                
                                lines = len([l for l in content.splitlines() if l.strip()])
                                stats[lang] = stats.get(lang, 0) + lines
                                total_loc += lines
                        except: continue
    return stats, total_loc

def generate_svg(stats, total):
    languages = sorted([(k, v, (v/total)*100) for k,v in stats.items()], key=lambda x: x[2], reverse=True)
    
    progress_bar = ""
    legend = ""
    current_delay = 0.85
    
    for name, size, percent in languages:
        color = LANG_COLORS.get(name, "#999999")
        progress_bar += f'<span class="progress-item" style="--final-width:{percent}%; --color:{color}; --delay:{current_delay}s;"></span>'
        legend += f'''
        <li style="--li-delay:{current_delay}s; width: 33%;">
          <svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{color};" viewBox="0 0 16 16" width="16" height="16">
            <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"></path>
          </svg>
          <span class="lang">{name}</span>
          <span class="percent">{percent:.1f}%</span>
        </li>'''
        current_delay += 0.2

    # SVG Template dengan CSS Variables untuk Dark Mode Otomatis
    svg_template = f'''<svg width="450" height="220" xmlns="http://www.w3.org/2000/svg">
    <style>
        :root {{
            --bg-color: #fff;
            --border-color: #e1e4e8;
            --header-color: #006AFF;
            --lang-color: #24292e;
            --percent-color: #586069;
            --bar-bg: #e1e4e8;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #0d1117;
                --border-color: #30363d;
                --header-color: #58a6ff;
                --lang-color: #c9d1d9;
                --percent-color: #8b949e;
                --bar-bg: #21262d;
            }}
        }}

        svg {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial; font-size: 14px; }}
        h2 {{ font-size:16px; font-weight:600; color: var(--header-color); margin:0 0 0.75em 0; }}
        
        .card {{
            padding: 20px;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            background: var(--bg-color);
        }}

        .progress {{ display:flex; height:10px; overflow:hidden; background-color: var(--bar-bg); border-radius:6px; margin-bottom:1.5em; }}
        
        @keyframes progressGrow {{ from {{ width:0; }} to {{ width:var(--final-width); }} }}
        
        .progress-item {{ 
            width:0; 
            background-color:var(--color); 
            animation:progressGrow 2s cubic-bezier(.33,1.53,.53,1.01) forwards; 
            animation-delay:var(--delay); 
        }}
        
        ul {{ list-style:none; padding:0; margin:0; display:flex; flex-wrap:wrap; }}
        li {{ display:flex; align-items:center; font-size:12px; margin-bottom:8px; color: var(--lang-color); }}
        
        .lang {{ font-weight:600; margin-right:4px; margin-left:4px; color: var(--lang-color); }}
        .percent {{ color: var(--percent-color); }}
    </style>
    <foreignObject x="0" y="0" width="450" height="220">
        <div xmlns="http://www.w3.org/1999/xhtml" class="card">
            <h2>language used</h2>
            <div class="progress">{progress_bar}</div>
            <ul>{legend}</ul>
        </div>
    </foreignObject>
    </svg>'''
    
    os.makedirs("output", exist_ok=True)
    with open("output/stats_langs.svg", "w", encoding="utf-8") as f:
        f.write(svg_template)

if __name__ == "__main__":
    result = get_stats()
    if result:
        generate_svg(result[0], result[1])
        print("SVG Updated in output/stats_langs.svg")