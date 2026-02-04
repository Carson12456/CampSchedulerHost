"""
Unit tests for Troop Repository Interface
"""
import pytest
from abc import ABC, abstractmethod
from typing import List, Optional

from interfaces.repositories.troop_repository import TroopRepository
from core.entities.troop import Troop


class TestTroopRepositoryInterface:
    """Test cases for Troop Repository Interface"""
    
    def test_interface_is_abstract(self):
        """Test that TroopRepository is an abstract base class"""
        assert issubclass(TroopRepository, ABC)
    
    def test_interface_has_required_methods(self):
        """Test that TroopRepository has required abstract methods"""
        required_methods = [
            'get_all',
            'get_by_name', 
            'save',
            'delete',
            'exists',
            'get_by_campsite',
            'get_by_commissioner',
            'count'
        ]
        
        for method_name in required_methods:
            assert hasattr(TroopRepository, method_name)
            method = getattr(TroopRepository, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_get_all_method_signature(self):
        """Test get_all method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.get_all)
        assert 'return' in hints
        # Check that it returns a List of Troop objects
        return_type = str(hints['return'])
        assert 'List[' in return_type and 'Troop' in return_type
    
    def test_get_by_name_method_signature(self):
        """Test get_by_name method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.get_by_name)
        assert 'name' in hints
        assert 'return' in hints
        # Check that it returns Optional[Troop]
        return_type = str(hints['return'])
        assert 'Optional[' in return_type and 'Troop' in return_type
    
    def test_save_method_signature(self):
        """Test save method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.save)
        assert 'troop' in hints
        # Check that it takes a Troop parameter
        param_type = str(hints['troop'])
        assert 'Troop' in param_type
    
    def test_delete_method_signature(self):
        """Test delete method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.delete)
        assert 'troop' in hints
        # Check that it takes a Troop parameter
        param_type = str(hints['troop'])
        assert 'Troop' in param_type
    
    def test_exists_method_signature(self):
        """Test exists method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.exists)
        assert 'name' in hints
        assert 'return' in hints
        # Check that it returns a bool
        return_type = str(hints['return'])
        assert 'bool' in return_type
    
    def test_get_by_campsite_method_signature(self):
        """Test get_by_campsite method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.get_by_campsite)
        assert 'campsite' in hints
        assert 'return' in hints
        # Check that it returns a List of Troop objects
        return_type = str(hints['return'])
        assert 'List[' in return_type and 'Troop' in return_type
    
    def test_get_by_commissioner_method_signature(self):
        """Test get_by_commissioner method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.get_by_commissioner)
        assert 'commissioner' in hints
        assert 'return' in hints
        # Check that it returns a List of Troop objects
        return_type = str(hints['return'])
        assert 'List[' in return_type and 'Troop' in return_type
    
    def test_count_method_signature(self):
        """Test count method signature"""
        from typing import get_type_hints
        
        hints = get_type_hints(TroopRepository.count)
        assert 'return' in hints
        # Check that it returns an int
        return_type = str(hints['return'])
        assert 'int' in return_type
    
    def test_interface_cannot_be_instantiated(self):
        """Test that abstract interface cannot be instantiated"""
        with pytest.raises(TypeError):
            TroopRepository()
