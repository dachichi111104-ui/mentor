import unicodedata

def remove_vietnamese_accents(text: str) -> str:
    """
    Strips Vietnamese diacritical marks and converts Đ/đ to D/d.
    """
    if not text:
        return ""
    text = str(text).replace('Đ', 'D').replace('đ', 'd')
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents

def generate_mentor_email(first_name: str, last_name: str, full_name: str = "") -> str:
    """
    Generates mentor email according to rule:
    <tên><chữ cái đầu của họ và tên đệm>@vaa.edu.vn
    Example: Nguyễn Lương Anh Tuấn -> tuannla@vaa.edu.vn
    """
    if not full_name:
        fn = (first_name or "").strip()
        ln = (last_name or "").strip()
        full_name = f"{fn} {ln}".strip()
    
    words = full_name.split()
    if not words:
        return "mentor@vaa.edu.vn"

    ten = words[-1]
    ho_dem = words[:-1]

    ten_ascii = remove_vietnamese_accents(ten).lower()
    ho_dem_initials = "".join(remove_vietnamese_accents(w)[0].lower() for w in ho_dem if w)

    return f"{ten_ascii}{ho_dem_initials}@vaa.edu.vn"

def generate_student_email(student_id: str, username: str = "") -> str:
    """
    Generates student email according to rule:
    <mssv>@vaa.edu.vn
    Example: 2431540114 -> 2431540114@vaa.edu.vn
    """
    sid = str(student_id).strip() if student_id else str(username).strip()
    sid_ascii = remove_vietnamese_accents(sid).lower()
    return f"{sid_ascii}@vaa.edu.vn"
