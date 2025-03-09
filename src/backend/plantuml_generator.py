import os
import ast
import subprocess
from pathlib import Path
from collections import defaultdict

class PlantUMLGenerator:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = self.repo_path / "diagrams"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all(self):
        diagrams = {
            "class": self.generate_class_diagram(),
            "sequence": self.generate_sequence_diagram(),
            "component": self.generate_component_diagram(),
        }
        return diagrams

    def generate_class_diagram(self):
        """Generates a class diagram based on Python classes found in the repository."""
        class_diagram_path = self.output_dir / "class_diagram.puml"
        classes = self.extract_classes()

        with open(class_diagram_path, "w") as f:
            f.write("@startuml\n")
            for class_name, methods in classes.items():
                f.write(f"class {class_name} {{\n")
                for method in methods:
                    f.write(f"  +{method}()\n")
                f.write("}\n")
            f.write("@enduml\n")

        return self.render_plantuml(class_diagram_path)

    def generate_sequence_diagram(self):
        """Generates a sequence diagram showing function calls between classes."""
        sequence_diagram_path = self.output_dir / "sequence_diagram.puml"
        calls = self.extract_function_calls()

        with open(sequence_diagram_path, "w") as f:
            f.write("@startuml\n")
            for caller, callees in calls.items():
                for callee in callees:
                    f.write(f"{caller} -> {callee}: calls\n")
            f.write("@enduml\n")

        return self.render_plantuml(sequence_diagram_path)

    def generate_component_diagram(self):
        """Generates a component diagram showing dependencies between modules."""
        component_diagram_path = self.output_dir / "component_diagram.puml"
        dependencies = self.extract_module_dependencies()

        with open(component_diagram_path, "w") as f:
            f.write("@startuml\n")
            for module, imports in dependencies.items():
                for imp in imports:
                    f.write(f"[{module}] --> [{imp}]\n")
            f.write("@enduml\n")

        return self.render_plantuml(component_diagram_path)

    def render_plantuml(self, puml_path):
        """Renders a PlantUML diagram into a PNG file."""
        output_image_path = puml_path.with_suffix(".png")
        subprocess.run(["plantuml", "-tpng", str(puml_path)], check=True)
        return output_image_path

    def extract_classes(self):
        """Extracts class names and their methods from Python files."""
        classes = defaultdict(list)
        for file_path in self.repo_path.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        classes[class_name].extend(methods)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

        return classes

    def extract_function_calls(self):
        """Extracts function calls between classes for sequence diagrams."""
        calls = defaultdict(set)
        for file_path in self.repo_path.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                current_class = None
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        current_class = node.name
                    elif isinstance(node, ast.FunctionDef):
                        function_name = node.name
                        for stmt in ast.walk(node):
                            if isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Attribute):
                                called_method = stmt.func.attr
                                calls[f"{current_class}.{function_name}"].add(called_method)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

        return calls

    def extract_module_dependencies(self):
        """Extracts module-level dependencies for component diagrams."""
        dependencies = defaultdict(set)
        for file_path in self.repo_path.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                module_name = file_path.stem
                for node in tree.body:
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            dependencies[module_name].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        dependencies[module_name].add(node.module)

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

        return dependencies
