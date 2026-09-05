import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web.api_app import create_app


def generate_markdown_docs():
    app = create_app(testing=True)
    openapi = app.openapi()

    md_lines = []

    # 1. Header & Plugin Architecture Section
    md_lines.append("# EchoSync Enterprise API Reference (v2.5.0)\n")
    md_lines.append("## Architecture Overview & Zero-Trust Plugin Namespacing\n")
    md_lines.append(
        "EchoSync's v2.5.0 rebuild runs entirely on FastAPI / ASGI, offering high-performance, asynchronous endpoints "
        "and auto-validated Pydantic models.\n"
    )
    md_lines.append("### Zero-Trust Sub-Application Namespacing\n")
    md_lines.append(
        "All dynamically registered third-party and custom plugin REST endpoints are isolated using FastAPI Sub-Applications. "
        "Each plugin's API routes are mounted strictly under the `/api/v1/plugins/{plugin_id}/` hierarchical namespace.\n\n"
        "- **Collision Isolation:** The mandatory `{plugin_id}` prefix guarantees that plugins can never collide with core routes or hijack other plugins' endpoints.\n"
        "- **Context Scope:** Plugins operate strictly within their isolated sub-app context and facade storage boundaries.\n"
    )
    md_lines.append("---\n")

    # 2. Extract OpenAPI paths and group by Tags
    paths = openapi.get("paths", {})
    components = openapi.get("components", {}).get("schemas", {})

    tagged_endpoints = {}

    for path, methods in paths.items():
        for method, spec in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue

            tags = spec.get("tags", ["General"])
            tag = tags[0] if tags else "General"

            if tag not in tagged_endpoints:
                tagged_endpoints[tag] = []

            tagged_endpoints[tag].append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": spec.get(
                        "summary", spec.get("description", "No summary provided.")
                    ),
                    "parameters": spec.get("parameters", []),
                    "request_body": spec.get("requestBody"),
                    "responses": spec.get("responses", {}),
                }
            )

    # 3. Format Endpoints into Markdown
    md_lines.append("## API Endpoints Reference\n")

    for tag, endpoints in sorted(tagged_endpoints.items()):
        md_lines.append(f"### {tag}\n")
        for ep in endpoints:
            md_lines.append(f"#### `{ep['method']}` `{ep['path']}`\n")
            md_lines.append(f"**Summary:** {ep['summary']}\n")

            # Parameters
            if ep["parameters"]:
                md_lines.append("\n**Parameters:**\n")
                md_lines.append("| Name | In | Required | Type | Description |")
                md_lines.append("| --- | --- | --- | --- | --- |")
                for p in ep["parameters"]:
                    p_name = p.get("name", "")
                    p_in = p.get("in", "")
                    p_req = "Yes" if p.get("required") else "No"
                    p_schema = p.get("schema", {})
                    p_type = p_schema.get("type", "string")
                    p_desc = p.get("description", "")
                    md_lines.append(
                        f"| `{p_name}` | {p_in} | {p_req} | `{p_type}` | {p_desc} |"
                    )
                md_lines.append("")

            # Request Body
            if ep["request_body"]:
                content = ep["request_body"].get("content", {})
                json_schema = content.get("application/json", {}).get("schema", {})
                if json_schema:
                    ref = json_schema.get("$ref")
                    if ref:
                        schema_name = ref.split("/")[-1]
                        md_lines.append(f"\n**Request Body Schema:** `{schema_name}`\n")
                    else:
                        md_lines.append("\n**Request Body Schema:** Custom JSON Body\n")

            md_lines.append("\n---\n")

    doc_content = "\n".join(md_lines)

    os.makedirs("docs", exist_ok=True)
    with open("docs/API_REFERENCE.md", "w", encoding="utf-8") as f:
        f.write(doc_content)

    print("Successfully generated docs/API_REFERENCE.md")


if __name__ == "__main__":
    generate_markdown_docs()
