"""WikiLinks 解析器测试。"""
import pytest
from linglong.knowledge.wikilinks import WikiLinksParser, WikiLink


@pytest.fixture
def parser():
    return WikiLinksParser()


def test_parse_simple_link(parser):
    """解析简单 [[target]] 链接。"""
    content = "这是一个 [[概念A]] 的描述"
    links = parser.parse(content)
    assert len(links) == 1
    assert links[0].target == "概念A"
    assert links[0].display == "概念A"


def test_parse_link_with_display(parser):
    """解析 [[target|display]] 链接。"""
    content = "参考 [[微服务|微服务架构]] 了解更多"
    links = parser.parse(content)
    assert len(links) == 1
    assert links[0].target == "微服务"
    assert links[0].display == "微服务架构"


def test_parse_multiple_links(parser):
    """解析多个链接。"""
    content = "[[A]] 和 [[B|链接B]] 以及 [[C]]"
    links = parser.parse(content)
    assert len(links) == 3
    assert [l.target for l in links] == ["A", "B", "C"]


def test_skip_code_blocks(parser):
    """跳过代码块内的链接。"""
    content = "正文 [[链接1]]\n```\n[[代码内链接]]\n```\n更多 [[链接2]]"
    links = parser.parse(content)
    assert len(links) == 2
    assert [l.target for l in links] == ["链接1", "链接2"]


def test_skip_inline_code(parser):
    """跳过行内代码中的链接。"""
    content = "使用 `[[not_link]]` 语法，但 [[real_link]] 是真的"
    links = parser.parse(content)
    assert len(links) == 1
    assert links[0].target == "real_link"


def test_extract_unique_targets(parser):
    """提取唯一目标列表。"""
    content = "[[A]] [[B]] [[A]] [[C]] [[B]]"
    targets = parser.extract_targets(content)
    assert targets == ["A", "B", "C"]


def test_no_links(parser):
    """无链接返回空列表。"""
    content = "普通文本没有链接"
    assert parser.parse(content) == []
