"""
Agency response simulation for CFR Document Analyzer.

Simulates realistic agency responses to regulatory reform recommendations.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from .llm_client import LLMClient
from .models import AnalysisResult
from .utils import safe_json_dumps, safe_json_loads


logger = logging.getLogger(__name__)


class ResponseType(Enum):
    """Types of agency responses."""
    SUPPORTIVE = "supportive"
    RESISTANT = "resistant"
    CONDITIONAL = "conditional"
    NEUTRAL = "neutral"


class StakeholderPerspective(Enum):
    """Different stakeholder perspectives within agencies."""
    LEADERSHIP = "leadership"
    PROGRAM_STAFF = "program_staff"
    LEGAL_COUNSEL = "legal_counsel"
    BUDGET_OFFICE = "budget_office"
    FIELD_OPERATIONS = "field_operations"


@dataclass
class AgencyResponse:
    """Agency response to reform recommendations."""
    agency_slug: str
    document_number: str
    response_type: ResponseType
    perspective: StakeholderPerspective
    position_summary: str
    detailed_rationale: str
    concerns: List[str] = field(default_factory=list)
    counterproposals: List[str] = field(default_factory=list)
    implementation_challenges: List[str] = field(default_factory=list)
    resource_implications: str = ""
    timeline_concerns: str = ""
    stakeholder_impact: str = ""
    legal_considerations: str = ""
    confidence_level: float = 0.0
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None


class AgencyResponseSimulator:
    """Simulates realistic agency responses to regulatory reform recommendations."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize agency response simulator.
        
        Args:
            llm_client: LLM client for generating responses
        """
        self.llm_client = llm_client or LLMClient()
        
        # Response templates for different perspectives
        self.perspective_templates = {
            StakeholderPerspective.LEADERSHIP: {
                "focus": "strategic impact, organizational priorities, public perception",
                "concerns": ["mission alignment", "resource allocation", "stakeholder relations", "political implications"]
            },
            StakeholderPerspective.PROGRAM_STAFF: {
                "focus": "operational feasibility, program effectiveness, service delivery",
                "concerns": ["implementation complexity", "staff workload", "program outcomes", "beneficiary impact"]
            },
            StakeholderPerspective.LEGAL_COUNSEL: {
                "focus": "legal compliance, regulatory authority, procedural requirements",
                "concerns": ["statutory authority", "due process", "legal risks", "regulatory precedent"]
            },
            StakeholderPerspective.BUDGET_OFFICE: {
                "focus": "cost implications, resource requirements, budget constraints",
                "concerns": ["funding availability", "cost-benefit analysis", "budget impact", "resource reallocation"]
            },
            StakeholderPerspective.FIELD_OPERATIONS: {
                "focus": "practical implementation, operational impact, field staff concerns",
                "concerns": ["operational disruption", "training needs", "system changes", "field capacity"]
            }
        }
        
        logger.info("Agency response simulator initialized")
    
    def simulate_agency_response(self, 
                                analysis_result: AnalysisResult,
                                agency_context: Dict[str, Any],
                                perspective: StakeholderPerspective = StakeholderPerspective.LEADERSHIP,
                                response_bias: Optional[ResponseType] = None) -> AgencyResponse:
        """
        Simulate an agency response to reform recommendations.
        
        Args:
            analysis_result: Analysis result with reform recommendations
            agency_context: Context about the agency (mission, priorities, constraints)
            perspective: Stakeholder perspective to simulate
            response_bias: Optional bias toward specific response type
            
        Returns:
            AgencyResponse object
        """
        try:
            import time
            start_time = time.time()
            
            # Extract reform recommendations
            recommendations = analysis_result.reform_recommendations or []
            if not recommendations:
                return AgencyResponse(
                    agency_slug=agency_context.get('agency_slug', 'unknown'),
                    document_number=str(analysis_result.document_id),
                    response_type=ResponseType.NEUTRAL,
                    perspective=perspective,
                    position_summary="No specific recommendations to respond to.",
                    detailed_rationale="The analysis did not provide specific reform recommendations.",
                    success=True,
                    processing_time=time.time() - start_time
                )
            
            # Generate response using LLM
            response_data = self._generate_llm_response(
                analysis_result, agency_context, perspective, response_bias, recommendations
            )
            
            if not response_data['success']:
                return AgencyResponse(
                    agency_slug=agency_context.get('agency_slug', 'unknown'),
                    document_number=str(analysis_result.document_id),
                    response_type=ResponseType.NEUTRAL,
                    perspective=perspective,
                    position_summary="Response generation failed.",
                    detailed_rationale="Unable to generate agency response due to technical issues.",
                    success=False,
                    error_message=response_data.get('error'),
                    processing_time=time.time() - start_time
                )
            
            # Parse LLM response
            parsed_response = self._parse_response(response_data['response'], perspective)
            
            # Create agency response object
            agency_response = AgencyResponse(
                agency_slug=agency_context.get('agency_slug', 'unknown'),
                document_number=str(analysis_result.document_id),
                response_type=ResponseType(parsed_response.get('response_type', 'neutral')),
                perspective=perspective,
                position_summary=parsed_response.get('position_summary', ''),
                detailed_rationale=parsed_response.get('detailed_rationale', ''),
                concerns=parsed_response.get('concerns', []),
                counterproposals=parsed_response.get('counterproposals', []),
                implementation_challenges=parsed_response.get('implementation_challenges', []),
                resource_implications=parsed_response.get('resource_implications', ''),
                timeline_concerns=parsed_response.get('timeline_concerns', ''),
                stakeholder_impact=parsed_response.get('stakeholder_impact', ''),
                legal_considerations=parsed_response.get('legal_considerations', ''),
                confidence_level=parsed_response.get('confidence_level', 0.7),
                processing_time=time.time() - start_time,
                success=True
            )
            
            logger.info(f"Generated {perspective.value} response for document {analysis_result.document_id}")
            return agency_response
            
        except Exception as e:
            logger.error(f"Error simulating agency response: {e}")
            return AgencyResponse(
                agency_slug=agency_context.get('agency_slug', 'unknown'),
                document_number=str(analysis_result.document_id),
                response_type=ResponseType.NEUTRAL,
                perspective=perspective,
                position_summary="Response simulation failed.",
                detailed_rationale=f"Error occurred during response simulation: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    def _generate_llm_response(self, 
                              analysis_result: AnalysisResult,
                              agency_context: Dict[str, Any],
                              perspective: StakeholderPerspective,
                              response_bias: Optional[ResponseType],
                              recommendations: List[str]) -> Dict[str, Any]:
        """Generate LLM response for agency simulation."""
        try:
            # Build context for the prompt
            agency_name = agency_context.get('agency_name', 'Unknown Agency')
            agency_mission = agency_context.get('mission', 'Not specified')
            agency_priorities = agency_context.get('priorities', [])
            agency_constraints = agency_context.get('constraints', [])
            
            perspective_info = self.perspective_templates[perspective]
            
            # Create the simulation prompt
            prompt = f"""You are simulating the response of a {perspective.value.replace('_', ' ')} at {agency_name} to regulatory reform recommendations.

