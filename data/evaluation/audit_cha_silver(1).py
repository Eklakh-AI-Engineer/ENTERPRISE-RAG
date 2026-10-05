import json, sys, os

checkpoint_path = os.path.abspath('data/evaluation/cha_silver_labels_v1.json')

with open(checkpoint_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Basic checks
assert data.get('total_queries') == 50, f"total_queries {data.get('total_queries')} != 50"
assert data.get('status') == 'complete', f"status {data.get('status')} != 'complete'"
assert data.get('completed_queries') == 50, f"completed_queries {data.get('completed_queries')} != 50"
assert data.get('completed_judgments') == 780, f"completed_judgments {data.get('completed_judgments')} != 780"
assert isinstance(data.get('queries'), list), "queries not a list"
assert len(data['queries']) == 50, f"queries length {len(data['queries'])} != 50"

# Check unique query IDs
ids = [q['query_id'] for q in data['queries']]
assert len(ids) == len(set(ids)), "duplicate query_id found"

# Check each query judgments
for q in data['queries']:
    cand_cnt = q.get('candidate_count')
    judgments = q.get('judgments')
    assert isinstance(judgments, list), f"judgments not list for {q['query_id']}"
    assert len(judgments) == cand_cnt, f"judgment count {len(judgments)} != candidate_count {cand_cnt} for {q['query_id']}"
    # Check each judgment fields
    for j in judgments:
        for field in ['candidate_index','relevance','confidence','chunk_id','label_source']:
            assert field in j, f"missing {field} in judgment of {q['query_id']}"
        # relevance in 0-3
        assert j['relevance'] in (0,1,2,3), f"invalid relevance {j['relevance']} in {q['query_id']}"
        # confidence 0.0-1.0
        assert 0.0 <= float(j['confidence']) <= 1.0, f"invalid confidence {j['confidence']} in {q['query_id']}"
        # label_source must be silver_ai
        assert j['label_source'] == 'silver_ai', f"invalid label_source {j['label_source']} in {q['query_id']}"

# Ensure partial_queries empty
assert not data.get('partial_queries'), "partial_queries not empty"

print('Audit passed: all checks OK')
