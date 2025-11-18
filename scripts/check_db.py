#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('agent_manager.db')
cursor = conn.cursor()

print("=== RECENT WORKFLOWS ===")
cursor.execute('SELECT workflow_id, status, created_at FROM task_graphs ORDER BY created_at DESC LIMIT 3')
for row in cursor.fetchall():
    print(f"Workflow: {row[0]}, Status: {row[1]}, Created: {row[2]}")

print("\n=== RECENT TASKS ===")
cursor.execute('SELECT step_id, assigned_agent, status, workflow_id FROM task_steps ORDER BY created_at DESC LIMIT 5')
for row in cursor.fetchall():
    print(f"Task: {row[0]}, Agent: {row[1]}, Status: {row[2]}, Workflow: {row[3]}")

conn.close()
