from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredPowerPointLoader

def get_file_type(filename, content):
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf' and content[:4] == b'%PDF':
        return 'pdf'
    elif ext == 'docx':
        return 'docx'
    elif ext in ['ppt', 'pptx']:
        return 'ppt'
    else:
        return 'unknown'

def process_file(filename, content):
    file_type = get_file_type(filename, content)
    if file_type == 'pdf':
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name
        try:
            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
        finally:
            import os
            os.remove(tmp_path)
        return pages
    elif file_type == 'docx':
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name
        try:
            loader = UnstructuredWordDocumentLoader(tmp_path)
            pages = loader.load()
        finally:
            import os
            os.remove(tmp_path)
        return pages
    elif file_type == 'ppt':
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name
        try:
            loader = UnstructuredPowerPointLoader(tmp_path)
            pages = loader.load()
        finally:
            import os
            os.remove(tmp_path)
        return pages
    elif file_type == 'txt':
        text = content.decode('utf-8')
        ...
    elif file_type == 'xlsx':
        ...
    else:
        raise ValueError("Unsupported file type") 