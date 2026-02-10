from django.urls import path
from . import views
from . import evidence_views
from . import evidence_web_views

app_name = 'cancer_detection'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_image, name='upload_image'),
    path('analyses/', views.analysis_list, name='analysis_list'),
    path('analyses/<uuid:analysis_id>/', views.analysis_detail, name='analysis_detail'),
    path('analyses/<uuid:analysis_id>/delete/', views.delete_analysis, name='delete_analysis'),
    path('analyses/<uuid:analysis_id>/treatment-plan/', views.generate_treatment_plan, name='generate_treatment_plan'),
    path('treatment-plans/', views.treatment_plans_list, name='treatment_plans_list'),
    path('treatment-plans/<uuid:plan_id>/', views.treatment_plan_detail, name='treatment_plan_detail'),
    path('treatment-plans/<uuid:plan_id>/submit-review/', views.submit_treatment_plan_review, name='submit_treatment_plan_review'),
    
    # Histopathology Reports
    path('histopathology/upload/', views.upload_histopathology_report, name='upload_histopathology'),
    path('histopathology/', views.histopathology_reports_list, name='histopathology_list'),
    path('histopathology/<uuid:report_id>/', views.histopathology_report_detail, name='histopathology_detail'),
    
    # Genomic Profiles
    path('genomics/upload/', views.upload_genomic_profile, name='upload_genomic'),
    path('genomics/', views.genomic_profiles_list, name='genomic_list'),
    path('genomics/<uuid:profile_id>/', views.genomic_profile_detail, name='genomic_detail'),
    
    # Combined Data Analysis
    path('data-analysis/', views.combined_data_analysis, name='combined_data_analysis'),

    # Combined Hub Pages
    path('image-hub/', views.image_hub, name='image_hub'),
    path('pathology-hub/', views.pathology_hub, name='pathology_hub'),
    path('genomics-hub/', views.genomics_hub, name='genomics_hub'),
    
    # Comprehensive Treatment Planning
    path('comprehensive-plan/', views.create_comprehensive_plan, name='create_comprehensive_plan'),
    path('treatment-plans/<uuid:plan_id>/visualize/', views.visualize_treatment_pathway, name='visualize_pathway'),
    path('treatment-plans/<uuid:plan_id>/decision-support/', views.decision_support, name='decision_support'),
    
    # Evidence Traceability Engine - API Endpoints
    path('api/evidence/explain/<uuid:treatment_plan_id>/', evidence_views.explain_recommendation, name='explain_recommendation'),
    path('api/evidence/explain/<uuid:treatment_plan_id>/<uuid:rec_evidence_id>/', evidence_views.explain_recommendation, name='explain_specific_recommendation'),
    path('api/evidence/recommendations/<uuid:treatment_plan_id>/', evidence_views.get_recommendation_with_evidence, name='get_recommendations_with_evidence'),
    path('api/evidence/source/<uuid:evidence_id>/', evidence_views.get_evidence_source_detail, name='get_evidence_detail'),
    path('api/evidence/feedback/<uuid:treatment_plan_id>/<uuid:rec_evidence_id>/', evidence_views.log_explanation_feedback, name='log_feedback'),
    path('api/evidence/search/', evidence_views.search_evidence, name='search_evidence'),
    path('api/evidence/rule-reference/', evidence_views.create_rule_based_reference, name='create_rule_reference'),
    path('api/evidence/decision-factors/<uuid:treatment_plan_id>/<uuid:rec_evidence_id>/', evidence_views.get_patient_decision_factors, name='decision_factors'),
    path('api/evidence/init/', evidence_views.initialize_evidence_database, name='init_evidence'),
    path('api/evidence/ingest-studies/', evidence_views.search_and_ingest_studies, name='ingest_studies'),
    path('api/evidence/history/<uuid:treatment_plan_id>/', evidence_views.get_explanation_history, name='explanation_history'),
    
    # Evidence Traceability Engine - HTML Views (Web UI)
    path('treatment-plans/<uuid:plan_id>/evidence/', evidence_web_views.treatment_plan_with_evidence, name='treatment_plan_with_evidence'),
    path('treatment-plans/<uuid:plan_id>/evidence/explain/<uuid:rec_evidence_id>/', evidence_web_views.evidence_explanation_detail, name='evidence_explanation_detail'),
    path('treatment-plans/<uuid:plan_id>/evidence/factors/<uuid:rec_evidence_id>/', evidence_web_views.decision_factors_breakdown, name='decision_factors_breakdown'),
    path('treatment-plans/<uuid:plan_id>/evidence/statistics/', evidence_web_views.evidence_statistics, name='evidence_statistics'),
    path('treatment-plans/<uuid:plan_id>/evidence/audit/', evidence_web_views.evidence_audit_trail, name='evidence_audit_trail'),
    path('treatment-plans/<uuid:plan_id>/evidence/feedback/<uuid:rec_evidence_id>/', evidence_web_views.submit_explanation_feedback, name='submit_explanation_feedback'),
    path('evidence/search/', evidence_web_views.evidence_search, name='evidence_search'),
    path('evidence/source/<uuid:source_id>/', evidence_web_views.evidence_source_detail, name='evidence_source_detail'),
    path('evidence/rules/', evidence_web_views.rule_based_references_view, name='rule_based_references_view'),

]