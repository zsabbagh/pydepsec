import re

def create_purl(type, namespace, name, version, qualifiers=None, subpath=None):
    """
    Create a PURL (Package URL) string, used by Snyk for example.

    type: The package type (e.g., 'pypi' for Python packages).
    namespace: The namespace of the package (often left blank for Python).
    name: The name of the package.
    version: The version of the package.
    qualifiers: A dictionary of qualifier keys and values.
    subpath: The subpath within the package.
    """
    purl = f"pkg:{type}/{namespace}/{name}@{version}"
    if qualifiers:
        # Convert qualifiers dictionary to a sorted, encoded string
        qualifier_str = '&'.join(f"{key}={value}" for key, value in sorted(qualifiers.items()))
        purl += f"?{qualifier_str}"
    if subpath:
        purl += f"#{subpath}"
    return purl

def homepage_to_vendor(homepage: str) -> str:
    """
    Get the vendor from the homepage URL.

    This is not a perfect solution, but it works for most cases.
    """
    if not homepage:
        return None
    print(f"Homepage: {homepage}")
    homepage = re.sub(r'^https?://', '', homepage)
    print(f"Homepage: {homepage}")
    parts = homepage.split('.')
    print(f"Parts: {parts}")
    if len(parts) < 2:
        return None
    return parts[-2]