#!/usr/bin/env python3
"""
Manually synthesize and save workflow results
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from agent_manager.db import get_session_factory
from agent_manager.orm import TaskGraphORM, TaskStepORM, ResultORM

async def synthesize_workflow(workflow_id: str):
    """Synthesize and save workflow results"""
    
    print(f"\n[INFO] Extracting results for workflow: {workflow_id}")
    
    # Get database session
    SessionLocal = get_session_factory()
    
    async with SessionLocal() as session:
        # Get task graph with results
        stmt = (
            select(TaskGraphORM)
            .where(TaskGraphORM.workflow_id == workflow_id)
            .options(
                selectinload(TaskGraphORM.tasks)
                .selectinload(TaskStepORM.results)
            )
        )
        result = await session.execute(stmt)
        task_graph = result.scalar_one_or_none()
        
        if not task_graph:
            print(f"[ERROR] Workflow {workflow_id} not found")
            return
        
        print(f"[INFO] Found workflow with {len(task_graph.tasks)} tasks")
        
        # Extract results
        all_results = []
        for task in task_graph.tasks:
            if task.results:
                for task_result in task.results:
                    all_results.append({
                        'task_id': task.step_id,
                        'agent': task_result.source_agent,
                        'result': task_result.final_result,
                        'execution_time': task_result.execution_time
                    })
        
        if not all_results:
            print(f"[ERROR] No results found for workflow")
            return
        
        print(f"[INFO] Found {len(all_results)} task results")
        
        # Create project folder  
        today = datetime.now().strftime('%Y-%m-%d')
        project_name = "paint_app"
        project_folder = Path(f"projects/{today}/{project_name}")
        src_folder = project_folder / "src"
        src_folder.mkdir(parents=True, exist_ok=True)
        
        # Save individual task results
        for i, result_data in enumerate(all_results, 1):
            task_file = src_folder / f"task_{i}_{result_data['agent']}.md"
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(f"# Task {i} - {result_data['agent']}\n\n")
                f.write(f"**Execution Time**: {result_data['execution_time']:.2f}s\n\n")
                f.write(result_data['result'])
            print(f"  [SAVED] {task_file}")
        
        # Create FINAL_OUTPUT.md with synthesized result
        final_output = project_folder / "FINAL_OUTPUT.md"
        with open(final_output, 'w', encoding='utf-8') as f:
            f.write(f"# Paint Application - Final Output\n\n")
            f.write(f"**Workflow ID**: {workflow_id}\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Project Request\n\n")
            f.write(task_graph.user_request + "\n\n")
            f.write("## Analysis and Implementation Plan\n\n")
            
            for result_data in all_results:
                f.write(result_data['result'] + "\n\n")
        
        print(f"  [SAVED] {final_output}")
        
        # Create workflow summary
        summary_file = project_folder / "workflow_summary.json"
        summary = {
            'workflow_id': workflow_id,
            'project_name': project_name,
            'completed_at': datetime.now().isoformat(),
            'total_tasks': len(all_results),
            'total_execution_time': sum(r['execution_time'] for r in all_results),
            'agents_used': list(set(r['agent'] for r in all_results))
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        print(f"  [SAVED] {summary_file}")
        
        print(f"\n[SUCCESS] All results saved to: {project_folder}")
        print(f"\n[FILES]")
        for file in project_folder.rglob('*'):
            if file.is_file():
                print(f"  - {file.relative_to('projects')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        workflow_id = sys.argv[1]
    else:
        # Use the paint app workflow ID
        workflow_id = "edb2ec6b-4ed6-4cab-bb63-ac6b0a401573"
    
    asyncio.run(synthesize_workflow(workflow_id))
