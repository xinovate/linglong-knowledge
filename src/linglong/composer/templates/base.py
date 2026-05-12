from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class Template(ABC):
    """模板抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', 'unknown')
        self.rules = config.get('rules', {})
    
    @abstractmethod
    def validate(self, content: str) -> ValidationResult:
        """
        验证内容是否符合模板规范
        
        Args:
            content: 待验证的内容
            
        Returns:
            ValidationResult: 验证结果
        """
        pass
    
    @abstractmethod
    def apply(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        将内容和元数据应用到模板
        
        Args:
            content: 原始内容
            metadata: 元数据（标题、日期、标签等）
            
        Returns:
            str: 格式化后的内容
        """
        pass
    
    @abstractmethod
    def get_required_metadata(self) -> List[str]:
        """返回必需的元数据字段"""
        pass
    
    def format_info(self) -> str:
        """返回模板信息"""
        return f"{self.name}: {self.__class__.__name__}"
