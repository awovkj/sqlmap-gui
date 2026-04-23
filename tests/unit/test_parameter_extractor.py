from framework.intake.parameter_extractor import extract_test_points
from framework.model.request import TargetRequest


def test_extracts_query_and_json_points():
    target = TargetRequest(
        method="POST",
        url="http://example.com/items?id=1",
        headers={"Content-Type": "application/json", "X-Test": "demo"},
        body='{"name":"alice","profile":{"age":18}}',
    )
    points = extract_test_points(target)
    locations = {(point.location, point.name) for point in points}
    assert ("query", "id") in locations
    assert ("json", "name") in locations
    assert ("json", "age") in locations
    assert ("header", "X-Test") in locations
