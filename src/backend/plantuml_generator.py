import os
import subprocess


class PlantUMLGenerator:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.output_dir = os.path.join(repo_path, "diagrams")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all(self):
        diagrams = {"class": self.generate_class_diagram(), "sequence": self.generate_sequence_diagram(),
                    "component": self.generate_component_diagram()}
        return diagrams

    def generate_class_diagram(self):
        class_diagram_path = os.path.join(self.output_dir, "class_diagram.puml")
        with open(class_diagram_path, "w") as f:
            f.write("@startuml\n")
            f.write(
                "class ExampleClass {\n  +method1()\n  -method2()\n}\n"
            )  # Placeholder, integrate with repo_parser
            f.write("@enduml\n")
        return self.render_plantuml(class_diagram_path)

    def generate_sequence_diagram(self):
        sequence_diagram_path = os.path.join(self.output_dir, "sequence_diagram.puml")
        with open(sequence_diagram_path, "w") as f:
            f.write("@startuml\n")
            f.write("Alice -> Bob: Hello\n")  # Placeholder example
            f.write("@enduml\n")
        return self.render_plantuml(sequence_diagram_path)

    def generate_component_diagram(self):
        component_diagram_path = os.path.join(self.output_dir, "component_diagram.puml")
        with open(component_diagram_path, "w") as f:
            f.write("@startuml\n")
            f.write("[Component1] --> [Component2]\n")  # Placeholder example
            f.write("@enduml\n")
        return self.render_plantuml(component_diagram_path)

    def render_plantuml(self, puml_path):
        output_image_path = puml_path.replace(".puml", ".png")
        subprocess.run(["plantuml", "-tpng", puml_path], check=True)
        return output_image_path
