from enum import IntEnum, StrEnum


class ForecastHorizon(IntEnum):
    DAYS_7 = 7
    DAYS_15 = 15
    DAYS_30 = 30


class ForecastModel(StrEnum):
    RANDOM_FOREST = "random_forest"
    BASELINE = "baseline"


class SalesUploadDuplicatePolicy(StrEnum):
    REJECT = "reject"
    ALLOW = "allow"
    MARK_DUPLICATE = "mark_duplicate"


class SalesUploadDateFormat(StrEnum):
    YYYY_MM_DD = "yyyy-mm-dd"
    DD_MM_YYYY = "dd-mm-yyyy"
    MM_DD_YYYY = "mm-dd-yyyy"


class ReportDefaultFormat(StrEnum):
    JSON = "json"
    CSV = "csv"


class SettingsCategory(StrEnum):
    FORECAST = "forecast"
    INVENTORY = "inventory"
    SALES_UPLOAD = "sales_upload"
    REPORTS = "reports"
    DASHBOARD = "dashboard"
    BACKGROUND_JOBS = "background_jobs"
    LOCALIZATION = "localization"


class LocaleOption(StrEnum):
    EN = "en"
    EN_IN = "en-IN"
    HI_IN = "hi-IN"
