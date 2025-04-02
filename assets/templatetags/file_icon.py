from django import template

register = template.Library()

@register.filter
def file_icon(filename):
    ext = filename.lower().split('.')[-1]

    IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "tiff", "bmp", "webp"]
    TEXT_EXTENSIONS = ["txt", "csv"]
    HTML_EXTENSIONS = ["html", "htm"]
    ARCHIVE_EXTENSIONS = ["zip", "rar", "7z"]
    WORDPERFECT_EXTENSIONS = ["wpd", "wp", "wpt"]
    CODE_EXTENSIONS = ["py", "java", "c", "cpp", "js", "ts", "rb", "go"]
    LOTUS_EXTENSIONS = ["123"]
    PRESENTATION_EXTENSIONS = ["prz"]

    if ext in IMAGE_EXTENSIONS:
        return 'fa-file-image'
    elif ext in TEXT_EXTENSIONS:
        return 'fa-file-alt'
    elif ext in HTML_EXTENSIONS:
        return 'fa-file-code'
    elif ext in ARCHIVE_EXTENSIONS:
        return 'fa-file-archive'
    elif ext in WORDPERFECT_EXTENSIONS:
        return 'fa-file-word'
    elif ext in CODE_EXTENSIONS:
        return 'fa-file-code'
    elif ext in LOTUS_EXTENSIONS:
        return 'fa-file-excel'
    elif ext in PRESENTATION_EXTENSIONS:
        return 'fa-file-powerpoint'
    elif ext == "pdf":
        return 'fa-file-pdf'
    elif ext in ["doc", "docx"]:
        return 'fa-file-word'
    elif ext in ["xls", "xlsx"]:
        return 'fa-file-excel'
    elif ext in ["ppt", "pptx"]:
        return 'fa-file-powerpoint'
    elif ext == "rtf":
        return 'fa-file-alt'
    elif ext in ["eml", "msg"]:
        return 'fa-envelope'
    elif ext in ["odt", "ods", "odp"]:
        return 'fa-file-lines'
    else:
        return 'fa-folder'
