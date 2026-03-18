from app.ai.constants.embedding_fields import EMBEDDING_FIELDS
from app.ai.utils.helpers import normalize_text


def has_meaningful_change(old_student, updated_data):
    for field in EMBEDDING_FIELDS:
        old_val = normalize_text(getattr(old_student, field, ""))
        new_val = normalize_text(updated_data.get(field, old_val))

        if old_val != new_val:
            return True
    return False
