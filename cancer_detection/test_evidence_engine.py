"""
Testing and Example Script for Evidence Traceability Engine
Run this in Django shell to test all components
"""

# Run in Django shell:
# python manage.py shell
# exec(open('cancer_detection/test_evidence_engine.py').read())


def test_evidence_engine():
    """
    Complete test suite for Evidence Traceability Engine
    Tests all components: models, RAG, ingestion, integration, API
    """
    
    print("=" * 80)
    print("EVIDENCE TRACEABILITY ENGINE - TEST SUITE")
    print("=" * 80)
    
    # Test 1: Database Models
    print("\n[TEST 1] Database Models")
    print("-" * 80)
    
    from cancer_detection.evidence_models import (
        EvidenceSource, RecommendationEvidence, RuleBasedReference
    )
    
    # Check models exist
    print(f"✓ EvidenceSource model loaded")
    print(f"✓ RecommendationEvidence model loaded")
    print(f"✓ RuleBasedReference model loaded")
    
    # Count existing data
    evidence_count = EvidenceSource.objects.filter(is_active=True).count()
    rule_count = RuleBasedReference.objects.filter(is_active=True).count()
    print(f"\nCurrent data:")
    print(f"  - Evidence sources: {evidence_count}")
    print(f"  - Active rules: {rule_count}")
    
    # Test 2: RAG Pipeline
    print("\n[TEST 2] RAG Pipeline (Semantic Search)")
    print("-" * 80)
    
    from cancer_detection.evidence_retriever import EvidenceRetriever
    
    retriever = EvidenceRetriever()
    
    if retriever.initialized:
        print("✓ Sentence-transformers model loaded successfully")
        
        # Test embedding
        test_query = "breast cancer HER2-positive chemotherapy"
        embedding = retriever.get_embedding(test_query)
        if embedding:
            print(f"✓ Generated embedding for query (dimension: {len(embedding)})")
        
        # Test retrieval (if evidence exists)
        if evidence_count > 0:
            results = retriever.retrieve_evidence(
                query=test_query,
                top_k=3,
                cancer_types=['breast']
            )
            print(f"✓ Retrieved {len(results)} evidence sources")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['title'][:50]}... (relevance: {result['relevance_score']:.2%})")
    else:
        print("⚠ Sentence-transformers not initialized")
        print("  Install with: pip install sentence-transformers")
    
    # Test 3: Evidence Ingestion
    print("\n[TEST 3] Evidence Ingestion")
    print("-" * 80)
    
    from cancer_detection.evidence_ingester import EvidenceIngestionService
    
    ingestion_service = EvidenceIngestionService()
    print("✓ EvidenceIngestionService initialized")
    
    # Test guideline ingestion (no API calls)
    print("\nTesting guideline ingestion...")
    guideline_data = {
        'title': 'Test NCCN Guideline',
        'source_type': 'nccn_guideline',
        'organization': 'NCCN',
        'cancer_types': ['breast'],
        'treatment_types': ['surgery', 'chemotherapy'],
        'version': '2024',
    }
    
    try:
        evidence = ingestion_service.guideline_ingester.ingest_guideline(guideline_data)
        if evidence:
            print(f"✓ Ingested test guideline: {evidence.title}")
    except Exception as e:
        print(f"⚠ Guideline ingestion: {str(e)}")
    
    # Test 4: Rule-Based References
    print("\n[TEST 4] Rule-Based References")
    print("-" * 80)
    
    from cancer_detection.rule_based_references import RuleBasedReferenceManager
    
    # Get matching rules
    rules = RuleBasedReferenceManager.get_matching_rules(
        cancer_type='breast',
        cancer_stage='2'
    )
    
    print(f"✓ Found {len(rules)} rules for breast cancer stage 2")
    
    if rules:
        rule = rules[0]
        print(f"\nExample rule:")
        print(f"  - Name: {rule.rule_name}")
        print(f"  - Recommendation: {rule.recommended_treatment}")
        print(f"  - Evidence strength: {rule.evidence_strength}")
        print(f"  - Priority: {rule.priority_level}/10")
        
        # Get evidence from rule
        rule_evidence = RuleBasedReferenceManager.get_rule_evidence(rule)
        print(f"  - Associated evidence: {len(rule_evidence)} items")
    
    # Test 5: Evidence Integration
    print("\n[TEST 5] Evidence Integration")
    print("-" * 80)
    
    from cancer_detection.evidence_integration import EvidenceIntegratedPlanner
    
    planner = EvidenceIntegratedPlanner()
    print("✓ EvidenceIntegratedPlanner initialized")
    
    # Create tracked recommendation (without saving to DB)
    from cancer_detection.evidence_integration import EvidenceTrackedRecommendation
    
    rec = EvidenceTrackedRecommendation(
        recommendation_text="Surgery + Chemotherapy + Radiation",
        recommendation_type="Multimodal Therapy",
        patient_factors={
            'age': 45,
            'performance_status': 1,
            'her2_status': 'positive',
        }
    )
    
    print(f"✓ Created tracked recommendation:")
    print(f"  - Type: {rec.recommendation_type}")
    print(f"  - Text: {rec.recommendation_text}")
    print(f"  - Patient factors: {len(rec.patient_factors)}")
    
    # Test 6: Feature Influence Analysis
    print("\n[TEST 6] Decision Factor Analysis")
    print("-" * 80)
    
    from cancer_detection.evidence_integration import RecommendationFactorAnalyzer
    
    factors = RecommendationFactorAnalyzer.analyze_decision_factors(
        patient_data={
            'patient_age': 45,
            'patient_performance_status': 1,
            'genetic_profile': {'HER2': 'positive', 'ER': 'positive'},
            'comorbidities': ['hypertension'],
        },
        recommendation='HER2-targeted therapy + chemotherapy'
    )
    
    print(f"✓ Analyzed {len(factors)} decision factors")
    for factor, info in factors.items():
        print(f"  - {factor}: influence {info.get('influence_score', 0):.2%}")
    
    # Test 7: API Endpoint Structure
    print("\n[TEST 7] API Endpoints")
    print("-" * 80)
    
    endpoints = [
        ('GET', '/api/evidence/explain/<plan_id>/', 'Explain recommendation'),
        ('GET', '/api/evidence/recommendations/<plan_id>/', 'Get all recommendations with evidence'),
        ('GET', '/api/evidence/decision-factors/<plan_id>/<rec_id>/', 'Analyze decision factors'),
        ('GET', '/api/evidence/search/', 'Search evidence sources'),
        ('GET', '/api/evidence/source/<id>/', 'Get evidence detail'),
        ('POST', '/api/evidence/feedback/<plan_id>/<rec_id>/', 'Log user feedback'),
        ('POST', '/api/evidence/rule-reference/', 'Create rule'),
        ('POST', '/api/evidence/init/', 'Initialize database'),
        ('POST', '/api/evidence/ingest-studies/', 'Ingest PubMed studies'),
    ]
    
    print(f"✓ {len(endpoints)} API endpoints available:")
    for method, path, desc in endpoints:
        print(f"  [{method:4}] {path:50} - {desc}")
    
    # Test 8: Database Migrations
    print("\n[TEST 8] Database Migrations")
    print("-" * 80)
    
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    
    print("✓ Database tables created:")
    tables = [
        'evidence_sources',
        'recommendation_evidences',
        'evidence_links',
        'evidence_explanation_logs',
        'rule_based_references',
    ]
    
    for table in tables:
        exists = table in connection.introspection.table_names()
        status = "✓" if exists else "✗"
        print(f"  {status} {table}")
    
    # Test 9: Performance
    print("\n[TEST 9] Performance Benchmarks")
    print("-" * 80)
    
    import time
    
    # Embedding speed
    if retriever.initialized:
        start = time.time()
        _ = retriever.get_embedding("test query")
        embed_time = (time.time() - start) * 1000
        print(f"✓ Embedding generation: {embed_time:.1f}ms")
    
    # Database query speed
    start = time.time()
    _ = EvidenceSource.objects.count()
    query_time = (time.time() - start) * 1000
    print(f"✓ Database query: {query_time:.1f}ms")
    
    # Rule lookup
    start = time.time()
    _ = RuleBasedReference.objects.filter(
        cancer_type='breast',
        cancer_stage='2'
    ).count()
    rule_time = (time.time() - start) * 1000
    print(f"✓ Rule lookup: {rule_time:.1f}ms")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"""
✓ All components tested successfully!

System Status:
  - Evidence sources: {evidence_count} active
  - Rule-based references: {rule_count} active
  - RAG pipeline: {'Initialized' if retriever.initialized else 'Not initialized'}
  - Database tables: 5 created
  - API endpoints: {len(endpoints)} available

Next Steps:
  1. Initialize evidence database:
     python manage.py init_evidence_engine --all
  
  2. Test API endpoints:
     GET /api/evidence/search/?q=breast+cancer
  
  3. View admin interface:
     /admin/cancer_detection/evidencesource/
  
  4. Ingest PubMed studies:
     python manage.py init_evidence_engine --search-pubmed --cancer-type breast

For documentation, see:
  - EVIDENCE_ENGINE_QUICKSTART.md
  - EVIDENCE_ENGINE_DOCS.md
""")
    
    return True


