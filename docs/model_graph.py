import os

from django.core.management import call_command


def generate_model_graphs(app):
    output_dir = os.path.join(app.srcdir, "_static", "uml")
    os.makedirs(output_dir, exist_ok=True)

    project_root = os.path.abspath(os.path.join(app.srcdir, ".."))
    components_dir = os.path.join(project_root, "src", "openzaak", "components")

    apps_in_components = [
        d
        for d in os.listdir(components_dir)
        if os.path.isdir(os.path.join(components_dir, d))
        and os.path.isfile(os.path.join(components_dir, d, "__init__.py"))
    ]

    # Models you want to exclude from diagrams
    excluded_models = [
        "SingletonModel",
        "ETagMixin",
        "AuthorizationsConfig",
        "Service",
        "ConceptMixin",
        "GeldigheidMixin",
        "OptionalGeldigheidMixin",
        "ContextMixin",
        "ReservedDocument",
    ]

    exclude_models_str = ",".join(excluded_models)

    # Define grouped apps you want in one diagram
    grouped_apps = {
        "autorisaties": ["autorisaties", "authorizations"],
    }

    for group_name, app_list in grouped_apps.items():
        png_path = os.path.join(output_dir, f"{group_name}.png")
        try:
            call_command(
                "graph_models",
                *app_list,
                output=png_path,
                rankdir="LR",
                hide_edge_labels=True,
                exclude_models=exclude_models_str,
            )
        except Exception as exc:
            print(f"Failed to generate PNG for {group_name}: {exc}")

    # Generate separate diagrams for the remaining apps
    excluded_apps = set(app for group in grouped_apps.values() for app in group)
    for comp in apps_in_components:
        if comp in excluded_apps:
            continue

        png_path = os.path.join(output_dir, f"{comp}.png")
        try:
            call_command(
                "graph_models",
                comp,
                output=png_path,
                rankdir="LR",
                hide_edge_labels=True,
                exclude_models=exclude_models_str,
            )
        except Exception as exc:
            print(f"Failed to generate PNG for {comp}: {exc}")
