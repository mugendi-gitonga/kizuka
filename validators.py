from django.core.validators import RegexValidator


NUMERIC_ONLY = RegexValidator(
    regex=r"^([\s\d]+)$",
    message=(
        "Only numbers is required. Remove space and any other non-numeric character"
    ),
)

ALPHANUMERIC_ONLY = RegexValidator(
    regex=r"^[a-zA-Z0-9-_: ]+$",
    message=(
        "Only numbers, letters, underscores, dashes and spaces are allowed. Remove new lines, tabs, commas, fullstops if any and use - or _ instead."
    ),
)

ALPHANNUMERIC_WITH_FWD_SLASH_ONLY = RegexValidator(
    regex=r"^[a-zA-Z0-9-_/ ]+$",
    message=(
        "Only numbers, letters, underscores, dashes, forward slash, and spaces are allowed. Remove new lines, tabs, commas, fullstops if any and use - or _ instead."
    ),
)

ADDRESS_VALIDATOR = RegexValidator(
    regex=r"^[a-zA-Z0-9-_ .,]+$",
    message=(
        "Only numbers, letters, underscores, commas, fullstops, dashes and spaces are allowed. Any other special character e.g @$&<?>() etc are not allowed (remove newlines and tabs too if any)."
    ),
)

FULLTEXT_VALIDATOR = RegexValidator(
    regex=r"^[^<>%;$?]+$",
    message=(
        "Only numbers, letters, underscores, commas, fullstops, newlines, tabs, dashes and spaces are allowed. Any other special character e.g %$<?>; etc are not allowed."
    ),
)

SAFEURL_VALIDATOR = RegexValidator(
    regex=r"^[a-zA-Z0-9-_./=:?# ]+$",
    message=("URL format is not allowed or contains unallowed characters e.g < ^ etc."),
)


SAFEPHONENUMBER_VALIDATOR = RegexValidator(
    regex=r"^[0-9-_+ ]+$",
    message=("Phone number format is not allowed or contains invalid characters"),
)
