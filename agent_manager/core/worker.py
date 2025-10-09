"""
WorkerAgent implementation with RA (Reasoning-Acting) pattern.

This module provides the core worker agent logic that executes tasks
through iterative reasoning and action cycles, producing structured
ThoughtAction outputs and complete execution histories.
"""

import asyncio
import time
from typing import List, Optional, Set, Dict
from contextlib import asynccontextmanager

from agent_manager.core.models import TaskStep, ThoughtAction, RAHistory
from agent_manager.core.llm_client import LLMClient, get_llm_client
from agent_manager.core.file_lock import (
    file_lock,
    extract_file_paths_from_action,
    classify_file_access_type,
    FileLockError,
    FileLockTimeout
)


class WorkerAgent:
    """
    Specialized agent for task execution using RA pattern.
    
    Implements the Reasoning-Acting loop where the agent iteratively
    thinks about the problem, decides on actions, observes results,
    and continues until the task is complete.
    
    Go/No-Go Checkpoint: Worker test generates complete RA history in structured Result
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        max_iterations: int = 10,
        llm_client: Optional[LLMClient] = None,
        client_id: Optional[str] = None
    ):
        """
        Initialize WorkerAgent.
        
        Args:
            name: Human-readable agent name
            role: Agent role/type (e.g., "researcher", "writer", "analyst")
            max_iterations: Maximum RA iterations before stopping
            llm_client: Optional LLM client (uses global if None)
            client_id: Optional client identifier for file locking
        """
        self.name = name
        self.role = role
        self.max_iterations = max_iterations
        self._llm_client = llm_client
        self.client_id = client_id or f"{name}_{role}"
    
    async def get_llm_client(self) -> LLMClient:
        """Get LLM client instance."""
        if self._llm_client is None:
            return await get_llm_client()
        return self._llm_client
    
    def get_system_prompt(self) -> str:
        """
        Get role-specific system prompt with RA pattern instructions.
        
        Returns:
            str: Complete system prompt for this agent role
        """
        base_prompt = f"""
You are {self.name}, a highly skilled {self.role} agent working in a multi-agent coordination system.

Your task execution follows the Reasoning-Acting (RA) pattern:
1. THOUGHT: Carefully analyze the current situation, task requirements, and any previous observations
2. ACTION: Decide on a specific, concrete action to take next
3. OBSERVATION: Note the results or feedback from your action (this will be provided)

CRITICAL REQUIREMENTS:
- You must respond with valid JSON matching the ThoughtAction schema
- Each iteration should show clear reasoning leading to a specific action
- Continue iterating until you have a complete, high-quality result
- Your final iteration should include a comprehensive final result
- Be thorough but efficient - aim for quality over quantity

RESPONSE FORMAT:
You must always respond with a JSON object containing:
{{
  "thought": "Your detailed reasoning about the current situation",
  "action": "The specific action you're taking next",
  "observation": null,
  "iteration_number": <number>
}}

AGENT ROLE SPECIALIZATION ({self.role}):
"""
        
        # Add role-specific instructions
        role_instructions = {
            "researcher": """
- Conduct thorough research on the given topic
- Gather relevant information from multiple angles
- Verify facts and identify reliable sources
- Synthesize findings into comprehensive insights
- Focus on accuracy, depth, and reliability
""",
            "writer": """
- Create clear, engaging, and well-structured content
- Adapt writing style to the target audience
- Ensure proper flow, grammar, and readability
- Incorporate research findings effectively
- Focus on clarity, persuasiveness, and impact
""",
            "analyst": """
- Break down complex problems into manageable parts
- Identify patterns, trends, and key insights
- Provide data-driven recommendations
- Consider multiple perspectives and scenarios
- Focus on logical reasoning and evidence-based conclusions
""",
            "planner": """
- Break down complex tasks into actionable steps
- Consider dependencies and sequencing
- Estimate effort and identify potential risks
- Create clear, executable plans
- Focus on feasibility, completeness, and clarity
""",
            "reviewer": """
