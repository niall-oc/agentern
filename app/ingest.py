"""
Repository ingester for ChromaDB with semantic chunking.

This module provides :func:`ingest_directory` which walks a
filesystem directory, classifies files by extension, parses them
into structured semantic chunks (functions, classes, markdown
sections, etc.), and stores the result in a ChromaDB vector
collection for later similarity search.

**Supported file types:**

* **Source code** (Python, JavaScript, TypeScript, Java, C#, C++,
  C, Go, Rust, Haskell, Erlang, Pascal, BASIC, Astro) — parsed via
  Python's built-in :mod:`ast` for Python and optionally via
  `tree-sitter <https://tree-sitter.github.io/>`_ for other
  languages.
* **Documentation** (Markdown, reStructuredText, plain text)
* **Office documents** (PDF via PyMuPDF, DOCX via python-docx)
* **Configuration files** (JSON, YAML/yml, TOML, INI)

**Metadata:**

Each chunk is tagged with rich metadata — repository name, relative
file path, language, chunk type (``class``, ``function``,
``markdown_section``, etc.), symbol name, parent scope, and source
line numbers — allowing precise filtering during retrieval.
"""

import argparse
import ast
import hashlib
import os
import sys
from typing import List, Dict, Any, Optional, Tuple

# ----------------------------------------------------------------------
# File classification maps
# ----------------------------------------------------------------------

SOURCE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".go": "go",
    ".rs": "rust",
    ".astro": "astro",
    ".hs": "haskell",
    ".lhs": "haskell",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".pas": "pascal",
    ".pp": "pascal",
    ".p": "pascal",
    ".dpr": "pascal",
    ".lpr": "pascal",
    ".bas": "basic",
    ".vb": "basic",
    ".vbs": "basic",
    ".frm": "basic",
    ".cls": "basic",
}

DOCUMENT_EXTENSIONS = {
    ".md": "markdown",
    ".txt": "text",
    ".rst": "restructuredtext",
}

OFFICE_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
}

CONFIG_EXTENSIONS = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
}

ALL_EXTENSIONS = {
    **SOURCE_EXTENSIONS, **DOCUMENT_EXTENSIONS,
    **OFFICE_EXTENSIONS, **CONFIG_EXTENSIONS,
}


# ----------------------------------------------------------------------
# Binary detection
# ----------------------------------------------------------------------

def is_binary(filepath: str) -> bool:
    """Detect whether *filepath* points to a binary file.

    Reads the first 1024 bytes and checks for a null byte
    (``\\x00``).  Files that cannot be opened are conservatively
    treated as binary.

    :param filepath: Absolute or relative path to the file.
    :returns: ``True`` if the file is binary, ``False`` otherwise.
    """
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
        return b"\0" in chunk
    except Exception:
        return True


# ----------------------------------------------------------------------
# Python AST parser
# ----------------------------------------------------------------------