AGENCY CONTEXT:
- Agency: {agency_name}
- Mission: {agency_mission}
- Key Priorities: {', '.join(agency_priorities) if agency_priorities else 'Not specified'}
- Current Constraints: {', '.join(agency_constraints) if agency_constraints else 'Not specified'}

PERSPECTIVE: {perspective.value.replace('_', ' ').title()}
- Focus Areas: {perspective_info['focus']}
- Typical Concerns: {', '.join(perspective_info['concerns'])}

REFORM RECOMMENDATIONS TO RESPOND TO:
{chr(10).join(f'- {rec}' for rec in recommendations)}

DOCUMENT CATEGORY: {analysis_result.category.value if analysis_result.category else 'Unknown'}
STATUTORY REFERENCES: {', '.join(analysis_result.statutory_references) if analysis_result.statutory_references else 'None provided'}

Please provide a realistic agency response from this perspective. Consider:
- The agency's mission and priorities
- Practical implementation challenges
- Resource and budget implications
- Legal and regulatory constraints
- Stakeholder impacts
- Timeline considerations

Respond in this structured format:

RESPONSE_TYPE: [supportive/resistant/conditional/neutral]
POSITION_SUMMARY: [Brief 2-3 sentence summary of the agency's position]
DETAILED_RATIONALE: [Detailed explanation of the agency's reasoning and perspective]
CONCERNS: [List specific concerns, one per line with bullet points]
COUNTERPROPOSALS: [Alternative approaches or modifications, one per line with bullet points]
IMPLEMENTATION_CHALLENGES: [Specific implementation difficulties, one per line with bullet points]
RESOURCE_IMPLICATIONS: [Description of resource and budget impacts]
TIMELINE_CONCERNS: [Timeline-related issues and considerations]
STAKEHOLDER_IMPACT: [Impact on various stakeholders]
LEGAL_CONSIDERATIONS: [Legal and regulatory considerations]
CONFIDENCE_LEVEL: [0.0-1.0 confidence in this response]

Provide a realistic, professional response that reflects the genuine concerns and perspectives this stakeholder would have."""
            
            # Add bias instruction if specified
            if response_bias:
                prompt += f"\n\nNOTE: The agency is generally inclined to be {response_bias.value} toward these recommendations, but provide realistic reasoning for this position."
            
            # Generate response
            response_text, success, error = self.llm_client.analyze_document(
                "", prompt, f"agency_response_{analysis_result.document_id}_{perspective.value}"
            )
            
            return {
                'success': success,
                'response': response_text,
                'error': error
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_response(self, response_text: str, perspective: StakeholderPerspective) -> Dict[str, Any]:
        """Parse LLM response into structured data."""
        try:
            import re
            
            parsed = {}
            
            # Parse response type
            response_type_match = re.search(r'RESPONSE_TYPE:\s*(\w+)', response_text, re.IGNORECASE)
            if response_type_match:
                response_type = response_type_match.group(1).lower()
                if response_type in [rt.value for rt in ResponseType]:
                    parsed['response_type'] = response_type
                else:
                    parsed['response_type'] = 'neutral'
            else:
                parsed['response_type'] = 'neutral'
            
            # Parse position summary
            position_match = re.search(r'POSITION_SUMMARY:\s*(.*?)(?=DETAILED_RATIONALE:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if position_match:
                parsed['position_summary'] = position_match.group(1).strip()
            
            # Parse detailed rationale
            rationale_match = re.search(r'DETAILED_RATIONALE:\s*(.*?)(?=CONCERNS:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if rationale_match:
                parsed['detailed_rationale'] = rationale_match.group(1).strip()
            
            # Parse concerns
            concerns_match = re.search(r'CONCERNS:\s*(.*?)(?=COUNTERPROPOSALS:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if concerns_match:
                concerns_text = concerns_match.group(1)
                concerns = re.findall(r'[-•]\s*(.+)', concerns_text)
                parsed['concerns'] = [c.strip() for c in concerns if c.strip()]
            
            # Parse counterproposals
            counter_match = re.search(r'COUNTERPROPOSALS:\s*(.*?)(?=IMPLEMENTATION_CHALLENGES:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if counter_match:
                counter_text = counter_match.group(1)
                counterproposals = re.findall(r'[-•]\s*(.+)', counter_text)
                parsed['counterproposals'] = [c.strip() for c in counterproposals if c.strip()]
            
            # Parse implementation challenges
            challenges_match = re.search(r'IMPLEMENTATION_CHALLENGES:\s*(.*?)(?=RESOURCE_IMPLICATIONS:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if challenges_match:
                challenges_text = challenges_match.group(1)
                challenges = re.findall(r'[-•]\s*(.+)', challenges_text)
                parsed['implementation_challenges'] = [c.strip() for c in challenges if c.strip()]
            
            # Parse resource implications
            resource_match = re.search(r'RESOURCE_IMPLICATIONS:\s*(.*?)(?=TIMELINE_CONCERNS:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if resource_match:
                parsed['resource_implications'] = resource_match.group(1).strip()
            
            # Parse timeline concerns
            timeline_match = re.search(r'TIMELINE_CONCERNS:\s*(.*?)(?=STAKEHOLDER_IMPACT:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if timeline_match:
                parsed['timeline_concerns'] = timeline_match.group(1).strip()
            
            # Parse stakeholder impact
            stakeholder_match = re.search(r'STAKEHOLDER_IMPACT:\s*(.*?)(?=LEGAL_CONSIDERATIONS:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if stakeholder_match:
                parsed['stakeholder_impact'] = stakeholder_match.group(1).strip()
            
            # Parse legal considerations
            legal_match = re.search(r'LEGAL_CONSIDERATIONS:\s*(.*?)(?=CONFIDENCE_LEVEL:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if legal_match:
                parsed['legal_considerations'] = legal_match.group(1).strip()
            
            # Parse confidence level
            confidence_match = re.search(r'CONFIDENCE_LEVEL:\s*([\d.]+)', response_text, re.IGNORECASE)
            if confidence_match:
                try:
                    confidence = float(confidence_match.group(1))
                    parsed['confidence_level'] = max(0.0, min(1.0, confidence))
                except ValueError:
                    parsed['confidence_level'] = 0.7
            else:
                parsed['confidence_level'] = 0.7
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {
                'response_type': 'neutral',
                'position_summary': 'Response parsing failed',
                'detailed_rationale': f'Unable to parse response: {str(e)}',
                'concerns': [],
                'counterproposals': [],
                'implementation_challenges': [],
                'confidence_level': 0.5
            }
    
    def simulate_multiple_perspectives(self, 
                                     analysis_result: AnalysisResult,
                                     agency_context: Dict[str, Any],
                                     perspectives: List[StakeholderPerspective] = None) -> List[AgencyResponse]:
        """
        Simulate responses from multiple stakeholder perspectives.
        
        Args:
            analysis_result: Analysis result with reform recommendations
            agency_context: Context about the agency
            perspectives: List of perspectives to simulate (defaults to all)
            
        Returns:
            List of AgencyResponse objects
        """
        if perspectives is None:
            perspectives = list(StakeholderPerspective)
        
        responses = []
        
        for perspective in perspectives:
            try:
                response = self.simulate_agency_response(
                    analysis_result, agency_context, perspective
                )
                responses.append(response)
                
            except Exception as e:
                logger.error(f"Error simulating {perspective.value} response: {e}")
                # Add error response
                error_response = AgencyResponse(
                    agency_slug=agency_context.get('agency_slug', 'unknown'),
                    document_number=str(analysis_result.document_id),
                    response_type=ResponseType.NEUTRAL,
                    perspective=perspective,
                    position_summary="Response simulation failed.",
                    detailed_rationale=f"Error simulating {perspective.value} response: {str(e)}",
                    success=False,
                    error_message=str(e)
                )
                responses.append(error_response)
        
        logger.info(f"Simulated {len(responses)} perspective responses for document {analysis_result.document_id}")
        return responses
    
    def generate_consensus_response(self, individual_responses: List[AgencyResponse]) -> AgencyResponse:
        """
        Generate a consensus agency response from multiple perspective responses.
        
        Args:
            individual_responses: List of responses from different perspectives
            
        Returns:
            Consensus AgencyResponse
        """
        try:
            if not individual_responses:
                raise ValueError("No individual responses provided")
            
            # Use the first response as a template
            template = individual_responses[0]
            
            # Aggregate response types (most common wins)
            response_types = [r.response_type for r in individual_responses if r.success]
            if response_types:
                from collections import Counter
                most_common_type = Counter(response_types).most_common(1)[0][0]
            else:
                most_common_type = ResponseType.NEUTRAL
            
            # Combine concerns and challenges
            all_concerns = []
            all_challenges = []
            all_counterproposals = []
            
            for response in individual_responses:
                if response.success:
                    all_concerns.extend(response.concerns)
                    all_challenges.extend(response.implementation_challenges)
                    all_counterproposals.extend(response.counterproposals)
            
            # Remove duplicates while preserving order
            unique_concerns = list(dict.fromkeys(all_concerns))
            unique_challenges = list(dict.fromkeys(all_challenges))
            unique_counterproposals = list(dict.fromkeys(all_counterproposals))
            
            # Generate consensus summary
            consensus_summary = self._generate_consensus_summary(individual_responses)
            
            # Create consensus response
            consensus_response = AgencyResponse(
                agency_slug=template.agency_slug,
                document_number=template.document_number,
                response_type=most_common_type,
                perspective=StakeholderPerspective.LEADERSHIP,  # Consensus represents leadership view
                position_summary=consensus_summary,
                detailed_rationale="This consensus response synthesizes perspectives from multiple agency stakeholders.",
                concerns=unique_concerns[:10],  # Limit to top 10
                counterproposals=unique_counterproposals[:5],  # Limit to top 5
                implementation_challenges=unique_challenges[:10],  # Limit to top 10
                confidence_level=sum(r.confidence_level for r in individual_responses if r.success) / len([r for r in individual_responses if r.success]),
                success=True
            )
            
            logger.info(f"Generated consensus response from {len(individual_responses)} individual responses")
            return consensus_response
            
        except Exception as e:
            logger.error(f"Error generating consensus response: {e}")
            return AgencyResponse(
                agency_slug="unknown",
                document_number="unknown",
                response_type=ResponseType.NEUTRAL,
                perspective=StakeholderPerspective.LEADERSHIP,
                position_summary="Consensus generation failed.",
                detailed_rationale=f"Unable to generate consensus response: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    def _generate_consensus_summary(self, responses: List[AgencyResponse]) -> str:
        """Generate a consensus summary from multiple responses."""
        try:
            successful_responses = [r for r in responses if r.success]
            if not successful_responses:
                return "Unable to generate consensus due to response failures."
            
            # Count response types
            from collections import Counter
            response_counts = Counter(r.response_type for r in successful_responses)
            
            # Generate summary based on dominant response type
            dominant_type = response_counts.most_common(1)[0][0]
            
            if dominant_type == ResponseType.SUPPORTIVE:
                return f"The agency is generally supportive of the proposed reforms, with {len(successful_responses)} stakeholder perspectives providing input on implementation approaches."
            elif dominant_type == ResponseType.RESISTANT:
                return f"The agency has significant concerns about the proposed reforms, with {len(successful_responses)} stakeholder perspectives identifying implementation challenges."
            elif dominant_type == ResponseType.CONDITIONAL:
                return f"The agency supports the reforms with conditions, with {len(successful_responses)} stakeholder perspectives providing specific requirements and modifications."
            else:
                return f"The agency maintains a neutral position on the proposed reforms, with {len(successful_responses)} stakeholder perspectives providing balanced analysis."
                
        except Exception as e:
            logger.error(f"Error generating consensus summary: {e}")
            return "Consensus summary generation failed."