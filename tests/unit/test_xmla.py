"""XMLA placeholders must never look like a successful empty query."""

import pytest

from powerbi_governance.infrastructure.clients.xmla import XmlaClient


@pytest.mark.unit
async def test_unimplemented_xmla_queries_fail_explicitly():
    client = XmlaClient()

    with pytest.raises(NotImplementedError, match="DAX queries"):
        await client.execute_dax_query("dataset-1", "EVALUATE ROW(\"x\", 1)")

    with pytest.raises(NotImplementedError, match="usage metrics"):
        await client.get_usage_metrics_table("dataset-1")
