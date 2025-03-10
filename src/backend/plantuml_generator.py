import ast
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import pkg_resources

# Map known API libraries to external services
KNOWN_EXTERNAL_SERVICES = {
    "requests": "HTTP API",
    "boto3": "AWS SDK",
    "stripe": "Stripe API",
    "firebase_admin": "Firebase API",
    "twilio": "Twilio API",
    "pymongo": "MongoDB Atlas",
    "google.cloud": "Google Cloud API",
    "openai": "OpenAI API",
    "auth0": "Auth0 Authentication",
}

# Output files
CONTEXT_PUML = "c4_context.puml"
CONTAINER_PUML = "c4_container.puml"
COMPONENT_PUML = "c4_component.puml"

OUTPUT_IMAGES = ["c4_context.png", "c4_container.png", "c4_component.png"]


def render_plantuml(puml_path):
    output_image_path = puml_path.with_suffix(".png")
    subprocess.run(["plantuml", "-tpng", str(puml_path)], check=True)
    return output_image_path


def get_installed_packages():
    """Retrieve a list of installed packages from the environment."""
    installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    return installed_packages


def extract_imports_from_code(directory):
    """Parse Python files and extract imported modules."""
    imported_modules = set()

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and not file.startswith("__init__"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    imported_modules.add(alias.name.split(".")[0])
                            elif isinstance(node, ast.ImportFrom):
                                imported_modules.add(
                                    node.module.split(".")[0] if node.module else ""
                                )
                    except SyntaxError:
                        print(f"Skipping {file_path} due to syntax error.")

    return imported_modules


def detect_external_services(imported_modules):
    """Detect external APIs based on known API libraries."""
    installed_packages = get_installed_packages()
    detected_services = {}

    for module in imported_modules:
        if module in KNOWN_EXTERNAL_SERVICES:
            detected_services[module] = KNOWN_EXTERNAL_SERVICES[module]
        elif module in installed_packages:
            detected_services[module] = f"Third-Party Library ({module})"

    return detected_services


def extract_python_structure(directory):
    """Extracts modules, classes, and functions to structure the architecture."""
    architecture = {
        "modules": set(),
        "classes": set(),
        "functions": set(),
        "dependencies": set(),
    }

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and not file.startswith("__init__"):
                file_path = os.path.join(root, file)
                module_name = (
                    os.path.relpath(file_path, directory)
                    .replace("/", ".")
                    .replace("\\", ".")
                    .replace(".py", "")
                )
                architecture["modules"].add(module_name)

                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = f"{module_name}.{node.name}"
                                architecture["classes"].add(class_name)

                                # Extract class dependencies (parent classes)
                                for base in node.bases:
                                    if isinstance(base, ast.Name):
                                        parent = base.id
                                        architecture["dependencies"].add(
                                            (class_name, parent)
                                        )

                            if isinstance(node, ast.FunctionDef):
                                func_name = f"{module_name}.{node.name}()"
                                architecture["functions"].add(func_name)
                    except SyntaxError:
                        print(f"Skipping {file_path} due to syntax error.")

    return architecture


class PlantUMLGenerator:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = self.repo_path / "diagrams"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all(self):
        # Extract architecture from the codebase
        architecture_data = extract_python_structure(self.repo_path)

        # Extract imported modules from the Python project
        imported_modules = extract_imports_from_code(self.repo_path)

        # Detect external APIs based on known services
        external_services = detect_external_services(imported_modules)
        diagrams = {
            "class": self.generate_class_diagram(),
            "sequence": self.generate_sequence_diagram(),
            "component": self.generate_component_diagram(),
            "context": self.generate_context_diagram(external_services),
            "container": self.generate_container_diagram(
                architecture_data, external_services
            ),
            "c4_component": self.generate_c4_component_diagram(architecture_data),
        }
        return diagrams

    def generate_class_diagram(self):
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

        return render_plantuml(class_diagram_path)

    def generate_sequence_diagram(self):
        sequence_diagram_path = self.output_dir / "sequence_diagram.puml"
        calls = self.extract_function_calls()

        with open(sequence_diagram_path, "w") as f:
            f.write("@startuml\n")
            for caller, callees in calls.items():
                for callee in callees:
                    f.write(f"{caller} -> {callee}: calls\n")
            f.write("@enduml\n")

        return render_plantuml(sequence_diagram_path)

    def generate_component_diagram(self):
        component_diagram_path = self.output_dir / "component_diagram.puml"
        dependencies = self.extract_module_dependencies()

        with open(component_diagram_path, "w") as f:
            f.write("@startuml\n")
            for module, imports in dependencies.items():
                for imp in imports:
                    f.write(f"[{module}] --> [{imp}]\n")
            f.write("@enduml\n")

        return render_plantuml(component_diagram_path)

    def generate_context_diagram(self, external_services):
        """Generates a C4 Context Diagram."""
        component_diagram_path = self.output_dir / "context_diagram.puml"
        with open(component_diagram_path, "w", encoding="utf-8") as f:
            f.write("@startuml\n")
            f.write("!include <C4/C4_Context>\n\n")

            f.write('Person(user, "User", "End user interacting with the system")\n')
            f.write('System_Boundary(py_app, "Python Application") {\n')
            f.write('    System(app, "Python Backend", "Main application backend")\n')
            f.write("}\n")

            for ext, desc in external_services.items():
                ext_var = ext.replace(" ", "_").lower()
                f.write(f'System_Ext({ext_var}, "{desc}", "External service")\n')
                f.write(f'app -> {ext_var} : "Interacts with {desc}"\n')

            f.write('user -> app : "Uses the application"\n')
            f.write("@enduml\n")

        return render_plantuml(component_diagram_path)

    def generate_container_diagram(self, architecture, external_services):
        """Generates a C4 Container Diagram."""
        component_diagram_path = self.output_dir / "container_diagram.puml"
        with open(component_diagram_path, "w", encoding="utf-8") as f:
            f.write("@startuml\n")
            f.write("!include <C4/C4_Container>\n\n")

            f.write('Person(user, "User", "End user interacting with the system")\n')
            f.write('System_Boundary(py_app, "Python Application") {\n')

            for module in architecture["modules"]:
                f.write(
                    f"    Container({module.replace('.', '_')}, \"{module}\", \"Python Module\")\n"
                )

            f.write("}\n")

            # External services
            for ext, desc in external_services.items():
                ext_var = ext.replace(" ", "_").lower()
                f.write(f'System_Ext({ext_var}, "{desc}", "External service")\n')
                f.write(f'app -> {ext_var} : "Interacts with {desc}"\n')

            f.write("user -> py_app : Uses the application\n")
            f.write("@enduml\n")

        return render_plantuml(component_diagram_path)

    def generate_c4_component_diagram(self, architecture):
        """Generates a C4 Component Diagram."""
        component_diagram_path = self.output_dir / "c4_component_diagram.puml"
        with open(component_diagram_path, "w", encoding="utf-8") as f:
            f.write("@startuml\n")
            f.write("!include <C4/C4_Component>\n\n")

            f.write('System_Boundary(py_app, "Python Application") {\n')

            for class_name in architecture["classes"]:
                class_id = class_name.replace(".", "_")
                f.write(f'    Component({class_id}, "{class_name}", "Python Class")\n')

            f.write("}\n")

            for source, target in architecture["dependencies"]:
                source_id = source.replace(".", "_")
                target_id = target.replace(".", "_")
                f.write(f'{source_id} -> {target_id} : "Inherits"\n')

            f.write("@enduml\n")

        return render_plantuml(component_diagram_path)

    def extract_external_dependencies(self):
        """Identifies external dependencies like AWS services, databases, etc."""
        external_deps = set()
        for file_path in self.repo_path.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                if "boto3" in code:
                    external_deps.add("AWS Services")
                if "psycopg2" in code or "sqlalchemy" in code:
                    external_deps.add("PostgreSQL")
                if "redis" in code:
                    external_deps.add("Redis")
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        return external_deps

    def extract_classes(self):
        classes = defaultdict(list)
        for file_path in self.repo_path.rglob("*.py"):
            ext = file_path.suffix.lower()
            try:
                if ext == ".py":
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_name = node.name
                            methods = [
                                n.name
                                for n in node.body
                                if isinstance(n, ast.FunctionDef)
                            ]
                            classes[class_name].extend(methods)

                # elif ext in [".java", ".js", ".cpp", ".c", ".h"]:
                #     with open(file_path, "r", encoding="utf-8") as f:
                #         code = f.read()
                #     class_pattern = r'class\s+(\w+)\s*[{|:]'
                #     function_pattern = r'(public|private|protected)?\s*\w+\s+(\w+)\s*\(.*\)\s*[{|;]'
                #     found_classes = re.findall(class_pattern, code)
                #     found_functions = re.findall(function_pattern, code)
                #     for cls in found_classes:
                #         classes[cls] = []
                #     for func in found_functions:
                #         if func[1] not in classes:
                #             classes[func[1]] = []
                #         classes[func[1]].append(func[1])
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        return classes

    def extract_function_calls(self):
        calls = defaultdict(set)
        for file_path in self.repo_path.rglob("*.py"):
            ext = file_path.suffix.lower()
            try:
                if ext == ".py":
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    current_class = None
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            current_class = node.name
                        elif isinstance(node, ast.FunctionDef):
                            function_name = node.name
                            for stmt in ast.walk(node):
                                if isinstance(stmt, ast.Call) and isinstance(
                                    stmt.func, ast.Attribute
                                ):
                                    called_method = stmt.func.attr
                                    calls[f"{current_class}.{function_name}"].add(
                                        called_method
                                    )
                # elif ext in [".java", ".js", ".cpp", ".c", ".h"]:
                #     with open(file_path, "r", encoding="utf-8") as f:
                #         code = f.read()
                #     function_call_pattern = r"(\w+)\.(\w+)\s*\("
                #     matches = re.findall(function_call_pattern, code)
                #     for cls, method in matches:
                #         calls[f"{cls}.{method}"].add(method)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        return calls

    def extract_module_dependencies(self):
        dependencies = defaultdict(set)
        for file_path in self.repo_path.rglob("*.py"):
            ext = file_path.suffix.lower()
            try:
                if ext == ".py":
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    module_name = file_path.stem
                    for node in tree.body:
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                dependencies[module_name].add(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            dependencies[module_name].add(node.module)
                # elif ext in [".java", ".js", ".cpp", ".c", ".h"]:
                #     with open(file_path, "r", encoding="utf-8") as f:
                #         code = f.read()
                #     import_pattern = r"import\s+([\w.]+)"
                #     imports = re.findall(import_pattern, code)
                #     module_name = file_path.stem
                #     for imp in imports:
                #         dependencies[module_name].add(imp)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        return dependencies
