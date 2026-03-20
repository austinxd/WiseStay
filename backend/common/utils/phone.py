import phonenumbers


def normalize_phone(phone: str, default_region: str = "US") -> str:
    """Normalize a phone number to E.164 format."""
    parsed = phonenumbers.parse(phone, default_region)
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {phone}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
