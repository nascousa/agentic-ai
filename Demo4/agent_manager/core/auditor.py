"""
AuditorAgent implementation for quality control and workflow validation.

This module provides the critical quality assessment functionality that
reviews completed workflows and determines if they meet quality standards,
providing specific feedback and rework suggestions when necessary.
"""

from typing import List, Optional

from agent_manager.core.models import AuditReport, TaskGraph, RAHistory
from agent_manager.core.llm_client import LLMClient, get_llm_client


class AuditorAgent:
    """
    Specialized agent for quality control and workflow auditing.
    
    Acts as a critical quality gate that reviews completed work
    and provides detailed feedback with specific improvement suggestions.
    
    Go/No-Go Checkpoint: Auditor flags known "bad" input and returns concrete rework_suggestions
    """
    
    def __init__(
        self,
        name: str = "QualityAuditor",
        criteria: Optional[List[str]] = None,
        confidence_threshold: float = 0.8,
        llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize AuditorAgent.
        
        Args:
            name: Human-readable auditor name
            criteria: Quality criteria for evaluation (uses defaults if None)
            confidence_threshold: Minimum confidence for approval
            llm_client: Optional LLM client (uses global if None)
        """
        self.name = name
        self.confidence_threshold = confidence_threshold
        self._llm_client = llm_client
        
        # Default quality criteria
        self.criteria = criteria or [
            "Completeness: All task requirements are fully addressed",
            "Accuracy: Information and conclusions are factually correct",
            "Clarity: Content is clear, well-organized, and easy to understand",
            "Relevance: All content directly relates to the original request",
            "Quality: Work demonstrates professionalism and attention to detail",
            "Consistency: Style and approach are consistent throughout",
            "Actionability: Deliverables are practical and implementable"
        ]
    
    async def get_llm_client(self) -> LLMClient:
        """Get LLM client instance."""
        if self._llm_client is None:
            return await get_llm_client()
        return self._llm_client
    
    def get_audit_prompt(self) -> str:
        """
        Get comprehensive audit system prompt with critical evaluation criteria.
        
        Returns:
            str: Complete system prompt for quality auditing
        """
        criteria_text = "\n".join([f"- {criterion}" for criterion in self.criteria])
        
        return f"""
You are {self.name}, a rigorous quality auditor in a multi-agent coordination system.

Your role is CRITICAL: You are the final quality gate that determines whether completed work meets professional standards. You must be thorough, objective, and uncompromising in your evaluation.

AUDIT RESPONSIBILITIES:
1. Review all completed work against defined quality criteria
2. Identify specific strengths and weaknesses
3. Provide actionable feedback for improvement
4. Make go/no-go decisions based on quality standards
5. Ensure work meets the original requirements

QUALITY CRITERIA:
{criteria_text}

AUDIT PROCESS:
1. Examine the original request and requirements
2. Review each task's execution history and final results
3. Evaluate against each quality criterion
4. Identify specific issues and improvement opportunities
5. Determine overall quality assessment with confidence score
6. Provide detailed, actionable feedback

CRITICAL STANDARDS:
- Be objective and evidence-based in your evaluation
- Point out specific examples of both strengths and weaknesses
- Provide concrete, actionable improvement suggestions
- Consider the end user's perspective and needs
- Maintain high professional standards throughout

RESPONSE FORMAT:
You must respond with valid JSON matching the AuditReport schema:
{{
  "workflow_id": "string",
  "is_successful": boolean,
  "feedback": "Detailed evaluation with specific examples",
  "rework_suggestions": ["Specific actionable improvements"],
  "confidence_score": 0.0-1.0,
  "reviewed_tasks": ["list of task IDs"],
  "audit_criteria": ["criteria used for evaluation"]
}}

IMPORTANT: 
- Only approve work that truly meets high professional standards
- Be specific in your feedback with concrete examples
- Provide actionable rework suggestions when quality is insufficient
- Your confidence score should reflect your certainty in the assessment
- Consider whether you would be comfortable presenting this work to a client
"""
    
    async def run_audit(self, workflow_id: str, task_results: List[RAHistory]) -> AuditReport:
        """
        Conduct comprehensive audit of completed workflow.
        
        Reviews all task results against quality criteria and provides
        detailed feedback with specific improvement suggestions.
        
        Args:
            workflow_id: Workflow identifier being audited
            task_results: List of completed task execution histories
            
        Returns:
            AuditReport: Complete quality assessment with feedback
            
        Go/No-Go Checkpoint: Returns AuditReport with concrete rework_suggestions
        """
        print(f"[AUDIT] {self.name} starting audit for workflow: {workflow_id}")
        
        llm_client = await self.get_llm_client()
        system_prompt = self.get_audit_prompt()
        
        # Prepare comprehensive audit input
        audit_input = self._prepare_audit_input(workflow_id, task_results)
        
        try:
            # Get audit assessment from LLM
            audit_report = await llm_client.run_prompt_for_json(
                system_prompt=system_prompt,
                user_input=audit_input,
                json_schema=AuditReport
            )
            
            # Ensure required fields are set
            audit_report.workflow_id = workflow_id
            audit_report.reviewed_tasks = [result.client_id for result in task_results]
            audit_report.audit_criteria = self.criteria
            
            # Apply confidence threshold logic
            if audit_report.confidence_score < self.confidence_threshold:
                audit_report.is_successful = False
                if "low confidence" not in audit_report.feedback.lower():
                    audit_report.feedback += f" NOTE: Confidence score ({audit_report.confidence_score}) below threshold ({self.confidence_threshold})."
            
            print(f"  [AUDIT] Audit completed: {'PASSED' if audit_report.is_successful else 'FAILED'}")
            print(f"  [CONFIDENCE] {audit_report.confidence_score:.2f}")
            
            return audit_report
            
        except Exception as e:
            print(f"  [ERROR] Audit error: {str(e)}")
            # Return failed audit with error details
            return AuditReport(
                workflow_id=workflow_id,
                is_successful=False,
                feedback=f"Audit process encountered an error: {str(e)}. Manual review required.",
                rework_suggestions=[
                    "Review workflow execution for technical issues",
                    "Ensure all tasks completed successfully",
                    "Verify data integrity and completeness"
                ],
                confidence_score=0.0,
                reviewed_tasks=[result.client_id for result in task_results],
                audit_criteria=self.criteria
            )
    
    def _prepare_audit_input(self, workflow_id: str, task_results: List[RAHistory]) -> str:
        """
        Prepare comprehensive input for audit evaluation.
        
        Compiles all task execution histories and results into a
        structured format for thorough quality assessment.
        """
        input_parts = [
            f"WORKFLOW AUDIT REQUEST",
            f"Workflow ID: {workflow_id}",
            f"Total Tasks: {len(task_results)}",
            f"",
            f"QUALITY CRITERIA TO EVALUATE:",
        ]
        
        for i, criterion in enumerate(self.criteria, 1):
            input_parts.append(f"{i}. {criterion}")
        
        input_parts.extend([
            "",
            "COMPLETED TASK RESULTS FOR REVIEW:",
            ""
        ])
        
        for i, result in enumerate(task_results, 1):
            input_parts.extend([
                f"TASK {i}:",
                f"  Agent: {result.source_agent}",
                f"  Client: {result.client_id}",
                f"  Execution Time: {result.execution_time:.2f}s",
                f"  Iterations: {len(result.iterations)}",
                f"",
                f"  EXECUTION HISTORY:"
            ])
            
            for j, iteration in enumerate(result.iterations, 1):
                input_parts.extend([
                    f"    Iteration {j}:",
                    f"      Thought: {iteration.thought}",
                    f"      Action: {iteration.action}",
                ])
                if iteration.observation:
                    input_parts.append(f"      Observation: {iteration.observation}")
            
            input_parts.extend([
                f"",
                f"  FINAL RESULT:",
                f"  {result.final_result}",
                f"",
                f"  {'-' * 80}",
                f""
            ])
        
        input_parts.extend([
            "",
            "AUDIT INSTRUCTIONS:",
            "1. Evaluate each task result against all quality criteria",
            "2. Consider the overall workflow coherence and completeness",
            "3. Identify specific strengths and areas for improvement",
            "4. Provide actionable feedback with concrete examples",
            "5. Determine if the work meets professional standards",
            "6. Assign an appropriate confidence score for your assessment",
            "",
            "Please provide your comprehensive audit assessment:"
        ])
        
        return "\n".join(input_parts)
    
    async def run_quick_audit(self, final_result: str, original_request: str) -> bool:
        """
        Run a quick quality check on a single result.
        
        Useful for rapid validation without full workflow audit.
        
        Args:
            final_result: The result to evaluate
            original_request: Original user request for context
            
        Returns:
            bool: True if result meets basic quality standards
        """
        try:
            llm_client = await self.get_llm_client()
            
            quick_prompt = f"""
You are a quality auditor doing a quick assessment.

ORIGINAL REQUEST: {original_request}

RESULT TO EVALUATE: {final_result}

Does this result adequately address the original request with reasonable quality?
Consider: completeness, accuracy, clarity, and relevance.

Respond with just "PASS" or "FAIL" followed by a brief reason.
"""
            
            response = await llm_client.run_simple_prompt(quick_prompt)
            return response.strip().upper().startswith("PASS")
            
        except Exception:
            # Conservative approach - fail on error
            return False
    
    def update_criteria(self, new_criteria: List[str]) -> None:
        """
        Update audit criteria for future evaluations.
        
        Args:
            new_criteria: New list of quality criteria
        """
        self.criteria = new_criteria
        print(f"[AUDIT] {self.name} updated audit criteria ({len(new_criteria)} items)")
    
    def add_criterion(self, criterion: str) -> None:
        """
        Add a new quality criterion.
        
        Args:
            criterion: New quality criterion to add
        """
        if criterion not in self.criteria:
            self.criteria.append(criterion)
            print(f"[AUDIT] {self.name} added new criterion: {criterion}")
    
    def get_audit_summary(self, audit_report: AuditReport) -> str:
        """
        Generate a concise audit summary for logging/reporting.
        
        Args:
            audit_report: Completed audit report
            
        Returns:
            str: Concise audit summary
        """
        status = "PASSED" if audit_report.is_successful else "FAILED"
        confidence = f"{audit_report.confidence_score:.1%}"
        task_count = len(audit_report.reviewed_tasks)
        rework_count = len(audit_report.rework_suggestions)
        
        summary = f"Audit {status} | Confidence: {confidence} | Tasks: {task_count}"
        if rework_count > 0:
            summary += f" | Rework Items: {rework_count}"
        
        return summary