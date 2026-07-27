"""Tenant Isolation 测试"""

from api.middleware.tenant import inject_tenant_filter


def test_inject_tenant_filter():
    sql = "SELECT * FROM embedding_items WHERE source_type = 'doc'"
    result = inject_tenant_filter(sql, firm_id="firm_a", engagement_id="eng_001")
    assert "firm_id = 'firm_a'" in result
    assert "engagement_id = 'eng_001'" in result


def test_inject_no_engagement():
    sql = "SELECT * FROM embedding_items"
    result = inject_tenant_filter(sql, firm_id="firm_a")
    assert "firm_id = 'firm_a'" in result
    assert "engagement_id" not in result
