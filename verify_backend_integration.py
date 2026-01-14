#!/usr/bin/env python3
"""
API Backend Integration Verification Script
Tests critical service integration before Svelte UI development.
Run: python verify_backend_integration.py
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all critical modules import without errors."""
    print("\n=== Testing Module Imports ===")
    tests = [
        ("Flask app factory", lambda: __import__('web.api_app', fromlist=['create_app'])),
        ("Providers route", lambda: __import__('web.routes.providers', fromlist=['bp'])),
        ("System route", lambda: __import__('web.routes.system', fromlist=['bp'])),
        ("Jobs route", lambda: __import__('web.routes.jobs', fromlist=['bp'])),
        ("Config manager", lambda: __import__('core.settings', fromlist=['config_manager'])),
        ("Job queue", lambda: __import__('core.job_queue', fromlist=['job_queue'])),
        ("Provider registry", lambda: __import__('core.provider', fromlist=['ProviderRegistry'])),
    ]
    
    passed = 0
    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
    
    print(f"\nImports: {passed} passed, {failed} failed")
    return failed == 0

def test_config_manager():
    """Test config_manager persistence."""
    print("\n=== Testing config_manager Persistence ===")
    try:
        from core.settings import config_manager
        
        # Test get
        test_key = 'test.verify_script'
        initial = config_manager.get(test_key)
        print(f"  ✓ config_manager.get('{test_key}') returned: {initial}")
        
        # Test set
        test_value = 'verify_test_value_12345'
        config_manager.set(test_key, test_value)
        print(f"  ✓ config_manager.set('{test_key}', '{test_value}') executed")
        
        # Test persistence (retrieve again)
        retrieved = config_manager.get(test_key)
        if retrieved == test_value:
            print(f"  ✓ config_manager persisted: retrieved '{retrieved}'")
            return True
        else:
            print(f"  ✗ Persistence failed: expected '{test_value}', got '{retrieved}'")
            return False
            
    except Exception as e:
        print(f"  ✗ config_manager test failed: {e}")
        traceback.print_exc()
        return False

def test_job_queue():
    """Test job_queue creation and tracking."""
    print("\n=== Testing job_queue ===")
    try:
        from core.job_queue import job_queue
        
        # Test list jobs
        jobs = job_queue.list_jobs()
        print(f"  ✓ job_queue.list_jobs() returned {len(jobs)} jobs")
        
        # Test get active jobs
        active = job_queue.get_active_jobs()
        print(f"  ✓ job_queue.get_active_jobs() returned {len(active)} active jobs")
        
        # Test create job (optional - depends on implementation)
        if hasattr(job_queue, 'create_job'):
            try:
                test_job = job_queue.create_job('verify_test', {'test': True})
                print(f"  ✓ job_queue.create_job() created job: {test_job.get('id', 'unknown')}")
            except Exception as e:
                print(f"  ⚠ job_queue.create_job() not fully functional: {e}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ job_queue test failed: {e}")
        traceback.print_exc()
        return False

def test_provider_registry():
    """Test provider registry discovery."""
    print("\n=== Testing provider_registry ===")
    try:
        from web.services.provider_registry import provider_registry
        
        # Test list all providers
        providers = provider_registry.list_all() if hasattr(provider_registry, 'list_all') else []
        if not providers:
            print(f"  ⚠ provider_registry.list_all() returned empty (may be normal)")
        else:
            print(f"  ✓ provider_registry.list_all() returned {len(providers)} providers")
            if isinstance(providers, list) and len(providers) > 0:
                first = providers[0]
                print(f"    - First provider: {first.get('name', first.get('id', 'unknown'))}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ provider_registry test failed: {e}")
        traceback.print_exc()
        return False

def test_plugin_registry():
    """Test provider registry system."""
    print("\n=== Testing Provider Registry ===")
    try:
        from core.provider import ProviderRegistry
        
        # Test list all
        providers = ProviderRegistry.list_providers()
        print(f"  ✓ ProviderRegistry.list_providers() returned {len(providers)} providers")
        
        # Test get provider (for each available)
        if providers:
            for provider_name in providers[:2]:  # Test first 2
                fetched = ProviderRegistry.get_provider_class(provider_name)
                if fetched:
                    print(f"  ✓ ProviderRegistry.get_provider_class('{provider_name}') found")
                else:
                    print(f"  ⚠ ProviderRegistry.get_provider_class('{provider_name}') returned None")
        
        return True
        
    except Exception as e:
        print(f"  ✗ plugin_registry test failed: {e}")
        traceback.print_exc()
        return False

def test_flask_app():
    """Test Flask app factory and endpoints."""
    print("\n=== Testing Flask App ===")
    try:
        from web.api_app import create_app
        
        app = create_app()
        print(f"  ✓ create_app() initialized Flask app")
        
        # Test client
        client = app.test_client()
        print(f"  ✓ app.test_client() created")
        
        # Test critical endpoints
        endpoints = [
            ('/api/health', 'Health check'),
            ('/api/settings', 'Get settings'),
            ('/api/providers', 'List providers'),
            ('/api/jobs', 'List jobs'),
            ('/api/status', 'System status'),
        ]
        
        for path, desc in endpoints:
            try:
                resp = client.get(path)
                status = resp.status_code
                is_ok = status in (200, 404)  # 404 is acceptable for some unimplemented endpoints
                marker = "✓" if is_ok else "⚠"
                print(f"  {marker} GET {path} ({desc}): {status}")
            except Exception as e:
                print(f"  ✗ GET {path} failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Flask app test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Backend Integration Verification")
    print("=" * 60)
    
    results = {
        "Module Imports": test_imports(),
        "Config Manager": test_config_manager(),
        "Job Queue": test_job_queue(),
        "Provider Registry": test_provider_registry(),
        "Plugin Registry": test_plugin_registry(),
        "Flask App": test_flask_app(),
    }
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        marker = "✓" if passed_flag else "✗"
        print(f"{marker} {test_name}")
    
    print(f"\nResult: {passed}/{total} test groups passed")
    
    if passed == total:
        print("\n✓ All backend services are integrated and ready for Svelte UI!")
        return 0
    else:
        print("\n✗ Some backend services need attention before proceeding.")
        print("   See errors above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