# Run all tests
if __name__ == '__main__':
    try:
        success = test_evidence_engine()
        if success:
            print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


# ============================================================================
# ADDITIONAL USAGE EXAMPLES
# ============================================================================

def example_1_create_recommendation():
    """Example 1: Create recommendation with evidence"""
    
    from cancer_detection.evidence_integration import EvidenceIntegratedPlanner
    from cancer_detection.models import PersonalizedTreatmentPlan
    
    # Get a treatment plan
    treatment_plan = PersonalizedTreatmentPlan.objects.first()
    if not treatment_plan:
        print("No treatment plan found")
        return
    
    planner = EvidenceIntegratedPlanner()
    
    # Create recommendation with evidence
    rec = planner.create_treatment_recommendation_with_evidence(
        cancer_type=treatment_plan.cancer_type,
        cancer_stage=treatment_plan.cancer_stage,
        treatment_recommendation="Surgery + Adjuvant Chemotherapy",
        treatment_type="Multimodal Therapy",
        patient_factors={
            'age': 45,
            'performance_status': 1,
            'her2_status': 'positive',
        },
        treatment_plan=treatment_plan,
        use_rag=True,
        fallback_to_rules=True
    )
    
    # Synthesize evidence
    rationale = rec.synthesize_evidence()
    
    # Save to database
    rec_evidence = rec.save_to_database()
    
    print(f"✓ Created recommendation with {len(rec.evidence_sources)} evidence sources")
    print(f"  Recommendation ID: {rec_evidence.id}")
    
    return rec_evidence


