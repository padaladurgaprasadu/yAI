import os
import ast
import json
from typing import Dict, List, Set, Any
from pathlib import Path

class RepoGraph:
    """
    Builds a semantic dependency graph of the repository.
    Used by the ContextOrchestrator to fetch related files dynamically.
    """
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.graph: Dict[str, List[str]] = {}
        self.file_index: Dict[str, str] = {}
        
    def build_graph(self):
        """Scans the repository and builds the dependency map."""
        self.graph.clear()
        self.file_index.clear()
        
        for root, dirs, files in os.walk(self.root_dir):
            # Ignore hidden directories and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules' and d != 'venv']
            
            for file in files:
                if file.endswith('.py') or file.endswith('.js') or file.endswith('.jsx'):
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
                    self.file_index[rel_path] = str(file_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            imports = self._extract_imports(content, file_path.suffix)
                            self.graph[rel_path] = imports
                    except Exception:
                        pass
                        
    def _extract_imports(self, content: str, ext: str) -> List[str]:
        """Extracts imports from the file content."""
        imports = []
        if ext == '.py':
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            imports.append(name.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
            except SyntaxError:
                pass
        elif ext in ['.js', '.jsx']:
            # Extremely basic regex heuristic for JS/JSX
            import re
            js_imports = re.findall(r'import\s+.*?\s+from\s+[\'"](.*?)[\'"]', content)
            require_imports = re.findall(r'require\([\'"](.*?)[\'"]\)', content)
            imports.extend(js_imports + require_imports)
            
        return imports

    def get_related_files(self, filepath: str) -> List[str]:
        """Returns a list of files that this file depends on, or files that depend on it."""
        filepath = filepath.replace("\\", "/")
        related = set()
        
        # Outbound dependencies
        if filepath in self.graph:
            related.update(self.graph[filepath])
            
        # Inbound dependencies (who imports this?)
        # Simple heuristic: checking if the filename base is in someone's import list
        base_name = Path(filepath).stem
        for f_path, f_imports in self.graph.items():
            for imp in f_imports:
                if base_name in imp or imp in filepath:
                    related.add(f_path)
                    
        return list(related)

    def to_json(self) -> str:
        return json.dumps(self.graph, indent=2)

if __name__ == "__main__":
    # Test the repo graph
    import sys
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    rg = RepoGraph(test_dir)
    rg.build_graph()
    print(f"Mapped {len(rg.graph)} files.")