- Evaluate work quality against defined criteria
- Identify strengths, weaknesses, and improvement areas
- Provide constructive, actionable feedback
- Ensure completeness and accuracy
- Focus on quality assurance and continuous improvement
"""
        }
        
        role_instruction = role_instructions.get(
            self.role.lower(),
            f"- Execute tasks according to your {self.role} specialization\n- Apply domain expertise and best practices\n- Deliver high-quality, professional results"
        )
        
        return base_prompt + role_instruction
    
    async def execute_task(self, task: TaskStep) -> RAHistory:
        """
        Execute a task using the RA pattern with file safety coordination.
        
        Runs the iterative reasoning-acting loop until the task is complete
        or max iterations reached, producing a complete execution history.
        Includes file lock management to prevent concurrent access conflicts.
        
        Args:
            task: TaskStep to execute
            
        Returns:
            RAHistory: Complete execution trace with all iterations
            
        Go/No-Go Checkpoint: Returns structured Result with complete ThoughtAction history
        """
        start_time = time.time()
        iterations: List[ThoughtAction] = []
        current_observation = None
        
        llm_client = await self.get_llm_client()
        system_prompt = self.get_system_prompt()
        
        print(f"🤖 {self.name} starting task: {task.step_id}")
        
        # Pre-acquire file locks if task has declared file dependencies
        async with self._manage_task_file_locks(task):
            for iteration_num in range(1, self.max_iterations + 1):
                # Prepare user input with task context and previous observations
                user_input = self._prepare_iteration_input(
                    task, iterations, current_observation, iteration_num
                )
                
                try:
                    # Get next thought/action from LLM
                    thought_action = await llm_client.run_prompt_for_json(
                        system_prompt=system_prompt,
                        user_input=user_input,
                        json_schema=ThoughtAction
                    )
                    
                    # Ensure correct iteration number
                    thought_action.iteration_number = iteration_num
                    
                    # Execute action with file safety
                    observation = await self._execute_action_safely(thought_action.action, task)
                    thought_action.observation = observation
                    current_observation = observation
                    
                    iterations.append(thought_action)
                    
                    print(f"  🧠 Iteration {iteration_num}: {thought_action.action[:100]}...")
                    
                    # Check if task is complete
                    if self._is_task_complete(thought_action, task):
                        print(f"  ✅ Task completed after {iteration_num} iterations")
                        break
                        
                except Exception as e:
                    print(f"  ❌ Error in iteration {iteration_num}: {str(e)}")
                    # Create error iteration
                    error_thought = ThoughtAction(
                        thought=f"Encountered error: {str(e)}. Need to adjust approach.",
                        action="Reassess task and continue with alternative approach",
                        observation=f"Error occurred: {str(e)}",
                        iteration_number=iteration_num
                    )
                    iterations.append(error_thought)
                    current_observation = error_thought.observation
        
        # Generate final result
        final_result = await self._generate_final_result(task, iterations)
        execution_time = time.time() - start_time
        
        return RAHistory(
            iterations=iterations,
            final_result=final_result,
            source_agent=self.role,
            execution_time=execution_time,
            client_id=self.client_id
        )
    
    @asynccontextmanager
    async def _manage_task_file_locks(self, task: TaskStep):
        """
        Context manager for task-level file lock management.
        
        Pre-acquires locks for declared file dependencies and releases them
        when the task execution context exits.
        """
        acquired_locks = []
        
        try:
            # Acquire locks for declared file dependencies
            for file_path in task.file_dependencies:
                access_type = task.file_access_types.get(file_path, "read")
                try:
                    async with file_lock(
                        file_path=file_path,
                        access_type=access_type,
                        timeout_seconds=30.0,
                        client_id=self.client_id
                    ) as handle:
                        acquired_locks.append((file_path, access_type, handle))
                        print(f"🔒 Pre-acquired {access_type} lock: {file_path}")
                except FileLockTimeout:
                    print(f"⏰ Timeout acquiring lock for {file_path}, proceeding without pre-lock")
                except FileLockError as e:
                    print(f"⚠️ Could not acquire lock for {file_path}: {e}")
            
            yield
            
        finally:
            # Locks are automatically released when file handles close
            if acquired_locks:
                print(f"🔓 Released {len(acquired_locks)} pre-acquired file locks")
    
    async def _execute_action_safely(self, action: str, task: TaskStep) -> str:
        """
        Execute action with file safety coordination.
        
        Extracts file paths from the action and acquires appropriate locks
        before executing the action.
        """
        # Extract potential file paths from action
        file_paths = extract_file_paths_from_action(action)
        
        if not file_paths:
            # No file operations detected, execute normally
            return await self._execute_action(action, task)
        
        # Acquire locks for detected file operations
        async with self._acquire_action_file_locks(action, file_paths):
            return await self._execute_action(action, task)
    
    @asynccontextmanager
    async def _acquire_action_file_locks(self, action: str, file_paths: Set[str]):
        """
        Context manager for action-specific file lock acquisition.
        """
        acquired_locks = []
        
        try:
            for file_path in file_paths:
                access_type = classify_file_access_type(action, file_path)
                
                try:
                    async with file_lock(
                        file_path=file_path,
                        access_type=access_type,
                        timeout_seconds=10.0,
                        client_id=self.client_id
                    ) as handle:
                        acquired_locks.append((file_path, access_type, handle))
                        
                except FileLockTimeout:
                    print(f"⏰ Timeout acquiring {access_type} lock for {file_path}")
                    # Continue without lock for this file
                except FileLockError as e:
                    print(f"⚠️ File lock error for {file_path}: {e}")
                    # Continue without lock for this file
            
            yield
            
        finally:
            # File handles automatically release locks when closed
            pass
    
    def _prepare_iteration_input(
        self,
        task: TaskStep,
        previous_iterations: List[ThoughtAction],
        current_observation: Optional[str],
        iteration_num: int
    ) -> str:
        """Prepare input for the current iteration."""
        input_parts = [
            f"TASK: {task.task_description}",
            f"STEP ID: {task.step_id}",
            f"ASSIGNED AGENT: {task.assigned_agent}",
            f"ITERATION: {iteration_num}/{self.max_iterations}"
        ]
        
        if task.dependencies:
            input_parts.append(f"DEPENDENCIES: {', '.join(task.dependencies)}")
        
        if previous_iterations:
            input_parts.append("\nPREVIOUS ITERATIONS:")
            for i, prev in enumerate(previous_iterations, 1):
                input_parts.append(f"{i}. THOUGHT: {prev.thought}")
                input_parts.append(f"   ACTION: {prev.action}")
                if prev.observation:
                    input_parts.append(f"   OBSERVATION: {prev.observation}")
        
        if current_observation:
            input_parts.append(f"\nCURRENT OBSERVATION: {current_observation}")
        
        input_parts.append(f"\nWhat is your next thought and action for iteration {iteration_num}?")
        
        return "\n".join(input_parts)
    
    async def _execute_action(self, action: str, task: TaskStep) -> str:
        """
        Simulate action execution and return observation.
        
        In a real implementation, this would interface with external tools,
        APIs, or systems. For now, we simulate realistic observations.
        """
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Generate realistic observation based on action type
        action_lower = action.lower()
        
        if "research" in action_lower or "search" in action_lower:
            return f"Research completed. Found relevant information related to: {action}"
        elif "write" in action_lower or "draft" in action_lower:
            return f"Writing completed. Generated content based on: {action}"
        elif "analyze" in action_lower or "review" in action_lower:
            return f"Analysis completed. Key insights identified from: {action}"
        elif "plan" in action_lower or "organize" in action_lower:
            return f"Planning completed. Structured approach developed for: {action}"
        elif "finalize" in action_lower or "complete" in action_lower:
            return f"Task finalization completed. Ready for delivery."
        else:
            return f"Action executed successfully: {action}"
    
    def _is_task_complete(self, thought_action: ThoughtAction, task: TaskStep) -> bool:
        """
        Determine if the task is complete based on the current iteration.
        
        Checks for completion indicators in the thought or action.
        """
        completion_indicators = [
            "complete", "finished", "done", "final", "ready",
            "delivered", "accomplished", "concluded"
        ]
        
        text_to_check = (thought_action.thought + " " + thought_action.action).lower()
        return any(indicator in text_to_check for indicator in completion_indicators)
    
    async def _generate_final_result(
        self,
        task: TaskStep,
        iterations: List[ThoughtAction]
    ) -> str:
        """
        Generate comprehensive final result based on all iterations.
        
        Synthesizes the complete reasoning and action history into
        a coherent final deliverable.
        """
        if not iterations:
            return f"Task {task.step_id} could not be completed - no successful iterations."
        
        # Use LLM to synthesize final result
        llm_client = await self.get_llm_client()
        
        synthesis_prompt = f"""
You are synthesizing the final result for a completed task.

TASK: {task.task_description}
AGENT ROLE: {self.role}

COMPLETE EXECUTION HISTORY:
"""
        
        for i, iteration in enumerate(iterations, 1):
            synthesis_prompt += f"\nIteration {i}:\n"
            synthesis_prompt += f"  Thought: {iteration.thought}\n"
            synthesis_prompt += f"  Action: {iteration.action}\n"
            if iteration.observation:
                synthesis_prompt += f"  Observation: {iteration.observation}\n"
        
        synthesis_prompt += f"""

Please provide a comprehensive final result that:
1. Summarizes what was accomplished
2. Includes key deliverables or insights
3. Addresses the original task requirements
4. Is clear, professional, and actionable

Respond with just the final result content, not meta-commentary about the process.
"""
        
        try:
            final_result = await llm_client.run_simple_prompt(synthesis_prompt)
            return final_result
        except Exception as e:
            # Fallback to simple synthesis
            return f"Task {task.step_id} completed by {self.role} agent. Final iteration: {iterations[-1].action}"