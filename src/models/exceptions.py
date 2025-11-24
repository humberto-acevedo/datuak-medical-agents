"""Custom exceptions for the medical record analysis system."""


class MedicalAnalysisError(Exception):
    """Base exception for medical analysis system."""
    pass


class PatientNotFoundError(MedicalAnalysisError):
    """Raised when a patient record cannot be found."""
    pass


class XMLParsingError(MedicalAnalysisError):
    """Raised when XML parsing fails."""
    pass


class DataValidationError(MedicalAnalysisError):
    """Raised when data validation fails."""
    pass


class S3Error(MedicalAnalysisError):
    """Raised when S3 operations fail."""
    pass


class ResearchError(MedicalAnalysisError):
    """Raised when research correlation fails."""
    pass


class AgentCommunicationError(MedicalAnalysisError):
    """Raised when agent-to-agent communication fails."""
    pass


class HallucinationDetectedError(MedicalAnalysisError):
    """Raised when potential hallucination is detected in extracted data."""
    pass


class ReportError(MedicalAnalysisError):
    """Raised when report generation fails."""
    pass