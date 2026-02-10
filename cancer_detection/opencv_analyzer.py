"""
Backward compatibility module - imports from ml_analyzer
All cancer detection analysis now uses ML-based models
"""
from .ml_analyzer import CancerImageAnalyzer, MLCancerAnalyzer

__all__ = ['CancerImageAnalyzer', 'MLCancerAnalyzer']

