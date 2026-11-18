"""Validate cross-domain release dependency graphs without credentials."""
from __future__ import annotations


def validate_graph(nodes: object) -> list[str]:
    if not isinstance(nodes, list):
        return ["Release dependencies must be a list"]
    errors, graph, domains = [], {}, {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue
        name, domain, deps = node.get("name"), node.get("domain"), node.get("depends_on", [])
        if set(node) - {"name", "domain", "depends_on"}:
            errors.append(f"nodes[{index}] contains unsupported fields; credentials are not permitted")
        if not isinstance(name, str) or not name.strip() or name in graph:
            errors.append(f"nodes[{index}].name must be nonempty and unique")
            continue
        if domain not in ("fabric", "power-bi"):
            errors.append(f"nodes[{index}].domain must be fabric or power-bi")
        if not isinstance(deps, list) or any(not isinstance(dep, str) or not dep.strip() for dep in deps):
            errors.append(f"nodes[{index}].depends_on must contain names")
            deps = []
        graph[name] = deps
        domains[name] = domain
    for name, deps in graph.items():
        for dep in deps:
            if dep not in graph:
                errors.append(f"{name} references missing dependency {dep}")
            elif domains[name] == "fabric" and domains[dep] == "power-bi":
                errors.append(f"Fabric release {name} cannot depend on Power BI release {dep}")
    visited, visiting = set(), set()
    def walk(name):
        if name in visiting:
            return True
        if name in visited:
            return False
        visiting.add(name)
        cyclic = any(walk(dep) for dep in graph[name] if dep in graph)
        visiting.remove(name)
        visited.add(name)
        return cyclic
    if any(walk(name) for name in graph if name not in visited):
        errors.append("Release dependencies contain a cycle")
    return errors


def validate_cross_domain(pbi: object, nodes: object) -> list[str]:
    """Require each explicit Power BI prerequisite to reference a Fabric node."""
    from validate_pbi_mapping import validate as validate_mapping
    errors = validate_mapping(pbi) + validate_graph(nodes)
    if errors:
        return errors
    by_name = {node["name"]: node for node in nodes}
    for mapping in pbi["mappings"]:
        for dep in mapping.get("fabric_prerequisites", []):
            if dep not in by_name or by_name[dep]["domain"] != "fabric":
                errors.append(f"{mapping['name']} references missing Fabric release {dep}")
    return errors
