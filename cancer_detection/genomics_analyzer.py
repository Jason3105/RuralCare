"""
Advanced Genomics Analyzer
Analyzes genetic mutations, biomarkers, and genomic profiles to determine
treatment eligibility and prognosis
"""

from typing import Dict, List, Optional
from datetime import datetime
import json


class GenomicsAnalyzer:
    """
    Advanced genomics analysis for personalized cancer treatment
    Analyzes mutations, biomarkers, and genomic profiles
    """
    
    # Known actionable mutations and their targeted therapies
    ACTIONABLE_MUTATIONS = {
        'EGFR': {
            'mutations': ['L858R', 'exon19del', 'G719X', 'L861Q', 'S768I'],
            'therapies': ['Gefitinib', 'Erlotinib', 'Afatinib', 'Osimertinib'],
            'indication': 'NSCLC',
            'prognosis_impact': 'favorable',
        },
        'ALK': {
            'mutations': ['fusion', 'rearrangement', 'EML4-ALK'],
            'therapies': ['Crizotinib', 'Alectinib', 'Brigatinib', 'Lorlatinib'],
            'indication': 'NSCLC',
            'prognosis_impact': 'favorable',
        },
        'HER2': {
            'mutations': ['amplification', 'overexpression', '3+'],
            'therapies': ['Trastuzumab', 'Pertuzumab', 'T-DM1', 'Lapatinib'],
            'indication': 'Breast, Gastric',
            'prognosis_impact': 'variable',
        },
        'BRAF': {
            'mutations': ['V600E', 'V600K'],
            'therapies': ['Vemurafenib', 'Dabrafenib', 'Trametinib'],
            'indication': 'Melanoma, Colorectal, NSCLC',
            'prognosis_impact': 'variable',
        },
        'KRAS': {
            'mutations': ['G12C', 'G12D', 'G12V'],
            'therapies': ['Sotorasib (G12C)', 'Adagrasib (G12C)'],
            'indication': 'NSCLC, Colorectal',
            'prognosis_impact': 'unfavorable',
        },
        'BRCA1': {
            'mutations': ['pathogenic', 'deleterious'],
            'therapies': ['PARP inhibitors (Olaparib, Talazoparib)'],
            'indication': 'Breast, Ovarian, Prostate',
            'prognosis_impact': 'variable',
        },
        'BRCA2': {
            'mutations': ['pathogenic', 'deleterious'],
            'therapies': ['PARP inhibitors (Olaparib, Talazoparib)'],
            'indication': 'Breast, Ovarian, Prostate',
            'prognosis_impact': 'variable',
        },
        'PD-L1': {
            'mutations': ['high expression', 'TPS >= 50%', 'CPS >= 10'],
            'therapies': ['Pembrolizumab', 'Atezolizumab', 'Durvalumab'],
            'indication': 'Multiple cancers',
            'prognosis_impact': 'favorable',
        },
        'MSI-H': {
            'mutations': ['high', 'MSI-H', 'dMMR'],
            'therapies': ['Pembrolizumab', 'Nivolumab'],
            'indication': 'Colorectal, Endometrial, Multiple',
            'prognosis_impact': 'favorable',
        },
        'NTRK': {
            'mutations': ['fusion', 'rearrangement'],
            'therapies': ['Larotrectinib', 'Entrectinib'],
            'indication': 'Pan-cancer',
            'prognosis_impact': 'favorable',
        },
    }
    
    # Prognostic markers
    PROGNOSTIC_MARKERS = {
        'favorable': ['BRCA1/2 (for PARPi)', 'MSI-H', 'PD-L1 high', 'EGFR mutation'],
        'unfavorable': ['TP53 mutation', 'KRAS mutation (non-G12C)', 'Low TMB'],
        'variable': ['HER2 amplification', 'PIK3CA mutation'],
    }
    
    def __init__(self):
        """Initialize the genomics analyzer"""
        self.analysis_results = {}
    
    def analyze_genomic_profile(self, genomic_data: Dict) -> Dict:
        """
        Comprehensive genomic profile analysis
        
        Args:
            genomic_data: Dictionary containing:
                - mutations: Dict of mutation names and status
                - biomarkers: Dict of biomarker results
                - tmb: Tumor mutational burden
                - msi_status: MSI status
                - pd_l1_status: PD-L1 status
                - copy_number_variations: CNV data
                
        Returns:
            Comprehensive genomic analysis
        """
        mutations = genomic_data.get('mutations', {})
        biomarkers = genomic_data.get('biomarkers', {})
        
        analysis = {
            'actionable_mutations': self._identify_actionable_mutations(mutations),
            'targeted_therapy_eligibility': self._assess_targeted_therapy_eligibility(mutations, biomarkers),
            'immunotherapy_eligibility': self._assess_immunotherapy_eligibility(genomic_data),
            'prognostic_profile': self._assess_prognosis(genomic_data),
            'resistance_markers': self._identify_resistance_markers(mutations),
            'treatment_recommendations': self._generate_genomic_recommendations(genomic_data),
            'clinical_trial_eligibility': self._assess_trial_eligibility(genomic_data),
            'risk_assessment': self._calculate_genomic_risk(genomic_data),
            'analysis_date': datetime.now().isoformat(),
        }
        
        return analysis
    
    def _identify_actionable_mutations(self, mutations: Dict) -> List[Dict]:
        """Identify actionable mutations with treatment implications"""
        actionable = []
        
        for gene, mutation_info in mutations.items():
            gene_upper = gene.upper()
            
            if gene_upper in self.ACTIONABLE_MUTATIONS:
                action_info = self.ACTIONABLE_MUTATIONS[gene_upper]
                
                # Check if mutation matches known actionable variants
                mutation_value = str(mutation_info).lower() if not isinstance(mutation_info, bool) else ''
                is_actionable = False
                
                if isinstance(mutation_info, bool) and mutation_info:
                    is_actionable = True
                elif any(mut in mutation_value for mut in action_info['mutations']):
                    is_actionable = True
                
                if is_actionable:
                    actionable.append({
                        'gene': gene_upper,
                        'mutation': mutation_info,
                        'therapies': action_info['therapies'],
                        'indication': action_info['indication'],
                        'prognosis_impact': action_info['prognosis_impact'],
                        'priority': 'high' if gene_upper in ['EGFR', 'ALK', 'BRAF', 'HER2'] else 'medium',
                    })
        
        return actionable
    
    def _assess_targeted_therapy_eligibility(self, mutations: Dict, biomarkers: Dict) -> Dict:
        """Assess eligibility for targeted therapies"""
        eligible_therapies = []
        eligibility_score = 0
        
        # Check for EGFR mutations
        if mutations.get('EGFR') or biomarkers.get('EGFR'):
            eligible_therapies.append({
                'therapy_class': 'EGFR Inhibitors',
                'drugs': ['Gefitinib', 'Erlotinib', 'Afatinib', 'Osimertinib'],
                'indication': 'NSCLC with EGFR mutation',
                'evidence_level': 'Level 1',
            })
            eligibility_score += 30
        
        # Check for ALK rearrangements
        if mutations.get('ALK') or biomarkers.get('ALK'):
            eligible_therapies.append({
                'therapy_class': 'ALK Inhibitors',
                'drugs': ['Crizotinib', 'Alectinib', 'Brigatinib'],
                'indication': 'NSCLC with ALK rearrangement',
                'evidence_level': 'Level 1',
            })
            eligibility_score += 30
        
        # Check for HER2
        her2_status = biomarkers.get('HER2', '').lower()
        if 'positive' in her2_status or '3+' in str(her2_status) or mutations.get('HER2'):
            eligible_therapies.append({
                'therapy_class': 'HER2-Targeted Therapy',
                'drugs': ['Trastuzumab', 'Pertuzumab', 'T-DM1'],
                'indication': 'HER2-positive breast/gastric cancer',
                'evidence_level': 'Level 1',
            })
            eligibility_score += 25
        
        # Check for BRAF
        if mutations.get('BRAF'):
            braf_mut = str(mutations.get('BRAF', '')).upper()
            if 'V600' in braf_mut:
                eligible_therapies.append({
                    'therapy_class': 'BRAF/MEK Inhibitors',
                    'drugs': ['Vemurafenib', 'Dabrafenib', 'Trametinib'],
                    'indication': 'BRAF V600E/K mutation',
                    'evidence_level': 'Level 1',
                })
                eligibility_score += 25
        
        # Check for KRAS G12C
        if mutations.get('KRAS'):
            kras_mut = str(mutations.get('KRAS', '')).upper()
            if 'G12C' in kras_mut:
                eligible_therapies.append({
                    'therapy_class': 'KRAS G12C Inhibitors',
                    'drugs': ['Sotorasib', 'Adagrasib'],
                    'indication': 'KRAS G12C mutation',
                    'evidence_level': 'Level 1',
                })
                eligibility_score += 20
        
        # Check for BRCA
        if mutations.get('BRCA1') or mutations.get('BRCA2'):
            eligible_therapies.append({
                'therapy_class': 'PARP Inhibitors',
                'drugs': ['Olaparib', 'Talazoparib', 'Rucaparib'],
                'indication': 'BRCA1/2 mutation',
                'evidence_level': 'Level 1',
            })
            eligibility_score += 20
        
        return {
            'eligible': len(eligible_therapies) > 0,
            'eligibility_score': min(eligibility_score, 100),
            'therapies': eligible_therapies,
            'recommendation': 'Strongly consider targeted therapy' if eligible_therapies else 'Standard therapy recommended',
        }
    
    def _assess_immunotherapy_eligibility(self, genomic_data: Dict) -> Dict:
        """Assess eligibility for immunotherapy"""
        eligibility_factors = []
        score = 0
        
        # PD-L1 status
        pd_l1 = str(genomic_data.get('pd_l1_status', '')).lower()
        if 'positive' in pd_l1 or 'high' in pd_l1 or '>=50' in pd_l1:
            eligibility_factors.append('PD-L1 positive (high expression)')
            score += 40
        elif 'low' in pd_l1 or '1-49' in pd_l1:
            eligibility_factors.append('PD-L1 low/positive')
            score += 20
        
        # MSI status
        msi = str(genomic_data.get('msi_status', '')).lower()
        if 'msi-h' in msi or 'high' in msi:
            eligibility_factors.append('MSI-H/dMMR')
            score += 40
        elif 'stable' in msi or 'mss' in msi:
            eligibility_factors.append('MSS (may limit immunotherapy benefit)')
            score -= 10
        
        # Tumor Mutational Burden
        tmb = genomic_data.get('tumor_mutational_burden') or genomic_data.get('tmb')
        if isinstance(tmb, (int, float)):
            if tmb >= 20:
                eligibility_factors.append(f'High TMB ({tmb} mutations/Mb)')
                score += 30
            elif tmb >= 10:
                eligibility_factors.append(f'Intermediate TMB ({tmb} mutations/Mb)')
                score += 15
            else:
                eligibility_factors.append(f'Low TMB ({tmb} mutations/Mb)')
                score -= 10
        
        # Immune infiltration
        immune_infiltration = str(genomic_data.get('immune_infiltration', '')).lower()
        if 'high' in immune_infiltration:
            eligibility_factors.append('High immune infiltration')
            score += 20
        
        eligible = score >= 30
        
        return {
            'eligible': eligible,
            'eligibility_score': min(max(score, 0), 100),
            'factors': eligibility_factors,
            'recommendation': self._get_immunotherapy_recommendation(score),
            'preferred_agents': ['Pembrolizumab', 'Nivolumab', 'Atezolizumab'] if eligible else [],
        }
    
    def _get_immunotherapy_recommendation(self, score: int) -> str:
        """Get immunotherapy recommendation based on score"""
        if score >= 60:
            return 'Strongly recommended - First-line consideration'
        elif score >= 40:
            return 'Recommended - Consider as treatment option'
        elif score >= 20:
            return 'May be considered - Discuss with patient'
        else:
            return 'Limited benefit expected - Consider other options'
    
    def _assess_prognosis(self, genomic_data: Dict) -> Dict:
        """Assess prognostic implications"""
        mutations = genomic_data.get('mutations', {})
        biomarkers = genomic_data.get('biomarkers', {})
        
        favorable_markers = []
        unfavorable_markers = []
        
        # Check for favorable markers
        if mutations.get('BRCA1') or mutations.get('BRCA2'):
            favorable_markers.append('BRCA1/2 mutation (PARPi eligible)')
        
        msi = str(genomic_data.get('msi_status', '')).lower()
        if 'msi-h' in msi or 'high' in msi:
            favorable_markers.append('MSI-H (immunotherapy responsive)')
        
        pd_l1 = str(genomic_data.get('pd_l1_status', '')).lower()
        if 'positive' in pd_l1 or 'high' in pd_l1:
            favorable_markers.append('PD-L1 positive')
        
        # Check for unfavorable markers
        if mutations.get('TP53'):
            unfavorable_markers.append('TP53 mutation (poor prognosis)')
        
        if mutations.get('KRAS') and 'G12C' not in str(mutations.get('KRAS', '')).upper():
            unfavorable_markers.append('KRAS mutation (non-G12C)')
        
        tmb = genomic_data.get('tumor_mutational_burden') or genomic_data.get('tmb')
        if isinstance(tmb, (int, float)) and tmb < 5:
            unfavorable_markers.append('Low TMB (limited immunotherapy benefit)')
        
        # Determine overall prognosis
        if len(favorable_markers) > len(unfavorable_markers):
            prognosis = 'Favorable'
        elif len(unfavorable_markers) > len(favorable_markers):
            prognosis = 'Unfavorable'
        else:
            prognosis = 'Intermediate'
        
        return {
            'prognosis_category': prognosis,
            'favorable_markers': favorable_markers,
            'unfavorable_markers': unfavorable_markers,
            'overall_assessment': self._get_prognosis_assessment(prognosis, favorable_markers, unfavorable_markers),
        }
    
    def _get_prognosis_assessment(self, prognosis: str, favorable: List, unfavorable: List) -> str:
        """Get detailed prognosis assessment"""
        if prognosis == 'Favorable':
            return f'Genomic profile suggests favorable prognosis with {len(favorable)} positive markers. Targeted/immunotherapy options available.'
        elif prognosis == 'Unfavorable':
            return f'Genomic profile indicates challenging prognosis with {len(unfavorable)} unfavorable markers. Consider aggressive treatment and clinical trials.'
        else:
            return 'Mixed genomic profile. Standard treatment protocols recommended with consideration of available targeted options.'
    
    def _identify_resistance_markers(self, mutations: Dict) -> List[Dict]:
        """Identify markers associated with treatment resistance"""
        resistance_markers = []
        
        # T790M mutation (EGFR resistance)
        if mutations.get('T790M') or 'T790M' in str(mutations):
            resistance_markers.append({
                'marker': 'EGFR T790M',
                'resistance_to': 'First/second generation EGFR inhibitors',
                'alternative': 'Osimertinib (third generation EGFR inhibitor)',
            })
        
        # MET amplification (resistance mechanism)
        if mutations.get('MET') or 'MET' in str(mutations):
            resistance_markers.append({
                'marker': 'MET amplification',
                'resistance_to': 'EGFR inhibitors',
                'alternative': 'MET inhibitors or combination therapy',
            })
        
        return resistance_markers
    
    def _generate_genomic_recommendations(self, genomic_data: Dict) -> List[str]:
        """Generate treatment recommendations based on genomics"""
        recommendations = []
        
        mutations = genomic_data.get('mutations', {})
        targeted_eligibility = self._assess_targeted_therapy_eligibility(mutations, genomic_data.get('biomarkers', {}))
        immuno_eligibility = self._assess_immunotherapy_eligibility(genomic_data)
        
        if targeted_eligibility['eligible']:
            recommendations.append('Consider targeted therapy based on actionable mutations')
        
        if immuno_eligibility['eligible']:
            recommendations.append('Consider immunotherapy based on biomarker profile')
        
        if not targeted_eligibility['eligible'] and not immuno_eligibility['eligible']:
            recommendations.append('Standard chemotherapy recommended')
            recommendations.append('Consider comprehensive genomic profiling for additional options')
        
        return recommendations
    
    def _assess_trial_eligibility(self, genomic_data: Dict) -> List[Dict]:
        """Assess eligibility for clinical trials"""
        trials = []
        mutations = genomic_data.get('mutations', {})
        
        # Check for rare mutations that may have trial options
        rare_mutations = ['NTRK', 'RET', 'ROS1', 'MET']
        for mutation in rare_mutations:
            if mutations.get(mutation):
                trials.append({
                    'trial_type': f'{mutation} fusion/rearrangement study',
                    'phase': 'Phase 2/3',
                    'status': 'Recruiting',
                    'description': f'Targeted therapy trials for {mutation} alterations',
                })
        
        # High TMB trials
        tmb = genomic_data.get('tumor_mutational_burden') or genomic_data.get('tmb')
        if isinstance(tmb, (int, float)) and tmb >= 10:
            trials.append({
                'trial_type': 'High TMB immunotherapy study',
                'phase': 'Phase 2/3',
                'status': 'Recruiting',
                'description': 'Immunotherapy trials for high TMB patients',
            })
        
        return trials
    
    def _calculate_genomic_risk(self, genomic_data: Dict) -> Dict:
        """Calculate genomic risk score"""
        risk_score = 50  # Base score
        
        mutations = genomic_data.get('mutations', {})
        
        # Adjust for unfavorable markers
        if mutations.get('TP53'):
            risk_score += 20
        if mutations.get('KRAS') and 'G12C' not in str(mutations.get('KRAS', '')).upper():
            risk_score += 15
        
        # Adjust for favorable markers
        if mutations.get('BRCA1') or mutations.get('BRCA2'):
            risk_score -= 10
        if 'msi-h' in str(genomic_data.get('msi_status', '')).lower():
            risk_score -= 15
        
        # Normalize to 0-100
        risk_score = max(0, min(100, risk_score))
        
        if risk_score >= 70:
            risk_level = 'High'
        elif risk_score >= 40:
            risk_level = 'Moderate'
        else:
            risk_level = 'Low'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'interpretation': self._get_risk_interpretation(risk_level),
        }
    
    def _get_risk_interpretation(self, risk_level: str) -> str:
        """Get risk interpretation"""
        interpretations = {
            'High': 'High genomic risk profile. Consider aggressive treatment and close monitoring.',
            'Moderate': 'Moderate genomic risk. Standard treatment protocols with monitoring recommended.',
            'Low': 'Lower genomic risk profile. Favorable prognosis with appropriate treatment.',
        }
        return interpretations.get(risk_level, 'Risk assessment pending')

