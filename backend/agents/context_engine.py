import os
import re
import ast
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ContextEngine:
    """
    Advanced Context Engine (yAI IDE OS)
    Dynamically fetches relationships and dependencies using AST and Regex.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    def _get_python_imports(self, code: str) -> list:
        """Uses AST to parse python imports."""
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            pass
        return imports

    def _get_js_imports(self, code: str) -> list:
        """Uses Regex to parse JS/TS imports."""
        imports = []
        # Matches `import ... from '...'` or `require('...')`
        import_patterns = [
            r"import\s+.*?\s+from\s+['\"](.*?)['\"]",
            r"require\(['\"](.*?)['\"]\)"
        ]
        for pattern in import_patterns:
            matches = re.findall(pattern, code)
            imports.extend(matches)
        return imports

    def resolve_path(self, current_file: str, import_str: str) -> str:
        """Resolves an import path to an absolute file path in the workspace."""
        if not import_str.startswith('.'):
            # Might be a backend.xxx.yyy python module
            if import_str.startswith('backend.'):
                possible_path = os.path.join(self.workspace_root, import_str.replace('.', '/') + '.py')
                if os.path.exists(possible_path):
                    return possible_path
            return "" # External library

        # Relative paths (JS/TS)
        current_dir = os.path.dirname(current_file)
        # Handle trailing JS extensions
        clean_import = import_str
        if not clean_import.endswith('.js') and not clean_import.endswith('.ts') and not clean_import.endswith('.jsx') and not clean_import.endswith('.tsx'):
            # Guess extensions
            for ext in ['.ts', '.js', '.tsx', '.jsx']:
                test_path = os.path.normpath(os.path.join(current_dir, clean_import + ext))
                if os.path.exists(test_path):
                    return test_path
        else:
            test_path = os.path.normpath(os.path.join(current_dir, clean_import))
            if os.path.exists(test_path):
                return test_path
                
        return ""

    def build_dependency_context(self, target_file_path: str, max_depth: int = 1) -> str:
        """
        Reads the target file, parses its dependencies, and recursively gathers their code.
        Returns a formatted markdown string of all related files.
        """
        if not os.path.exists(target_file_path):
            return ""

        context_blocks = []
        visited = set()

        def fetch_deps(filepath, depth):
            if depth > max_depth or filepath in visited:
                return
            visited.add(filepath)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
            except Exception as e:
                logger.warning(f"ContextEngine failed to read {filepath}: {e}")
                return

            context_blocks.append(f"### [Dependency Context] {os.path.basename(filepath)}\n```\n{code}\n```")

            if depth < max_depth:
                ext = filepath.split('.')[-1].lower()
                imports = []
                if ext == 'py':
                    imports = self._get_python_imports(code)
                elif ext in ['js', 'ts', 'jsx', 'tsx']:
                    imports = self._get_js_imports(code)
                
                for imp in imports:
                    resolved = self.resolve_path(filepath, imp)
                    if resolved:
                        fetch_deps(resolved, depth + 1)

        # Start recursion
        fetch_deps(target_file_path, 0)
        
        # Don't return the target file itself in the dependency block (it's usually passed separately)
        if len(context_blocks) > 1:
            return "\n\n".join(context_blocks[1:]) 
        return "No local dependencies found."
