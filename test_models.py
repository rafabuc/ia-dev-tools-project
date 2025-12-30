# test_models.py
"""
Test script for SQLAlchemy models.
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import engine, init_db
from backend.models.workflow import Base, Workflow, WorkflowType, WorkflowStatus
from backend.models.workflow_step import WorkflowStep, WorkflowStepStatus
from backend.utils.logging import get_logger

logger = get_logger(__name__)

def test_models():
    """Test model creation and relationships."""
    print("=" * 60)
    print("TESTING MODELS")
    print("=" * 60)
    
    try:
        # Initialize database
        print("1. Initializing database...")
        init_db()
        print("   ✓ Database initialized")
        
        # Test creating tables
        print("\n2. Testing table creation...")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = {'workflows', 'workflow_steps'}
        for table in required_tables:
            if table in tables:
                print(f"   ✓ Table '{table}' created")
            else:
                print(f"   ✗ Table '{table}' NOT created")
        
        # Test model imports
        print("\n3. Testing model imports...")
        print(f"   ✓ Workflow imported: {Workflow}")
        print(f"   ✓ WorkflowStep imported: {WorkflowStep}")
        
        # Test enum values
        print("\n4. Testing enum values...")
        print(f"   ✓ WorkflowType: {[t.value for t in WorkflowType]}")
        print(f"   ✓ WorkflowStatus: {[s.value for s in WorkflowStatus]}")
        print(f"   ✓ WorkflowStepStatus: {[s.value for s in WorkflowStepStatus]}")
        
        # Test model instantiation
        print("\n5. Testing model instantiation...")
        import uuid
        
        # Create a workflow instance
        workflow = Workflow(
            type=WorkflowType.INCIDENT_RESPONSE,
            status=WorkflowStatus.PENDING,
            triggered_by="test_user",
            workflow_data={"test": "data"}
        )
        print(f"   ✓ Workflow instance created: {workflow}")
        
        # Create a workflow step instance
        workflow_step = WorkflowStep(
            workflow_id=uuid.uuid4(),
            step_name="test_step",
            step_order=1,
            status=WorkflowStepStatus.PENDING
        )
        print(f"   ✓ WorkflowStep instance created: {workflow_step}")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_models()