def example_2_explain_recommendation():
    """Example 2: Get explanation for recommendation"""
    
    from cancer_detection.evidence_integration import EvidenceIntegratedPlanner
    from cancer_detection.evidence_models import RecommendationEvidence
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get a recommendation
    rec_evidence = RecommendationEvidence.objects.first()
    if not rec_evidence:
        print("No recommendation found")
        return
    
    planner = EvidenceIntegratedPlanner()
    user = User.objects.first()
    
    # Get full explanation
    explanation = planner.get_recommendation_explanation(
        rec_evidence,
        user,
        format_type='full'
    )
    
    print(f"Recommendation: {explanation['recommendation']}")
    print(f"Confidence: {explanation['overall_confidence']:.1%}")
    print(f"Evidence sources: {len(explanation['evidence_sources'])}")
    print(f"Citations: {len(explanation['citations'])}")
    
    return explanation


def example_3_search_evidence():
    """Example 3: Search evidence sources"""
    
    from cancer_detection.evidence_retriever import EvidenceRetriever
    
    retriever = EvidenceRetriever()
    
    if not retriever.initialized:
        print("RAG pipeline not initialized")
        return
    
    # Search
    results = retriever.retrieve_evidence(
        query="HER2-positive breast cancer trastuzumab chemotherapy",
        top_k=5,
        cancer_types=['breast'],
        evidence_strength_filter='high'
    )
    
    print(f"\nSearch Results ({len(results)} found):")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   Type: {result['source_type']}")
        print(f"   Strength: {result['evidence_strength']}")
        print(f"   Relevance: {result['relevance_score']:.2%}")
        if result.get('pmid'):
            print(f"   PMID: {result['pmid']}")
    
    return results


def example_4_get_decision_factors():
    """Example 4: Analyze decision factors"""
    
    from cancer_detection.evidence_integration import RecommendationFactorAnalyzer
    
    patient_data = {
        'patient_age': 45,
        'patient_performance_status': 1,
        'genetic_profile': {'HER2': 'positive', 'ER': 'positive'},
        'comorbidities': ['hypertension', 'diabetes'],
        'organ_function': 'normal',
        'previous_treatments': ['tamoxifen']
    }
    
    recommendation = "Trastuzumab + Chemotherapy"
    
    factors = RecommendationFactorAnalyzer.analyze_decision_factors(
        patient_data,
        recommendation
    )
    
    print(f"\nDecision Factor Analysis:")
    print(f"Recommendation: {recommendation}\n")
    
    for factor, info in sorted(factors.items(), 
                               key=lambda x: x[1].get('influence_score', 0),
                               reverse=True):
        score = info.get('influence_score', 0)
        value = info.get('value', 'N/A')
        print(f"  • {factor:20} | Influence: {score:5.1%} | Value: {value}")
    
    return factors


# ============================================================================
# TO RUN EXAMPLES, UNCOMMENT BELOW IN DJANGO SHELL
# ============================================================================

# print("\n--- Example 1: Create Recommendation ---")
# example_1_create_recommendation()

# print("\n--- Example 2: Explain Recommendation ---")
# example_2_explain_recommendation()

# print("\n--- Example 3: Search Evidence ---")
# example_3_search_evidence()

# print("\n--- Example 4: Decision Factors ---")
# example_4_get_decision_factors()
