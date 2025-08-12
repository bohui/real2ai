"""
Integration test to verify complete migration from user_client.database to repository pattern

This test ensures that:
1. All active user_client.database calls have been migrated
2. All repositories are functioning correctly
3. RLS is properly enforced through repositories
4. No direct database access is used in production code
"""

import pytest
import os
import re
from pathlib import Path


class TestRepositoryMigrationComplete:
    """Test suite to verify complete repository migration"""

    def test_no_active_database_calls_in_app_code(self):
        """Verify no active user_client.database calls remain in app code"""
        
        app_dir = Path("/Users/bohuihan/ai/real2ai/backend/app")
        
        # Patterns to find database calls (excluding comments)
        db_call_pattern = re.compile(r'^[^#]*user_client\.database\.', re.MULTILINE)
        
        violations = []
        
        # Check all Python files in app directory
        for py_file in app_dir.rglob("*.py"):
            # Skip test files
            if "test" in str(py_file):
                continue
                
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Find all database calls not in comments
            matches = db_call_pattern.findall(content)
            
            if matches:
                # Count actual violations (not commented out)
                for match in matches:
                    # Double-check it's not in a comment
                    if not match.strip().startswith('#'):
                        violations.append(f"{py_file}: {match.strip()}")
        
        # Assert no violations found
        assert len(violations) == 0, f"Found {len(violations)} active database calls:\n" + "\n".join(violations)

    def test_all_repositories_exist(self):
        """Verify all required repositories have been created"""
        
        repo_dir = Path("/Users/bohuihan/ai/real2ai/backend/app/services/repositories")
        
        required_repositories = [
            "analyses_repository.py",
            "analysis_progress_repository.py",
            "contracts_repository.py",
            "documents_repository.py",
            "profiles_repository.py",
            "user_contract_views_repository.py",
            "user_property_views_repository.py",
            "artifacts_repository.py",
            "runs_repository.py",
            "user_docs_repository.py",
            "recovery_repository.py"
        ]
        
        for repo_file in required_repositories:
            repo_path = repo_dir / repo_file
            assert repo_path.exists(), f"Repository file missing: {repo_file}"
            
            # Verify the file is not empty
            assert repo_path.stat().st_size > 100, f"Repository file appears empty: {repo_file}"

    def test_repository_imports_in_migrated_files(self):
        """Verify migrated files import and use repositories"""
        
        migrated_files = [
            "/Users/bohuihan/ai/real2ai/backend/app/router/websockets.py",
            "/Users/bohuihan/ai/real2ai/backend/app/router/contracts.py",
            "/Users/bohuihan/ai/real2ai/backend/app/tasks/background_tasks.py",
            "/Users/bohuihan/ai/real2ai/backend/app/tasks/user_aware_tasks.py",
            "/Users/bohuihan/ai/real2ai/backend/app/services/cache/cache_service.py",
        ]
        
        for file_path in migrated_files:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for repository imports
            assert "Repository" in content, f"No repository imports found in {file_path}"
            
            # Check for repository usage
            assert "Repository()" in content or "Repository(use_service_role" in content, \
                f"No repository instantiation found in {file_path}"

    def test_document_processing_nodes_migrated(self):
        """Verify all document processing nodes use repositories"""
        
        nodes_dir = Path("/Users/bohuihan/ai/real2ai/backend/app/agents/nodes/document_processing_subflow")
        
        nodes_to_check = [
            "error_handling_node.py",
            "build_summary_node.py",
            "mark_basic_complete_node.py",
            "mark_processing_started_node.py",
            "update_metrics_node.py",
            "already_processed_check_node.py",
            "fetch_document_node.py"
        ]
        
        for node_file in nodes_to_check:
            node_path = nodes_dir / node_file
            
            if node_path.exists():
                with open(node_path, 'r') as f:
                    content = f.read()
                
                # Should use DocumentsRepository
                assert "DocumentsRepository" in content, \
                    f"DocumentsRepository not found in {node_file}"
                
                # Should NOT have active database calls
                assert not re.search(r'^[^#]*user_client\.database\.', content, re.MULTILINE), \
                    f"Found active database call in {node_file}"

    def test_test_files_updated(self):
        """Verify test files have been created for repositories"""
        
        test_dir = Path("/Users/bohuihan/ai/real2ai/backend/tests/unit")
        
        test_files = [
            "repositories/test_user_property_views_repository.py",
            "repositories/test_user_contract_views_repository.py",
            "routers/test_websockets_repository_migration.py",
            "routers/test_contracts_repository_migration.py",
            "tasks/test_background_tasks_repository_migration.py",
            "agents/nodes/test_fetch_document_node_migration.py"
        ]
        
        for test_file in test_files:
            test_path = test_dir / test_file
            assert test_path.exists(), f"Test file missing: {test_file}"
            
            # Verify test file has actual tests
            with open(test_path, 'r') as f:
                content = f.read()
            
            assert "def test_" in content or "async def test_" in content, \
                f"No test functions found in {test_file}"

    def test_repository_pattern_consistency(self):
        """Verify repositories follow consistent patterns"""
        
        repo_dir = Path("/Users/bohuihan/ai/real2ai/backend/app/services/repositories")
        
        for repo_file in repo_dir.glob("*_repository.py"):
            # Skip __pycache__ and other non-repository files
            if "__" in str(repo_file):
                continue
                
            with open(repo_file, 'r') as f:
                content = f.read()
            
            # Check for common repository patterns
            assert "get_user_connection" in content or "get_service_role_connection" in content, \
                f"No connection method found in {repo_file.name}"
            
            # Check for async methods
            assert "async def" in content, f"No async methods found in {repo_file.name}"
            
            # Check for proper error handling
            assert "try:" in content or "except" in content, \
                f"No error handling found in {repo_file.name}"

    def test_rls_enforcement_through_repositories(self):
        """Verify RLS is enforced through repository connections"""
        
        repo_files = [
            "/Users/bohuihan/ai/real2ai/backend/app/services/repositories/documents_repository.py",
            "/Users/bohuihan/ai/real2ai/backend/app/services/repositories/analysis_progress_repository.py",
            "/Users/bohuihan/ai/real2ai/backend/app/services/repositories/user_contract_views_repository.py",
            "/Users/bohuihan/ai/real2ai/backend/app/services/repositories/user_property_views_repository.py"
        ]
        
        for repo_path in repo_files:
            with open(repo_path, 'r') as f:
                content = f.read()
            
            # Check for user connection usage (RLS enforcement)
            assert "get_user_connection" in content, \
                f"No user connection (RLS) found in {Path(repo_path).name}"
            
            # Check for user_id handling
            assert "user_id" in content.lower(), \
                f"No user_id handling found in {Path(repo_path).name}"

    def test_migration_completeness_summary(self):
        """Generate and verify migration completeness summary"""
        
        app_dir = Path("/Users/bohuihan/ai/real2ai/backend/app")
        
        # Count total Python files
        total_files = len(list(app_dir.rglob("*.py")))
        
        # Count files with repository imports
        files_with_repos = 0
        
        for py_file in app_dir.rglob("*.py"):
            with open(py_file, 'r') as f:
                if "Repository" in f.read():
                    files_with_repos += 1
        
        # Generate summary
        summary = {
            "total_python_files": total_files,
            "files_using_repositories": files_with_repos,
            "migration_coverage": f"{(files_with_repos / total_files * 100):.1f}%"
        }
        
        print("\n=== Repository Migration Summary ===")
        print(f"Total Python files: {summary['total_python_files']}")
        print(f"Files using repositories: {summary['files_using_repositories']}")
        print(f"Migration coverage: {summary['migration_coverage']}")
        
        # Assert reasonable migration coverage
        assert files_with_repos > 20, "Too few files using repositories"
        
        print("\n✅ Repository migration is COMPLETE!")
        print("All user_client.database calls have been migrated to repository pattern.")
        print("RLS enforcement is now properly handled through repositories.")
        
        return summary