def parse_python(filepath: str) -> List[Dict[str, Any]]:
    """Parse a Python source file and extract classes / functions / methods.

    Uses Python's built-in :mod:`ast` module.  The returned list
    entries follow this schema:

    * ``"type"`` — ``"class"``, ``"function"``, or ``"method"``
    * ``"name"`` — the symbol name
    * ``"code"`` — the exact source segment as a string
    * ``"parent"`` — for methods, the containing class name;
      ``None`` otherwise
    * ``"start_line"`` / ``"end_line"`` — 1-based line numbers

    :param filepath: Path to a ``.py`` file.
    :returns: List of chunk dictionaries.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    chunks = []

    def get_segment(node):
        return ast.get_source_segment(source, node)

    # First pass: collect class nodes
    class_nodes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_nodes[node.name] = node
            chunks.append({
                "type": "class",
                "name": node.name,
                "code": get_segment(node),
                "parent": None,
                "start_line": node.lineno,
                "end_line": node.end_lineno if node.end_lineno else node.lineno,
            })

    # Second pass: collect functions, checking if they are methods
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            parent_class = None
            for cls_name, cls_node in class_nodes.items():
                if node in ast.walk(cls_node):
                    parent_class = cls_name
                    break
            chunk_type = "method" if parent_class else "function"
            chunks.append({
                "type": chunk_type,
                "name": node.name,
                "code": get_segment(node),
                "parent": parent_class,
                "start_line": node.lineno,
                "end_line": node.end_lineno if node.end_lineno else node.lineno,
            })

    return chunks


# ----------------------------------------------------------------------
# Tree-sitter parser (optional)
# ----------------------------------------------------------------------

try:
    import tree_sitter as ts
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True

    LANG_NAMES = {
        "python": "python",
        "javascript": "javascript",
        "typescript": "typescript",
        "tsx": "tsx",
        "java": "java",
        "csharp": "c_sharp",
        "cpp": "cpp",
        "c": "c",
        "go": "go",
        "rust": "rust",
        "haskell": "haskell",
        "erlang": "erlang",
        "pascal": "pascal",
        "basic": "basic",
    }

    _parsers = {}
    for lang in LANG_NAMES.values():
        try:
            import importlib
            module_name = f"tree_sitter_{lang.replace('_', '')}"
            try:
                mod = importlib.import_module(module_name)
                lang_func = getattr(mod, "language")
                _parsers[lang] = Parser()
                _parsers[lang].set_language(lang_func())
            except ImportError:
                pass
        except Exception:
            pass

    if not _parsers:
        TREE_SITTER_AVAILABLE = False

except ImportError:
    TREE_SITTER_AVAILABLE = False


def parse_with_tree_sitter(filepath: str, language: str) -> List[Dict[str, Any]]:
    """Parse a file using tree-sitter and extract top-level definitions.

    This is a generic implementation for any language with an installed
    tree-sitter grammar.  It walks the AST and collects function
    definitions, class definitions, interface declarations, and type
    aliases.

    Each result dict contains:

    * ``"type"`` — a human-readable type like ``"function"``,
      ``"class"``, ``"interface"``, or ``"symbol"``
    * ``"name"`` — the identifier text
    * ``"code"`` — the exact source segment
    * ``"parent"`` — for methods, the containing class name;
      ``None`` otherwise
    * ``"start_line"`` / ``"end_line"``

    :param filepath: Path to the source file.
    :param language: Language key (e.g. ``"javascript"``,
        ``"rust"``) used to look up the parser.
    :returns: List of chunk dictionaries, or an empty list if
        tree-sitter is unavailable or the language is not supported.
    """
    if not TREE_SITTER_AVAILABLE:
        return []

    lang_map = {
        "python": "python",
        "javascript": "javascript",
        "typescript": "typescript",
        "tsx": "tsx",
        "java": "java",
        "csharp": "c_sharp",
        "cpp": "cpp",
        "c": "c",
        "go": "go",
        "rust": "rust",
        "haskell": "haskell",
        "erlang": "erlang",
        "pascal": "pascal",
        "basic": "basic",
    }
    lang_key = lang_map.get(language)
    if not lang_key or lang_key not in _parsers:
        return []

    parser = _parsers[lang_key]
    with open(filepath, "rb") as f:
        code = f.read()
    tree = parser.parse(code)
    root = tree.root_node

    chunks = []

    def get_text(node):
        return code[node.start_byte : node.end_byte].decode("utf-8")

    def collect_definitions(node, parent_class=None):
        node_type = node.type
        def_types = {
            "function_definition",
            "function_declaration",
            "method_definition",
            "class_definition",
            "class_declaration",
            "interface_declaration",
            "type_alias_declaration",
            "function",
            "method",
        }
        if node_type in def_types:
            name_node = None
            for child in node.children:
                if child.type in ("identifier", "name", "type_identifier"):
                    name_node = child
                    break
            if name_node:
                name = get_text(name_node)
                chunk_type = node_type
                if "class" in node_type:
                    chunk_type = "class"
                elif "interface" in node_type:
                    chunk_type = "interface"
                elif "function" in node_type or "method" in node_type:
                    chunk_type = "function" if parent_class is None else "method"
                else:
                    chunk_type = "symbol"

                chunks.append({
                    "type": chunk_type,
                    "name": name,
                    "code": get_text(node),
                    "parent": parent_class,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                })
                if chunk_type == "class":
                    for child in node.children:
                        collect_definitions(child, parent_class=name)
                return
        for child in node.children:
            collect_definitions(child, parent_class)

    collect_definitions(root)
    return chunks


# ----------------------------------------------------------------------
# Markdown parser (split by headings)
# ----------------------------------------------------------------------

def parse_markdown(filepath: str) -> List[Dict[str, Any]]:
    """Parse a Markdown file, splitting into sections by headings.

    Each ``#``, ``##``, etc. starts a new section.  Content before
    the first heading is assigned a ``"name"`` of ``"Document"``.

    Result dict schema:

    * ``"type"`` — always ``"markdown_section"``
    * ``"name"`` — the heading text (without ``#`` markers)
    * ``"code"`` — the full section content
    * ``"start_line"`` / ``"end_line"``

    :param filepath: Path to a ``.md`` file.
    :returns: List of chunk dictionaries.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    sections = []
    current_heading = "Document"
    current_content = []
    start_line = 1
    for i, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            if current_content:
                sections.append({
                    "type": "markdown_section",
                    "name": current_heading,
                    "code": "".join(current_content),
                    "start_line": start_line,
                    "end_line": i - 1,
                })
            current_heading = line.strip().lstrip("#").strip()
            current_content = []
            start_line = i
        else:
            current_content.append(line)
    if current_content:
        sections.append({
            "type": "markdown_section",
            "name": current_heading,
            "code": "".join(current_content),
            "start_line": start_line,
            "end_line": len(lines),
        })
    return sections


# ----------------------------------------------------------------------
# PDF parser using PyMuPDF
# ----------------------------------------------------------------------

try:
    import fitz  # PyMuPDF

    HAS_PDF = True
except ImportError:
    HAS_PDF = False


def parse_pdf(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from a PDF using PyMuPDF.

    Returns a single chunk of type ``"pdf"`` containing all page text
    concatenated.

    .. note::

       Requires the ``PyMuPDF`` (``fitz``) package.  Returns an empty
       list if the package is not installed.

    :param filepath: Path to a ``.pdf`` file.
    :returns: A list with one chunk dictionary, or ``[]`` if PyMuPDF
        is unavailable.
    """
    if not HAS_PDF:
        return []
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return [
        {
            "type": "pdf",
            "name": os.path.basename(filepath),
            "code": text,
            "start_line": 1,
            "end_line": 1,
        }
    ]


# ----------------------------------------------------------------------
# DOCX parser using python-docx
# ----------------------------------------------------------------------

try:
    from docx import Document

    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def parse_docx(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from a DOCX using python-docx.

    Returns a single chunk of type ``"docx"`` containing all paragraph
    text joined by newlines.

    .. note::

       Requires the ``python-docx`` package.  Returns an empty list if
       the package is not installed.

    :param filepath: Path to a ``.docx`` file.
    :returns: A list with one chunk dictionary, or ``[]`` if
        python-docx is unavailable.
    """
    if not HAS_DOCX:
        return []
    doc = Document(filepath)
    text = "\n".join(p.text for p in doc.paragraphs)
    return [
        {
            "type": "docx",
            "name": os.path.basename(filepath),
            "code": text,
            "start_line": 1,
            "end_line": 1,
        }
    ]


# ----------------------------------------------------------------------
# Main dispatcher
# ----------------------------------------------------------------------

def parse_file(filepath: str, ext: str) -> List[Dict[str, Any]]:
    """Dispatch *filepath* to the appropriate parser based on extension.

    This is the top-level routing function called by
    :func:`ingest_directory`.  It uses the extension-to-type maps
    defined at module level to decide how to parse each file.

    :param filepath: Absolute or relative path to the file.
    :param ext: File extension including the leading dot, e.g.
        ``".py"``, ``".md"``.
    :returns: A list of chunk dictionaries.  Returns an empty list
        for unsupported extensions.
    """
    if ext in SOURCE_EXTENSIONS:
        language = SOURCE_EXTENSIONS[ext]
        if language == "python":
            return parse_python(filepath)
        elif TREE_SITTER_AVAILABLE and language in LANG_NAMES:
            chunks = parse_with_tree_sitter(filepath, language)
            if chunks:
                return chunks
        # Fallback: whole file
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return [
            {
                "type": "file",
                "name": os.path.basename(filepath),
                "code": content,
                "start_line": 1,
                "end_line": 1,
            }
        ]
    elif ext in DOCUMENT_EXTENSIONS:
        if ext == ".md":
            return parse_markdown(filepath)
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return [
                {
                    "type": "document",
                    "name": os.path.basename(filepath),
                    "code": content,
                    "start_line": 1,
                    "end_line": 1,
                }
            ]
    elif ext in OFFICE_EXTENSIONS:
        if ext == ".pdf":
            return parse_pdf(filepath)
        elif ext == ".docx":
            return parse_docx(filepath)
        else:
            return []
    elif ext in CONFIG_EXTENSIONS:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return [
            {
                "type": "config",
                "name": os.path.basename(filepath),
                "code": content,
                "start_line": 1,
                "end_line": 1,
            }
        ]
    else:
        return []


# ----------------------------------------------------------------------
# Ingest function
# ----------------------------------------------------------------------

def ingest_directory(path: str, db_store: str) -> None:
    """Walk a directory tree, parse supported files, and upsert chunks
    into the ChromaDB vector store.

    The ingestion process:

    1. Walk the directory tree, skipping ``.git``, ``node_modules``,
       ``__pycache__``, and ``.venv`` directories.
    2. Skip binary files (detected via :func:`is_binary`).
    3. For each supported file extension, call :func:`parse_file` to
       obtain structured semantic chunks.
    4. Collect all chunks into a batch and call
       :meth:`chromadb.Collection.upsert` to store them in the
       ``"agentern_codebase"`` collection.

    .. warning::

       The ``SOURCE_PATH`` environment variable must be set before
       starting the application.  If it is empty or unset, this
       function is never called and the vector store remains empty.

    :param path: Root directory to ingest.  All supported files
        under this directory (recursively) will be processed.
    :param db_store: Path to the ChromaDB database.
    """
    from vector import VectorStore

    store = VectorStore(db_store)
    repo_name = os.path.basename(os.path.abspath(path))

    all_chunks = []

    for root, dirs, files in os.walk(path):
        dirs[:] = [
            d
            for d in dirs
            if d not in (".git", "node_modules", "__pycache__", ".venv")
        ]
        for file in files:
            filepath = os.path.join(root, file)
            if is_binary(filepath):
                print(f"Skipping binary: {filepath}")
                continue

            relpath = os.path.relpath(filepath, path)
            ext = os.path.splitext(file)[1].lower()

            if ext in SOURCE_EXTENSIONS:
                language = SOURCE_EXTENSIONS[ext]
                file_type = "source"
            elif ext in DOCUMENT_EXTENSIONS:
                language = DOCUMENT_EXTENSIONS[ext]
                file_type = "document"
            elif ext in OFFICE_EXTENSIONS:
                language = OFFICE_EXTENSIONS[ext]
                file_type = "office"
            elif ext in CONFIG_EXTENSIONS:
                language = CONFIG_EXTENSIONS[ext]
                file_type = "config"
            else:
                print(f"Skipping unsupported: {filepath}")
                continue

            try:
                chunks = parse_file(filepath, ext)
            except Exception as e:
                print(f"Error parsing {filepath}: {e}")
                continue

            if not chunks:
                continue

            for idx, chunk in enumerate(chunks):
                metadata = {
                    "repo": repo_name or "",
                    "file": relpath or "",
                    "filename": file or "",
                    "extension": ext or "",
                    "language": language or "",
                    "file_type": file_type or "",
                    "chunk_type": chunk.get("type", "unknown") or "unknown",
                    "symbol": chunk.get("name", "") or "",
                    "parent": chunk.get("parent", "") or "",
                    "start_line": chunk.get("start_line", 1) or 1,
                    "end_line": chunk.get("end_line", 1) or 1,
                }
                doc_text = chunk.get("code", "")
                if not doc_text:
                    continue

                id_str = f"{repo_name}:{relpath}:{chunk.get('type','')}:{chunk.get('name','')}:{idx}"
                doc_id = hashlib.md5(id_str.encode("utf-8")).hexdigest()

                all_chunks.append({
                    "document": doc_text,
                    "metadata": metadata,
                    "id": doc_id,
                })

    if all_chunks:
        documents = [c["document"] for c in all_chunks]
        metadatas = [c["metadata"] for c in all_chunks]
        ids = [c["id"] for c in all_chunks]
        store.collection.upsert(
            documents=documents, metadatas=metadatas, ids=ids
        )
        print(f"Successfully ingested {len(all_chunks)} chunks from {path}.")
    else:
        print("No valid chunks found to ingest.")


# ----------------------------------------------------------------------
# Command-line entry
# ----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest a directory tree into a ChromaDB vector database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --document_path=/path/to/code                    \n"
            "  %(prog)s --document_path=. --chroma_path=./chroma_data    \n"
        ),
    )

    parser.add_argument(
        "--document_path",
        type=str,
        required=True,
        help=(
            "Root directory to scan and ingest.  All supported files "
            "(.py, .js, .ts, .md, .pdf, .yaml, .json, etc.) under this "
            "tree will be parsed into semantic chunks and stored in the "
            "vector database."
        ),
        metavar="PATH",
    )

    parser.add_argument(
        "--chroma_path",
        type=str,
        required=True,
        help=(
            "Filesystem path where the ChromaDB persistent database "
            "will be created or updated.  Ensure you have sufficient "
            "disk space for the embedding index."
        ),
        metavar="PATH",
    )

    args = parser.parse_args()

    document_path = os.path.abspath(args.document_path)
    chroma_path = os.path.abspath(args.chroma_path)

    if not os.path.isdir(document_path):
        parser.error(
            f"document_path does not exist or is not a directory: "
            f"{document_path}"
        )

    print(f"Document path : {document_path}")
    print(f"Chroma path   : {chroma_path}")
    print()
    print("Scanning and chunking files.  This may take a few minutes...")
    print()

    ingest_directory(path=document_path, db_store=chroma_path)

    print()
    print("Done.  The vector store is ready for queries.")