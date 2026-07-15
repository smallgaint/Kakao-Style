from typing import Type, Optional
from urllib.parse import urlparse

from parser import InstizParser
from pann_parser import PannParser


class ParserFactory:
    """
    URL에 따라 적절한 파서 클래스를 반환하는 팩토리 클래스
    """
    _parsers = {
        "www.instiz.net": InstizParser,
        "pann.nate.com": PannParser,
    }

    @staticmethod
    def register_parser(domain: str, parser_class: Type):
        """새로운 파서를 등록합니다."""
        ParserFactory._parsers[domain] = parser_class

    @staticmethod
    def get_parser(url: str) -> Optional[Type]:
        """
        주어진 URL의 도메인에 맞는 파서 클래스를 반환합니다.

        Args:
            url: 분석할 URL
        Returns:
            URL에 맞는 파서 클래스 또는 None
        """
        domain = urlparse(url).netloc
        return ParserFactory._parsers.get(domain)